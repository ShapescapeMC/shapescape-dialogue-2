from .compiler import AnimationTimeline, ConfigProvider
from .parser import ParseError, tokenize, build_ast
from pathlib import Path

import prettyprinter  # pip install prettyprinter (pprint didn't work nicely)

def main():
    prettyprinter.install_extras(
        include=[
            'dataclasses',
        ],
        warn_on_error=True
    )

    source_file = Path("test.txt")
    output_file = Path("log.txt")

    with source_file.open("r", encoding='utf8') as f:
        source = f.readlines()
    tokens = tokenize(source)
    with output_file.open("w", encoding='utf8') as f:
        for token in tokens:
            print(token, file=f)
        print("\n\n\n\n", file=f)
        tree = build_ast(tokens)
        prettyprinter.pprint(tree, stream=f)

        result = AnimationTimeline.from_events_list(
            ConfigProvider(tree.settings, None),
            tree.timeline[0].time.messages, "my_prefix"
        )
        print("\n\n\n\n", file=f)
        prettyprinter.pprint(result, stream=f)
