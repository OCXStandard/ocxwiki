#!/usr/bin/env python
"""Test script to verify python-dotenv is properly installed."""

#  Copyright (c) 2026. OCX Consortium https://3docx.org. See the LICENSE

import sys
print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print()

try:
    import dotenv
    print("✓ Successfully imported 'dotenv' module")
    print(f"  Location: {dotenv.__file__}")
    print(f"  Package: {dotenv.__package__}")

    from dotenv import load_dotenv
    print("✓ Successfully imported 'load_dotenv' function")

    # Try to load .env file
    load_dotenv()
    print("✓ load_dotenv() executed successfully")

except ImportError as e:
    print(f"✗ Import failed: {e}")
    print("\nInstalled packages with 'dotenv' in name:")
    import subprocess
    result = subprocess.run([sys.executable, "-m", "pip", "list"],
                          capture_output=True, text=True)
    for line in result.stdout.split('\n'):
        if 'dotenv' in line.lower():
            print(f"  {line}")
    sys.exit(1)

print("\n✓ All imports successful!")
