#!/usr/bin/env python3
"""
Goal Masters - Main Launcher
This script starts the menu system which then launches the game.
"""

import os
import sys

# Add the current directory to the Python path so imports work correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

# Import and run the menu system
if __name__ == "__main__":
    try:
        import imagem_inicial
    except ImportError as e:
        print(f"Error importing menu system: {e}")
        print("Make sure you're running this script from the PyGameDesoft directory")
        sys.exit(1) 