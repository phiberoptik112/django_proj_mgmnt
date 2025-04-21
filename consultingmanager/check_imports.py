import os
import sys
from collections import defaultdict

def find_circular_imports(start_path):
    import_graph = defaultdict(set)
    
    def scan_file(file_path):
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Simple import detection
        lines = content.split('\n')
        current_module = os.path.splitext(os.path.basename(file_path))[0]
        
        for line in lines:
            line = line.strip()
            if line.startswith('from ') and ' import ' in line:
                try:
                    module = line.split('from ')[1].split(' import ')[0]
                    if '.' in module:
                        module = module.split('.')[0]
                    if module != current_module:
                        import_graph[current_module].add(module)
                except:
                    continue
            elif line.startswith('import '):
                try:
                    module = line.split('import ')[1].split()[0]
                    if '.' in module:
                        module = module.split('.')[0]
                    if module != current_module:
                        import_graph[current_module].add(module)
                except:
                    continue
    
    def find_cycles(graph, start, path=None):
        if path is None:
            path = []
        path = path + [start]
        
        if start in path[:-1]:
            cycle_start = path.index(start)
            return path[cycle_start:]
            
        for next_node in list(graph[start]):  # Create a copy of the set
            if next_node not in path or next_node == path[0]:
                cycle = find_cycles(graph, next_node, path)
                if cycle:
                    return cycle
        return None
    
    # Scan all Python files
    for root, dirs, files in os.walk(start_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                scan_file(file_path)
    
    # Check for cycles
    cycles = []
    nodes = list(import_graph.keys())  # Create a copy of the keys
    for node in nodes:
        cycle = find_cycles(import_graph, node)
        if cycle:
            cycles.append(cycle)
    
    return cycles

if __name__ == '__main__':
    project_path = os.path.dirname(os.path.abspath(__file__))
    cycles = find_circular_imports(project_path)
    
    if cycles:
        print("Found circular imports:")
        for cycle in cycles:
            print(" -> ".join(cycle) + " -> " + cycle[0])
    else:
        print("No circular imports found.") 