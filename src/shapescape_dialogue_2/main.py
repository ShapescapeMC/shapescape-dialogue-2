from pathlib import Path

import prettyprinter  # pip install prettyprinter (pprint didn't work nicely)

from .compiler import (AnimationControllerTimeline, ConfigProvider,
                       SoundCodeProvider, TranslationCodeProvider)
from .generator import Context, generate
from .parser import build_ast, tokenize


def main() -> None:
    prettyprinter.install_extras(
        include=[
            'dataclasses',
        ],
        warn_on_error=True
    )
    # Debug paths
    source_file = Path("my_awesome_dialogue.txt")
    log_tokens = Path("log_tokens.txt")
    log_ast = Path("log_ast.txt")
    # log_compiled = Path("log_compiled.txt")
    # log_generated = Path("log_generated.txt")

    # Read the source
    with source_file.open("r", encoding='utf8') as f:
        source = f.readlines()

    tokens = tokenize(source)
    with log_tokens.open("w", encoding='utf8') as f:
        for token in tokens:
            print(token, file=f)
    tree = build_ast(tokens)
    with log_ast.open("w", encoding='utf8') as f:
        prettyprinter.pprint(tree, stream=f)

    context = Context(
        bp_path=Path("generated/BP"),
        rp_path=Path("generated/RP"),
        subpath=source_file.stem,
        namespace='shapescape'
    )
    results = Path('generated')
    if results.exists():
        import shutil
        shutil.rmtree(results)
    generate(tree, context)
    # with log_generated.open("w", encoding='utf8') as f:
    #     prettyprinter.pprint(generator, stream=f)
    
