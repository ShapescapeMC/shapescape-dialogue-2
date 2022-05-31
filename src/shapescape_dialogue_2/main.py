from .parser import ParseError, tokenize, build_ast
from pathlib import Path

def main():
    source_file = Path("test.txt")
    output_file = Path("log.txt")

    with source_file.open("r", encoding='utf8') as f:
        source = f.readlines()
    tokens = tokenize(source)
    with output_file.open("w", encoding='utf8') as f:
        for token in tokens:
            print(token, file=f)
        tree = build_ast(tokens)
        print(tree, file=f)
        # try:
        #     tree = build_ast(tokens)
        #     print(tree, file=f)
        # except ParseError as e:
        #     print(str(e))
