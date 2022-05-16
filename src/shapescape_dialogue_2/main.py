from .parser import tokenize
from pathlib import Path

def main():
    source_file = Path("test.txt")
    with source_file.open("r") as f:
        source = f.readlines()
    tokens = tokenize(source)
    for token in tokens:
        print(token)
