import sys, os
root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root)
os.chdir(root)

from tools.portrait_editor.editor_main import run_editor

if __name__ == "__main__":
    run_editor()
