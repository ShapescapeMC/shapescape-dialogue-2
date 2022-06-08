from pathlib import Path

import prettyprinter  # pip install prettyprinter (pprint didn't work nicely)

from .compiler import AnimationControllerTimeline, ConfigProvider
from .parser import build_ast, tokenize


def main():
    prettyprinter.install_extras(
        include=[
            'dataclasses',
        ],
        warn_on_error=True
    )

    source_file = Path("source.txt")
    log_tokens = Path("log_tokens.txt")
    log_ast = Path("log_ast.txt")
    log_compiled = Path("log_compiled.txt")

    with source_file.open("r", encoding='utf8') as f:
        source = f.readlines()
    tokens = tokenize(source)
    with log_tokens.open("w", encoding='utf8') as f:
        for token in tokens:
            print(token, file=f)
    with log_ast.open("w", encoding='utf8') as f:
        tree = build_ast(tokens)
        prettyprinter.pprint(tree, stream=f)

    with log_compiled.open("w", encoding='utf8') as f:
        for sound_profile in tree.sound_profiles.sound_profiles:
            config_provider = ConfigProvider(tree.settings, sound_profile)
            result = AnimationControllerTimeline.from_timeline_nodes(
                tree.timeline, config_provider)
            prettyprinter.pprint(result, stream=f)
