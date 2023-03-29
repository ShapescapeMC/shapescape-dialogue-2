<!-- doctree start -->
Table of contents:
- [About the documentation](/docs/README.md)
- [Installation as Regolith Filter](/docs/installation.md)
- [Syntax of the dialogue files](/docs/syntax.md)
- [Usage as module](/docs/usage_as_module.md)
- [Usage with regolith filter](/docs/usage_with_regolith_filter.md)
- [Writing the Documentation](/docs/writing_the_documentation.md)

In this article you can read about:
- [Run the filter](#run-the-filter)
- [Start dialogues in-game](#start-dialogues-in-game)
<!-- doctree end -->
# Usage with regolith filter

## Run the filter
This regolith filter is designed to generate Minecraft entities that run a sequence of commands, dialogues, and camera movements based on a custom syntax. It can be used to create cutscenes or dialogue sequences within Minecraft. By using this module, users can create more immersive and engaging experiences for players within the game.

To use this filter, you need to create dialogue files and place them in the data folder of the filter. By default, this folder is located at `data/shapescape_dialogue`, and all dialogue files must have the .dialogue extension. You can learn more about the syntax of the dialogue file by clicking on this [link to the syntax documentation](/docs/syntax.md).

Then you just need to run regolith and all files relevant to the filter will be placed into the compiled files. To start a dialogue sequence ingame you just need to summon the dialogue entity with this syntax:

```
/summon namespace:dialoge_file_name x y z <dialogue_file_name.profile>
```

## Start dialogues in-game
Since the dialogue entity executes the logic behind the camera movements and dialogue, it is important to ensure that the entity remains within the entity render distance. Ideally, the entity should be summoned within a ticking area to ensure that it continues to function properly.