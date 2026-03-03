with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i in range(3300, 3320):
        line = lines[i]
        indent = len(line) - len(line.lstrip())
        print(f'{i+1:4d} [{indent:2d}] {line}', end='')
