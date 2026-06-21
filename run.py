import os
import sys

# Ensure the 'src' directory is in the import path so that the package imports work
# even if it hasn't been installed in editable mode yet.
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from desktop_voice_assistant.app import main

if __name__ == "__main__":
    main()
