# parse_exclusions.py
def parse_exclusions(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    # Filter out comments and empty lines, then strip whitespace
    patterns = [line.strip() for line in lines if line.strip() and not line.startswith('#')]
    return patterns

if __name__ == '__main__':
    import sys
    exclusions_file = sys.argv[1]
    for pattern in parse_exclusions(exclusions_file):
        print(pattern)
