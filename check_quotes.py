with open("main.py", encoding="utf-8") as f:
    for idx, line in enumerate(f, 1):
        if line.count('"""') % 2 == 1:
            print('Quote imbalance candidate at', idx)
