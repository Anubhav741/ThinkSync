import subprocess
import os

import sys

def main():
    root_app = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app.py")
    subprocess.run([sys.executable, root_app])

if __name__ == "__main__":
    main()
