import os

repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
main_path = os.path.join(repo_root, "backend", "main.py")

with open(main_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(3300, 3320):
        line = lines[i]
        indent = len(line) - len(line.lstrip())
        print(f'{i+1:4d} [{indent:2d}] {line}', end='')
