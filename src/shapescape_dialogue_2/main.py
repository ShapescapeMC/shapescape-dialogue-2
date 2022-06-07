from .compiler import AnimationControllerTimeline, AnimationTimeline, ConfigProvider
from .parser import tokenize, build_ast
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

        for sound_profile in tree.sound_profiles.sound_profiles:
            config_provider = ConfigProvider(tree.settings, sound_profile)
            result = AnimationControllerTimeline.from_timeline_nodes(
                tree.timeline, config_provider)
            print("\n\n\n\n", file=f)
            prettyprinter.pprint(result, stream=f)
            # It's just for testing do only one iteration
            break
        # Skip the rest of the program for testing...
        return
        for sound_profile in tree.sound_profiles.sound_profiles:
            config_provider = ConfigProvider(tree.settings, sound_profile)
            result = AnimationTimeline.from_message_node_list(
                config_provider, tree.timeline[0].time.messages)
            print("\n\n\n\n", file=f)
            prettyprinter.pprint(result, stream=f)

            duration = max(result.events.keys())
            result = AnimationTimeline.from_coordinates_list(
                tree.timeline[0], duration, spline_fit_degree=3)
            print("\n\n\n\n", file=f)
            prettyprinter.pprint(result, stream=f)

            # It's just for testing do only one iteration
            break