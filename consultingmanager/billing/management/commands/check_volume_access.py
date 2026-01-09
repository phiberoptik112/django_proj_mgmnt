"""
Django management command to diagnose and refresh network volume access.

This command helps troubleshoot issues where Finder can see network volumes
but Django/terminal processes cannot access them.
"""

from django.core.management.base import BaseCommand, CommandError
from pathlib import Path
import sys

from billing.utils.volume_access import (
    check_volume_accessible,
    list_mounted_volumes,
    refresh_volume_access,
    attempt_volume_reconnection,
    diagnose_file_access,
)


class Command(BaseCommand):
    help = 'Diagnose and refresh network volume access for PIF file scanning'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Check access to a specific file path',
        )
        parser.add_argument(
            '--volume',
            type=str,
            help='Check access to a specific volume (e.g., "KAILUA PROJECTS")',
        )
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all mounted volumes',
        )
        parser.add_argument(
            '--refresh',
            type=str,
            help='Attempt to refresh access to a volume (provide volume name)',
        )
        parser.add_argument(
            '--reconnect',
            type=str,
            help='Attempt to reconnect to a volume (provide volume name)',
        )
        parser.add_argument(
            '--diagnose',
            type=str,
            help='Run full diagnosis on a file path',
        )

    def handle(self, *args, **options):
        if options['list']:
            self.list_volumes()
        elif options['file']:
            self.check_file(options['file'])
        elif options['volume']:
            self.check_volume(options['volume'])
        elif options['refresh']:
            self.refresh_volume(options['refresh'])
        elif options['reconnect']:
            self.reconnect_volume(options['reconnect'])
        elif options['diagnose']:
            self.diagnose_file(options['diagnose'])
        else:
            # Default: list volumes and show help
            self.stdout.write(self.style.WARNING('No action specified. Showing mounted volumes:'))
            self.list_volumes()
            self.stdout.write('\nUse --help to see available options.')

    def list_volumes(self):
        """List all mounted volumes."""
        self.stdout.write(self.style.SUCCESS('\n=== Mounted Volumes ===\n'))
        volumes = list_mounted_volumes()
        
        if not volumes:
            self.stdout.write(self.style.WARNING('No volumes found in /Volumes'))
            return
        
        for vol in volumes:
            status = '✓' if vol['readable'] else '✗'
            style = self.style.SUCCESS if vol['readable'] else self.style.ERROR
            self.stdout.write(
                style(f"{status} {vol['name']}")
            )
            self.stdout.write(f"   Path: {vol['path']}")
            self.stdout.write(f"   Exists: {vol['exists']}")
            self.stdout.write(f"   Readable: {vol['readable']}")
            
            mount_info = vol.get('mount_info', {})
            if mount_info.get('mounted'):
                self.stdout.write(f"   Mounted: Yes")
                if mount_info.get('device'):
                    self.stdout.write(f"   Device: {mount_info['device']}")
            else:
                self.stdout.write(self.style.WARNING(f"   Mounted: No"))
            self.stdout.write('')

    def check_file(self, file_path):
        """Check access to a specific file."""
        self.stdout.write(self.style.SUCCESS(f'\n=== Checking File Access ===\n'))
        self.stdout.write(f'File: {file_path}\n')
        
        check = check_volume_accessible(file_path)
        
        self.stdout.write(f"Exists: {check['exists']}")
        self.stdout.write(f"Is Directory: {check['is_dir']}")
        self.stdout.write(f"Is File: {check['is_file']}")
        self.stdout.write(f"Readable: {check['readable']}")
        self.stdout.write(f"Accessible: {check['accessible']}")
        
        if check.get('volume_name'):
            self.stdout.write(f"\nVolume: {check['volume_name']}")
            self.stdout.write(f"Volume Mount: {check['volume_mount']}")
            
            mount_info = check.get('mount_info', {})
            if mount_info:
                self.stdout.write(f"\nMount Info:")
                self.stdout.write(f"  Mounted: {mount_info.get('mounted', 'Unknown')}")
                if mount_info.get('device'):
                    self.stdout.write(f"  Device: {mount_info['device']}")
                if mount_info.get('mount_type'):
                    self.stdout.write(f"  Type: {mount_info['mount_type']}")
        
        if check.get('error'):
            self.stdout.write(self.style.ERROR(f"\nError: {check['error']}"))
        
        if not check['accessible']:
            self.stdout.write(self.style.WARNING('\n⚠ File is not accessible!'))
            self.stdout.write('\nTry running:')
            self.stdout.write(f'  python manage.py check_volume_access --diagnose "{file_path}"')

    def check_volume(self, volume_name):
        """Check access to a specific volume."""
        volume_path = f"/Volumes/{volume_name}"
        self.stdout.write(self.style.SUCCESS(f'\n=== Checking Volume Access ===\n'))
        self.stdout.write(f'Volume: {volume_name}\n')
        self.stdout.write(f'Path: {volume_path}\n')
        
        check = check_volume_accessible(volume_path)
        
        self.stdout.write(f"\nExists: {check['exists']}")
        self.stdout.write(f"Is Directory: {check['is_dir']}")
        self.stdout.write(f"Readable: {check['readable']}")
        self.stdout.write(f"Accessible: {check['accessible']}")
        
        mount_info = check.get('mount_info', {})
        if mount_info:
            self.stdout.write(f"\nMount Info:")
            self.stdout.write(f"  Mounted: {mount_info.get('mounted', 'Unknown')}")
            if mount_info.get('device'):
                self.stdout.write(f"  Device: {mount_info['device']}")
            if mount_info.get('mount_type'):
                self.stdout.write(f"  Type: {mount_info['mount_type']}")
            if mount_info.get('error'):
                self.stdout.write(self.style.ERROR(f"  Error: {mount_info['error']}"))
        
        if check.get('error'):
            self.stdout.write(self.style.ERROR(f"\nError: {check['error']}"))
        
        if not check['accessible']:
            self.stdout.write(self.style.WARNING('\n⚠ Volume is not accessible!'))
            self.stdout.write('\nTry:')
            self.stdout.write(f'  python manage.py check_volume_access --refresh "{volume_name}"')
            self.stdout.write(f'  python manage.py check_volume_access --reconnect "{volume_name}"')

    def refresh_volume(self, volume_name):
        """Attempt to refresh access to a volume."""
        self.stdout.write(self.style.SUCCESS(f'\n=== Refreshing Volume Access ===\n'))
        self.stdout.write(f'Volume: {volume_name}\n')
        
        result = refresh_volume_access(volume_name)
        
        if result['success']:
            self.stdout.write(self.style.SUCCESS(f"✓ {result['message']}"))
        else:
            self.stdout.write(self.style.ERROR(f"✗ {result['message']}"))
            if result.get('error'):
                self.stdout.write(self.style.ERROR(f"Error: {result['error']}"))
            
            self.stdout.write(self.style.WARNING('\nSuggestions:'))
            self.stdout.write('1. Disconnect the volume in Finder (eject)')
            self.stdout.write('2. Reconnect the volume in Finder')
            self.stdout.write('3. Verify the volume is accessible in Finder')
            self.stdout.write('4. Try running this command again')

    def reconnect_volume(self, volume_name):
        """Attempt to reconnect to a volume."""
        self.stdout.write(self.style.SUCCESS(f'\n=== Attempting Volume Reconnection ===\n'))
        self.stdout.write(f'Volume: {volume_name}\n')
        
        result = attempt_volume_reconnection(volume_name)
        
        self.stdout.write(f"\nMethods Tried:")
        for method in result.get('methods_tried', []):
            status = '✓' if method.get('success') or method.get('mounted') else '✗'
            style = self.style.SUCCESS if (method.get('success') or method.get('mounted')) else self.style.ERROR
            self.stdout.write(style(f"  {status} {method['method']}: {method.get('message', 'N/A')}"))
        
        if result['success']:
            self.stdout.write(self.style.SUCCESS(f"\n✓ {result['best_message']}"))
        else:
            self.stdout.write(self.style.WARNING(f"\n⚠ {result['best_message']}"))
            self.stdout.write(self.style.WARNING('\nManual Steps:'))
            self.stdout.write('1. Open Finder')
            self.stdout.write('2. Eject the volume (right-click -> Eject, or drag to trash)')
            self.stdout.write('3. Reconnect the volume using Finder -> Go -> Connect to Server (Cmd+K)')
            self.stdout.write('4. Wait for the volume to mount')
            self.stdout.write('5. Try running this command again')

    def diagnose_file(self, file_path):
        """Run full diagnosis on a file path."""
        self.stdout.write(self.style.SUCCESS(f'\n=== File Access Diagnosis ===\n'))
        self.stdout.write(f'File: {file_path}\n')
        
        diagnosis = diagnose_file_access(file_path)
        
        self.stdout.write(f"\n=== File Check ===")
        file_check = diagnosis.get('file_check', {})
        self.stdout.write(f"Exists: {file_check.get('exists', False)}")
        self.stdout.write(f"Is Directory: {file_check.get('is_dir', False)}")
        self.stdout.write(f"Is File: {file_check.get('is_file', False)}")
        self.stdout.write(f"Readable: {file_check.get('readable', False)}")
        self.stdout.write(f"Accessible: {file_check.get('accessible', False)}")
        
        if file_check.get('volume_name'):
            self.stdout.write(f"\n=== Volume Information ===")
            self.stdout.write(f"Volume Name: {file_check['volume_name']}")
            self.stdout.write(f"Volume Mount: {file_check.get('volume_mount')}")
            
            mount_info = file_check.get('mount_info', {})
            if mount_info:
                self.stdout.write(f"\nMount Status:")
                self.stdout.write(f"  Mounted: {mount_info.get('mounted', 'Unknown')}")
                if mount_info.get('device'):
                    self.stdout.write(f"  Device: {mount_info['device']}")
                if mount_info.get('mount_type'):
                    self.stdout.write(f"  Type: {mount_info['mount_type']}")
        
        if diagnosis.get('parent_dir_check'):
            self.stdout.write(f"\n=== Parent Directory Check ===")
            parent = diagnosis['parent_dir_check']
            self.stdout.write(f"Exists: {parent.get('exists', False)}")
            self.stdout.write(f"Readable: {parent.get('readable', False)}")
        
        if diagnosis.get('volume_check'):
            self.stdout.write(f"\n=== Volume Mount Check ===")
            volume = diagnosis['volume_check']
            self.stdout.write(f"Exists: {volume.get('exists', False)}")
            self.stdout.write(f"Readable: {volume.get('readable', False)}")
        
        if diagnosis.get('suggestions'):
            self.stdout.write(f"\n=== Suggestions ===")
            for i, suggestion in enumerate(diagnosis['suggestions'], 1):
                self.stdout.write(self.style.WARNING(f"{i}. {suggestion}"))
        
        if not file_check.get('accessible'):
            self.stdout.write(self.style.ERROR('\n⚠ File is not accessible!'))
            if file_check.get('volume_name'):
                self.stdout.write(f"\nTry refreshing the volume:")
                self.stdout.write(f'  python manage.py check_volume_access --refresh "{file_check["volume_name"]}"')






