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
from core.main import main
main() 