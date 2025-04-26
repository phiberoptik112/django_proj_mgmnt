import os
import pandas as pd
import re
from typing import List, Dict
from pathlib import Path
import pdfplumber
from docx import Document
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Set the backend to non-interactive Agg
import matplotlib.pyplot as plt
from matplotlib.cm import get_cmap


def extract_text_from_file(file_path: str) -> str:
    """Extract text content from various file types"""
    extension = Path(file_path).suffix.lower()
    
    try:
        if extension == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif extension == '.pdf':
            # Requires pdfplumber package
            with pdfplumber.open(file_path) as pdf:
                return ' '.join(page.extract_text() for page in pdf.pages)
        elif extension in ['.doc', '.docx']:
            # Requires python-docx package
            doc = Document(file_path)
            return ' '.join(paragraph.text for paragraph in doc.paragraphs)
        else:
            return ''
    except (IOError, FileNotFoundError, pdfplumber.PDFSyntaxError, ValueError) as e:
        print(f"Error extracting text from {file_path}: {str(e)}")
        return ''

def find_dollar_amounts(text: str) -> List[Dict]:
    """Find dollar amounts associated with 'lump sum fee' in text"""
    # Pattern for finding "lump sum fee" followed by dollar amount
    pattern = r'lump sum fee of (?:[\$]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)'
    
    # Find all matches with surrounding context
    findings = []
    for match in re.finditer(pattern, text, re.IGNORECASE):
        # Extract just the dollar amount portion
        amount = re.search(r'(?:[\$]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', match.group()).group()
        
        # Get surrounding context
        start = max(0, match.start() - 50)
        end = min(len(text), match.end() + 50)
        context = text[start:end].strip()
        
        findings.append({
            'integers_found': amount,
            'sentence': context
        })
    
    return findings

def create_project_db(project_path: str) -> Dict[str, pd.DataFrame]:
    """
    Create pandas DataFrames of files in project folder structure, organized by folder.
    
    Args:
        project_path: Path to project root directory
        
    Returns:
        Dictionary of DataFrames, keyed by folder name
    """
    folder_dfs = {}
    
    for root, dirs, files in os.walk(project_path):
        # Get folder name from path
        folder_name = os.path.basename(root)
        
        if files:  # Only process folders that contain files
            file_data = []
            for file in files:
                file_path = os.path.join(root, file)
                file_type = os.path.splitext(file)[1].lower()
                
                file_data.append({
                    'filename': file,
                    'path': file_path,
                    'file_type': file_type
                })
            
            # Create DataFrame for this folder
            df = pd.DataFrame(file_data)
            
            # Add to dictionary, combining with existing data if folder name exists
            if folder_name in folder_dfs:
                folder_dfs[folder_name] = pd.concat([folder_dfs[folder_name], df], ignore_index=True)
            else:
                folder_dfs[folder_name] = df
                
    return folder_dfs


def analyze_proposals(project_paths: List[str]) -> pd.DataFrame:
    """
    Analyze proposal documents from multiple projects to find dollar amounts.
    """
    all_findings = []
    
    for path in project_paths:
        # Walk through project directory
        for root, _, files in os.walk(path):
            for file in files:
                if 'proposal' in file.lower():
                    file_path = os.path.join(root, file)
                    text_content = extract_text_from_file(file_path)
                    
                    if text_content:
                        findings = find_dollar_amounts(text_content)
                        for finding in findings:
                            finding['source_file'] = file
                            finding['project_path'] = path
                            all_findings.append(finding)
    
    # Create DataFrame from findings
    if all_findings:
        results_df = pd.DataFrame(all_findings)
    else:
        results_df = pd.DataFrame(columns=['source_file', 'project_path', 'integers_found', 'sentence'])
    
    return results_df

def get_year_project_paths(base_path: str, year: str) -> List[str]:
    """
    Get a list of all project folder paths for a given year.
    
    Args:
        base_path (str): Base path to the projects directory (e.g. "//DLA-04/Shared/KAILUA PROJECTS/")
        year (str): Year to search for (e.g. "2023")
        
    Returns:
        List[str]: List of full paths to all project folders for that year
    """
    year_path = os.path.join(base_path, year)
    project_paths = []
    
    # Check if year directory exists
    if not os.path.exists(year_path):
        print(f"Warning: Year directory {year_path} not found")
        return project_paths
        
    # Get all subdirectories in the year folder
    try:
        for item in os.listdir(year_path):
            full_path = os.path.join(year_path, item)
            if os.path.isdir(full_path):
                # Only include if it starts with YY-### format
                if re.match(r'\d{2}-\d{3}', item):
                    project_paths.append(full_path)
                    
    except PermissionError:
        print(f"Warning: Permission denied accessing {year_path}")
    except Exception as e:
        print(f"Warning: Error accessing {year_path}: {str(e)}")
        
    return sorted(project_paths)

def analyze_scope_of_work(project_paths: List[str]) -> pd.DataFrame:
    """
    Analyze proposal documents to extract scope of work sections and categorize them.
    
    Args:
        project_paths (List[str]): List of paths to project folders to analyze
        
    Returns:
        pd.DataFrame: DataFrame containing scope categories and details for each project
    """
    all_scopes = []
    
    for project_path in project_paths:
        # Walk through project directory
        for root, _, files in os.walk(project_path):
            for filename in files:
                if filename.lower().endswith(('.doc', '.docx', '.pdf')):
                    file_path = os.path.join(root, filename)
                    
                    # Extract text content
                    try:
                        text_content = extract_text_from_file(file_path)
                    except Exception as e:
                        print(f"Warning: Could not read {file_path}: {str(e)}")
                        continue
                        
                    if text_content:
                        # Find scope of work section using regex
                        scope_match = re.search(r'(?i)scope\s+of\s+work\s*:?(.*?)(?:\n\s*[A-Z][A-Z\s]+:|$)', 
                                              text_content, re.DOTALL)
                        
                        if scope_match:
                            scope_text = scope_match.group(1).strip()
                            
                            # Split into bullet points/numbered items
                            scope_items = re.split(r'\n\s*[•\-\d]+\.?\s*', scope_text)
                            scope_items = [item.strip() for item in scope_items if item.strip()]
                            
                            # Categorize each scope item
                            for item in scope_items:
                                scope_info = {
                                    'project_path': project_path,
                                    'source_file': filename,
                                    'scope_item': item,
                                    'category': categorize_scope_item(item)
                                }
                                all_scopes.append(scope_info)
    
    # Create DataFrame from findings
    if all_scopes:
        results_df = pd.DataFrame(all_scopes)
    else:
        results_df = pd.DataFrame(columns=['project_path', 'source_file', 'scope_item', 'category'])
    
    return results_df

def categorize_scope_item(text: str) -> str:
    """
    Categorize a scope item based on keywords.
    This is a basic implementation - could be enhanced with ML/more sophisticated categorization.
    """
    text = text.lower()
    
    categories = {
        'structural': ['structural', 'foundation', 'concrete', 'steel', 'framing', 'seismic'],
        'assessment': ['assessment', 'evaluation', 'inspection', 'testing', 'analysis'],
        'design': ['design', 'drawing', 'specification', 'detail'],
        'documentation': ['report', 'documentation', 'document', 'submittal'],
        'coordination': ['coordination', 'meeting', 'review', 'consultation']
    }
    
    for category, keywords in categories.items():
        if any(keyword in text for keyword in keywords):
            return category
            
    return 'other'

def create_project_file_list(project_path: str | list[str], output_file: str = None) -> dict:
    """
    Create a text file listing all files in a project path and return a dictionary
    of folder structure with file counts.
    
    Args:
        project_path: Path to the project directory or list of project paths
        output_file: Path to output text file (if None, uses project name + '_files.txt')
        
    Returns:
        Dictionary with folder structure and file counts
    """
    # Handle both single path and list of paths
    if isinstance(project_path, list):
        all_folder_structures = {}
        for path in project_path:
            folder_structure = create_project_file_list(path)
            all_folder_structures.update(folder_structure)
        return all_folder_structures
    
    if output_file is None:
        # Create output filename based on project name
        project_name = os.path.basename(project_path)
        output_file = f"{project_name}_files.txt"
    
    # Dictionary to store folder structure and file counts
    folder_structure = {}
    
    # Open file for writing
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"File listing for project: {project_path}\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("-" * 80 + "\n\n")
        
        # Walk through directory
        for root, dirs, files in os.walk(project_path):
            # Get relative path from project root
            rel_path = os.path.relpath(root, project_path)
            if rel_path == '.':
                rel_path = ''
            
            # Write folder path
            folder_indent = '  ' * (rel_path.count(os.sep))
            f.write(f"{folder_indent}📁 {os.path.basename(root)}/\n")
            
            # Count files in this folder
            file_count = len(files)
            
            # Add to structure dictionary
            folder_structure[rel_path] = file_count
            
            # Write files
            for file in files:
                file_indent = '  ' * (rel_path.count(os.sep) + 1)
                f.write(f"{file_indent}📄 {file}\n")
            
            f.write("\n")
    
    return folder_structure

def plot_folder_tree(project_path: str | list[str], folder_structure: dict = None):
    """
    Plot the folder tree of a project, highlighting which sub-folders have large numbers of files.
    
    Args:
        project_path: Path to the project directory or list of project paths
        folder_structure: Dictionary with folder structure and file counts (if None, will be generated)
    """
    # Import networkx here to avoid loading it during Django startup
    import networkx as nx
    
    # Handle both single path and list of paths
    if isinstance(project_path, list):
        # Create a combined graph for all projects
        G = nx.DiGraph()
        
        for path in project_path:
            # Generate folder structure for this path if not provided
            if folder_structure is None:
                current_structure = create_project_file_list(path)
            else:
                current_structure = folder_structure
                
            # Add nodes for each folder
            project_name = os.path.basename(path)
            G.add_node(project_name, files=0)  # Root node
            
            # Process each folder
            for folder_path, file_count in current_structure.items():
                if folder_path == '':
                    # This is the root, update its file count
                    G.nodes[project_name]['files'] += file_count
                    continue
                    
                # Split path into components
                components = folder_path.split(os.sep)
                
                # Add nodes and edges for each level
                parent = project_name
                for i, component in enumerate(components):
                    # Create path up to this component
                    if i == 0:
                        path = component
                    else:
                        path = os.sep.join(components[:i+1])
                        
                    # If this node doesn't exist yet, add it
                    if not G.has_node(path):
                        G.add_node(path, files=0)
                        G.add_edge(parent, path)
                    
                    # If this is the leaf node, add file count
                    if i == len(components) - 1:
                        G.nodes[path]['files'] += file_count
                        
                    parent = path
        
        # Use the first project name for the plot title
        project_name = os.path.basename(project_path[0])
    else:
        # Single path case - use existing logic
        if folder_structure is None:
            folder_structure = create_project_file_list(project_path)
        
        # Create a directed graph
        G = nx.DiGraph()
        
        # Add nodes for each folder
        project_name = os.path.basename(project_path)
        G.add_node(project_name, files=0)  # Root node
        
        # Process each folder
        for folder_path, file_count in folder_structure.items():
            if folder_path == '':
                # This is the root, update its file count
                G.nodes[project_name]['files'] += file_count
                continue
                
            # Split path into components
            components = folder_path.split(os.sep)
            
            # Add nodes and edges for each level
            parent = project_name
            for i, component in enumerate(components):
                # Create path up to this component
                if i == 0:
                    path = component
                else:
                    path = os.sep.join(components[:i+1])
                    
                # If this node doesn't exist yet, add it
                if not G.has_node(path):
                    G.add_node(path, files=0)
                    G.add_edge(parent, path)
                
                # If this is the leaf node, add file count
                if i == len(components) - 1:
                    G.nodes[path]['files'] += file_count
                    
                parent = path
    
    # Calculate node sizes based on file counts
    max_files = max([data['files'] for _, data in G.nodes(data=True)]) if G.nodes else 1
    node_sizes = [2000 * (data['files'] / max_files) + 500 for _, data in G.nodes(data=True)]
    
    # Calculate node colors based on file counts
    cmap = get_cmap('viridis')
    node_colors = [cmap(data['files'] / max_files) if max_files > 0 else cmap(0) for _, data in G.nodes(data=True)]
    
    # Create labels with folder name and file count
    labels = {node: f"{node.split(os.sep)[-1]}\n({data['files']} files)" 
              for node, data in G.nodes(data=True)}
    
    # Create the plot
    plt.figure(figsize=(15, 10))
    # Use spring_layout instead of graphviz_layout
    pos = nx.spring_layout(G, k=1, iterations=50)
    
    # Draw the graph
    nx.draw(G, pos, 
            node_size=node_sizes,
            node_color=node_colors,
            with_labels=True,
            labels=labels,
            font_size=8,
            font_weight='bold',
            arrows=False,
            alpha=0.8)
    
    # Add a colorbar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, max_files))
    sm.set_array([])
    cbar = plt.colorbar(sm)
    cbar.set_label('Number of Files')
    
    # Add title
    plt.title(f"Folder Structure for {project_name}", fontsize=16)
    
    # Save the plot
    plt.savefig(f"{project_name}_folder_tree.png", dpi=300, bbox_inches='tight')
    plt.close()



def main():
    """Process multiple project folders to analyze proposal documents for dollar amounts."""
    # Example usage
    # root dir
    # //DLA-04/Shared/KAILUA PROJECTS/2023/
    project_paths = [
        "//DLA-04/Shared/KAILUA PROJECTS/2018/18-136 Masters at Ka'anapali Hillside Condos Floor Assessment",
        "//DLA-04/Shared/KAILUA PROJECTS/2018/18-099 Masters at Kaanpali AIIC Testing"
    ]
    
    # Analyze proposals and find dollar amounts
    # propsal_results = analyze_proposals(project_paths)
    
    # # Save results to CSV
    # propsal_results.to_csv('proposal_analysis_results.csv', index=False)
    
    # # Print summary
    # print(f"\nFound {len(propsal_results)} dollar amounts in proposal documents")
    # print("\nSample findings:")
    # print(propsal_results.head())

    # # Create project databases
    # project_dbs = [create_project_db(path) for path in project_paths]
    # print(project_dbs)
    # Save project databases to CSV
    # for folder_name, df in project_dbs.items():
    #     df.to_csv(f'{folder_name}_project_db.csv', index=False)

    # Get project paths for a specific year
    # year = '2023'
    # project_paths = get_year_project_paths("//DLA-04/Shared/KAILUA PROJECTS/", year)
    # print(project_paths)

    # # Analyze scope of work
    # scope_results = analyze_scope_of_work(project_paths)
    # print(scope_results)

    # Create project file list
    project_file_list = create_project_file_list(project_paths)
    print(project_file_list)

    # Plot folder tree
    plot_folder_tree(project_paths, project_file_list)

if __name__ == "__main__":
    main()
