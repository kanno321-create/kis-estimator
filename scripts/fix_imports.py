#!/usr/bin/env python3
"""Fix all _util_io imports to use relative imports"""

import os
import re
from pathlib import Path

# Files to fix
files_to_fix = [
    'src/kis_estimator_core/engine/breaker_critic.py',
    'src/kis_estimator_core/engine/cover_tab_writer.py',
    'src/kis_estimator_core/engine/doc_lint_guard.py',
    'src/kis_estimator_core/engine/enclosure_solver.py',
    'src/kis_estimator_core/engine/estimate_formatter.py',
    'src/kis_estimator_core/engine/spatial_assistant.py'
]

def fix_import(filepath):
    """Fix import statement in a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace the import statement
        content = content.replace('from _util_io import', 'from ._util_io import')

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

        print(f"[OK] Fixed: {filepath}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to fix {filepath}: {e}")
        return False

def main():
    print("Fixing _util_io imports...")

    fixed = 0
    for filepath in files_to_fix:
        if fix_import(filepath):
            fixed += 1

    print(f"\n[SUCCESS] Fixed {fixed}/{len(files_to_fix)} files")

if __name__ == '__main__':
    main()