#!/usr/bin/env python3
"""
Fix circular imports in route files by converting to dependency injection.
"""

import re
from pathlib import Path

# Mapping of old imports to new dependency imports
IMPORT_MAPPINGS = {
    'from main import auth_service': 'from main import get_auth_service',
    'from main import network_service': 'from main import get_network_service',
    'from main import system_service': 'from main import get_system_service',
    'from main import config_manager': 'from main import get_config_manager',
}

# Files to process
ROUTE_FILES = [
    'backend/api/routes/auth.py',
    'backend/api/routes/status.py',
    'backend/api/routes/config.py',
    'backend/api/routes/services.py',
    'backend/api/routes/portal.py',
    'backend/api/routes/backup.py',
]

def fix_file(filepath):
    """Fix imports in a single file."""
    print(f"Processing {filepath}...")

    with open(filepath, 'r') as f:
        content = f.read()

    original_content = content

    # Replace imports
    for old_import, new_import in IMPORT_MAPPINGS.items():
        content = content.replace(old_import, new_import)

    # If content changed, write it back
    if content != original_content:
        with open(filepath, 'w') as f:
            f.write(content)
        print(f"  ✓ Fixed {filepath}")
        return True
    else:
        print(f"  - No changes needed for {filepath}")
        return False

if __name__ == '__main__':
    for route_file in ROUTE_FILES:
        fix_file(route_file)

    print("\n✓ Import fixes complete!")
    print("\nIMPORTANT: You still need to add Depends() to function signatures.")
    print("Example change:")
    print("  OLD: async def my_endpoint(auth_service):")
    print("  NEW: async def my_endpoint(auth_service: AuthService = Depends(get_auth_service)):")
