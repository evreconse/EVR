#!/usr/bin/env python3
"""
EVRECONSE - Run Script.

Simple entry point that can be used to run the application.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from main import main

if __name__ == "__main__":
    sys.exit(main())