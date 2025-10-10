"""
Management command to test the PIF parser with a specific Excel file.
"""

import os
import sys
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import logging

from billing.utils.pif_parser import parse_pif_excel

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test the PIF parser with a specific Excel file'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='Path to the Excel file to test'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output'
        )

    def handle(self, *args, **options):
        file_path = options['file_path']
        verbose = options['verbose']
        
        if verbose:
            logging.basicConfig(level=logging.INFO)
        
        if not os.path.exists(file_path):
            raise CommandError(f'File does not exist: {file_path}')
        
        self.stdout.write(f'Testing PIF parser with file: {file_path}')
        
        try:
            result = parse_pif_excel(file_path)
            
            self.stdout.write(self.style.SUCCESS('Parser completed successfully!'))
            self.stdout.write(f'Extracted {len(result)} fields:')
            
            for key, value in result.items():
                if key == 'raw_pairs':
                    self.stdout.write(f'  {key}: {len(value)} raw pairs')
                elif key == 'csv_preview':
                    if value and 'error' in value:
                        self.stdout.write(f'  {key}: ERROR - {value["error"]}')
                    elif value:
                        self.stdout.write(f'  {key}: {value["row_count"]} rows from sheet "{value["sheet_name"]}"')
                    else:
                        self.stdout.write(f'  {key}: No preview available')
                else:
                    self.stdout.write(f'  {key}: {value}')
            
            # Show CSV preview details if available
            if 'csv_previews' in result and result['csv_previews']:
                csv_previews = result['csv_previews']
                total_sheets = result.get('total_sheets', 0)
                sheets_with_data = result.get('sheets_with_data', 0)
                
                self.stdout.write(f'\nCSV Preview Details ({sheets_with_data} of {total_sheets} sheets contain data):')
                
                for i, preview in enumerate(csv_previews):
                    self.stdout.write(f'\n  Sheet {i+1}: {preview["sheet_name"]}')
                    if 'error' in preview:
                        self.stdout.write(f'    Error: {preview["error"]}')
                    else:
                        self.stdout.write(f'    Headers: {preview["headers"]}')
                        self.stdout.write(f'    Rows shown: {preview["row_count"]}')
                        self.stdout.write(f'    Total rows in sheet: {preview["total_rows_in_sheet"]}')
                        self.stdout.write(f'    Total columns: {preview["total_cols_in_sheet"]}')
                        self.stdout.write(f'    Non-empty columns: {preview["non_empty_cols"]}')
                        
                        # Show first few rows
                        if preview['rows']:
                            self.stdout.write('    First 3 rows:')
                            for j, row in enumerate(preview['rows'][:3]):
                                self.stdout.write(f'      Row {j+1}: {row}')
            elif 'csv_preview' in result and result['csv_preview']:
                # Fallback for old format
                csv_preview = result['csv_preview']
                if 'error' not in csv_preview:
                    self.stdout.write('\nCSV Preview Details:')
                    self.stdout.write(f'  Sheet: {csv_preview["sheet_name"]}')
                    self.stdout.write(f'  Headers: {csv_preview["headers"]}')
                    self.stdout.write(f'  Rows: {csv_preview["row_count"]}')
                    if 'total_sheets' in csv_preview:
                        self.stdout.write(f'  Total sheets in file: {csv_preview["total_sheets"]}')
                    if 'total_rows_in_sheet' in csv_preview:
                        self.stdout.write(f'  Total rows in sheet: {csv_preview["total_rows_in_sheet"]}')
                    
                    # Show first few rows
                    if csv_preview['rows']:
                        self.stdout.write('\nFirst 3 rows:')
                        for i, row in enumerate(csv_preview['rows'][:3]):
                            self.stdout.write(f'  Row {i+1}: {row}')
            
            # Show raw pairs if available
            if 'raw_pairs' in result and result['raw_pairs']:
                self.stdout.write(f'\nFirst 10 raw pairs:')
                for i, (label, value) in enumerate(result['raw_pairs'][:10]):
                    self.stdout.write(f'  {i+1}. {label}: {value}')
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Parser failed with error: {e}'))
            if verbose:
                import traceback
                self.stdout.write(traceback.format_exc())
            raise CommandError(f'Parser failed: {e}')
