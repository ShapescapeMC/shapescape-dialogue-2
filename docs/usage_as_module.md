<!-- doctree start -->
Table of contents:
- [About the documentation](/docs/README.md)
- [Installation as Regolith Filter](/docs/installation.md)
- [Syntax of the dialogue files](/docs/syntax.md)
- [Usage as module](/docs/usage_as_module.md)
- [Usage with regolith filter](/docs/usage_with_regolith_filter.md)
- [Writing the Documentation](/docs/writing_the_documentation.md)

In this article you can read about:
<!-- doctree end -->
# Usage as module

This module is designed to generate Minecraft entities that run a sequence of commands, dialogues, and camera movements based on a custom syntax. It can be used to create cutscenes or dialogue sequences within Minecraft. By using this module, users can create more immersive and engaging experiences for players within the game.

The main script is a command line tool, and it should be available on your system after installation. To learn more about its features, simply run the following command:

```
shapescape-dialogue-2 --help
```

This will provide you with a detailed explanation of how to use the tool and its various capabilities.

The options starting with `--debug` are intended for debugging purposes only and are not necessary for normal use. To run the script, you must specify the source file, namespace, and output directories for both the resource pack and behavior pack. If you are using Regolith, these settings will be automatically provided.