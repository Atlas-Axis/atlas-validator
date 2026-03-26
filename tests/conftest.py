"""Test configuration — adds renderer directory to sys.path."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'renderer'))
