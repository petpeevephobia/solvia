#!/usr/bin/env python3
"""
Solvia SEO Audit Tool - Main Launcher

This is the main entry point for the Solvia SEO audit application.
It imports and runs the core application from the organized file structure.

Usage:
    python solvia.py
"""

import sys
import os

# Add the core directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

# Import and run the main application
if __name__ == "__main__":
    try:
        from main import main
        main()
    except ImportError as e:
        print(f"❌ Error importing main application: {e}")
        print("Please ensure all dependencies are installed and the file structure is correct.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error running Solvia: {e}")
        sys.exit(1) 