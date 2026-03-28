#!/usr/bin/python3
import sys, os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from web_app import start_server

if __name__ == "__main__":
    start_server()
