<!-- doctree start -->
Table of contents:
- [# Writing the Documentation](/docs/writing_the_documentation.md)
- [About the documentation](/docs/README.md)
- [Installation as Regolith Filter](/docs/installation.md)
- [Syntax of the dialogue files](/docs/syntax.md)
- [Usage](/docs/usage_as_module.md)
- [Usage](/docs/usage_with_regolith_filter.md)

In this article you can read about:
- [Overview](#overview)
- [Settings](#settings)
  - [`wpm`](#wpm)
  - [`cpm`](#cpm)
  - [`tp_selector:`](#tp_selector)
  - [`description`](#description)
- [Profiles](#profiles)
  - [`sounds:`](#sounds)
  - [`variables:`](#variables)
- [Dialogue Definition](#dialogue-definition)
<!-- doctree end -->
# Syntax of the dialogue files

## Overview
Dialogue files use a custom syntax similar to YAML. A dialogue file can be divided into 3 sections:

- [Settings](#settings) (optional) - Settings contain a list of global settings for the file.
- [Profiles](#profiles) (optional) - Profiles are used to create alternate versions of dialogues that differ in sounds and some text.
- [Dialogue Definition](#dialogue-definition) - The Dialogue Definition consists of a list of nodes used to create the dialogue.

Please note that this filter strictly looks for indentation in your code. While the tool can adjust to different types of indentation, it may break if the indentation is not consistent throughout your code.

## Settings
Settings define the default values of some properties used later in the code. Their use is optional. 

```
settings: wpm=120 tp_selector=@a[tag=!dev] description="The is a camera entity" 
```
The following settings are supported:
### `wpm`
`float` - The default words-per-minute value used to determine the dialogue duration.
### `cpm`
`float` - The default characters-per-minute value used to determine the dialogue duration. If `wpm` is defined, `cpm` is ignored.
### `tp_selector:`
`string` - The selector used in the `/tp` commands of the camera nodes. The default is `@a`.
### `description`
`string` - a description field for the entity for this dialogue for [Content Guide Generator](https://github.com/Shapescape-Software/content_guide_generator). Adding this property also adds other properties that the content guide generator expects: `"locations": [], "category": "non_player_facing_utility"`.


## Profiles

The `Profiles` node defines profiles. Each profile is used to generate an alternative version of the dialogue. Profiles are optional, but are really useful to create dialogues that share a lot of resources, such as two very similar dialogues but with different voice actors or slightly different text (such as different character names).

```
profiles:
    male:
        sounds:
        obi_wan=starwars/obi_wan/male
        grevious=starwars/grevious/spanish_accent
        variables:
        obi_wan_rank=General
    female:
        sounds:
        obi_wan=starwars/obi_wan/female
        grevious=starwars/grevious/french_accent
        variables:
        obi_wan_rank=Lieutenant

```


A profile contains definitions of sound and text variables. A profile can have any name except those reserved for other types of labels (such as "settings", "camera", etc.).

A profile can contain the following nodes:
### `sounds:`
`sounds_variable=sounds_variable_directory` 

The sounds node allows you to define a variable for a directory for all sounds connected to one actor of your profile. To refer to the sound path from a profile in the dialogue, simply enter it in the sound property's of a message node before the actual sound, separated by a colon.
\
\
**Example:**\
For example, in the code above, a sound is defined as `obi_wan=starwars/obi_wan/male`. The variable `obi_wan` will later be reused in one of the sounds like `obi_wan:hello.ogg`. This means that the dialogue will use the sound located at `starwars/obi_wan/male/hello.ogg`.

### `variables:`
`variable_name=value`

The `variables` node allows you to define a variable specific to your profile
\
\
**Example:**\
For example, there is a profile called `male` that defines `obi_wan_rank` as `General` and a `female` profile that defines `obi_wan_rank` as `Lieutenant`. In the code there is a message node that says `>[Grevious] {obi_wan_rank} Kenobi!`. The actual text used in the dialogue will be `>[Grevious] General Kenobi!` when using the `male` profile and `>[Grevious] Lieutenant Kenobi!` when using the `female` profile."

## Dialogue Definition
The `Dialogue Definition` section stores all the content of the dialogue/cutscene. All content is being executed from top to bottom. You can message nodes such as tell, title, actionbar or blank and the camera node.

```
tell:
    >Long time ago in a galaxy far, far away...
tell:
    > ...tere was an epic fight between General Grevious and Obi-Wan Kenobi.
    
title:
    > Level 1
    > The fight
    
actionbar:
    > Cutscene initiating...

blank: time=5

camera: interpolation_mode=1
    10 10 10 90 0
    5 5 5 30 0
    5 10 5 0 0
    5 10 5 0 0
    actor_path: interpolation_mode=3 tp_selector=@e[type=zombie,c=1]
        1617 14 1482 facing 1625 19 1472
        1617 14 1482 facing 1633 3 1478
    timeline:
        blank: time=1
            /scorebard players set @a force 0
            run_once:
                /summon shapescape:obi_wan 1 2 3
            schedule: time=2.3
                /execute @a[type=shapescape:clone] ~ ~ ~  function order_66
            on_exit:
                /event entity @e[type=shapescape:obi_wan] remove_high_ground
        tell: sound=obi_wan:hello.ogg
            >[Obi-Wan] Hello there!
        tell: wpm=90 sound=grevious:general_kenobi.ogg
            >[Grevious] {obi_wan_rank} Kenobi!
            >[this is just an example...] This is a multiline text.
            loop: time=0.1
                /playsound grevious.cough
        title:
            >Bossfight!
            >This is a subtitle.
            /scoreboard players set @a force 100
            run_once:
                /music play bossfight
        actionbar:
            >Objective: kill General Grevious
        blank: sound=starwars/rd2d/beep_boop.ogg time=1
```

###  Comments
Everything after `##` in a line is a comment.

### Message nodes
Message nodes are the main feature of the dialogue. They behave very similarly, with the main difference being their display and line count limit.

```
tell:
    >Long time ago in a galaxy far, far away...
tell:
    > ...tere was an epic fight between General Grevious and Obi-Wan Kenobi.
    
title:
    > Level 1
    > The fight
    
actionbar:
    > Cutscene initiating...

blank: time=5
```

The main part of the message node is the message. Messages start with `>`. Message nodes can also execute commands. Commands in dialogs must use the `/` prefix. Messages must be defined above commands.

The main part of the message node is the message, which starts with `>`. Message nodes can also execute commands, which must use the `/` prefix. Messages must be defined above commands."

Message nodes can be nested inside other nodes such as a [camera](#camera) timeline.

All Raw JSON text produced by the script uses the structure:
```
{"rawtext":[{"translate":"AUTOMATICALLY_ASSIGNED_VALUE","with":["\n"]}]}
```
where `AUTOMATICALLY_ASSIGNED_VALUE` is a translation key assigned by the script. Note that the `"with":["\n"]` is added so that you can use the newline character in your text (in the same way as you would when creating a normal Minecraft addon). For example, `>Hello%1World!` would be displayed in-game as:

where `AUTOMATICALLY_ASSIGNED_VALUE` is a translation key assigned by the script. Note that the `"with":["\n"]` is added so that you can use the newline character in your text (in the same way as you would when creating a normal Minecraft addon).

The following example illustrates this: `>Hello%1World!` will be displayed in-game as:

```
Hello
World!
```

#### `Tell:`
This node displays with the `tellraw <tp_selector>` command.
#### `Title:`
This node displays the text with the `titleraw <tp_selector> title` command for the first line and with `titleraw <tp_selector> subtitle` for the second line. It can't contain more than two lines.
#### `Actionbar:`
This node displays the text with the `titleraw <tp_selector> actionbar` command. It can't contain more than one line.
#### `Blank:`
This node is not used for displaying text. It is however used for executing commands, loops ect. The blank nodes do not allow for `wmp` and `cpm` properties.

#### Message node properties
Message nodes can use one following properties to define their length.

`wpm:` `float`\
Defines the length of this message by a set amount of words per minute. This property has a higher priority than the `wpm` defined in the settings.\
`cpm:` `float`\
Defines the length of this message by a set amount of characters per minute. Has higher priority than the `cpm` defined in the settings..\
`time:` `float`\
Defines the length of this message by a set amount of time. \
`sound:` `string`\
Defines the length of this message by the length of the provided sound file. 

Note that using a reference to a sound that doesn't exist is not an error, but it will print a warning. Such references are useful if you don't have a sound and need to generate a placeholder dialogue.

#### The sub-nodes of message nodes

Message nodes use sub-nodes for commands that have some additional conditions for execution:
##### `run_once`
Commands in this subsection of a message node are executed only once, even if a certain part of the dialogue is reached several times. This can happen if the world is reloaded while the dialogue is still running. It should be used for commands that should not be executed multiple times, for example when the player gets a reward or when the state of the game changes.
##### `schedule`
Schedule allows you to run commands with a delay. The schedule label requires the `time` property to be defined. The timer for the delay starts when the message is displayed. Schedule also supports negative values. In this case, the timer counts backwards from the end of the message. Adding scheduled commands that evaluate to values below 0 is not allowed.
##### `on_exit`
On exit is a convenient way to put a command after the time of the message node. It's the same as putting it in the next message node.
##### `loop`
Loop repeats the message while playing its section of the message node. It uses the `time` property to determine the duration of the loop.

> _Developer Note_
> 
>Internally, the `schedule`, `loop` and `on_exit` commands are just inserted into the timeline of the Minecraft BP animation. The `run_once` is handled by generating a tag which marks the commands as executed.

### Camera
The camera node is a special type of dialogue node that controls the movement of the camera. It can only be used in the root timeline of the dialogue and nesting camera nodes inside other camera nodes is not allowed. The camera node has three parts: the coordinates list, an optional actor paths section, and the timeline.

```
camera: interpolation_mode=1
    10 10 10 90 0
    5 5 5 30 0
    5 10 5 0 0
    5 10 5 0 0
    actor_path: interpolation_mode=3 tp_selector=@e[type=zombie,c=1]
        1617 14 1482 facing 1625 19 1472
        1617 14 1482 facing 1633 3 1478
    timeline:
        blank: time=1
            /scorebard players set @a force 0
            run_once:
                /summon shapescape:obi_wan 1 2 3
            schedule: time=2.3
                /execute @a[type=shapescape:clone] ~ ~ ~  function order_66
            on_exit:
                /event entity @e[type=shapescape:obi_wan] remove_high_ground
        tell: sound=obi_wan:hello.ogg
            >[Obi-Wan] Hello there!
        tell: wpm=90 sound=grevious:general_kenobi.ogg
            >[Grevious] {obi_wan_rank} Kenobi!
            >[this is just an example...] This is a multiline text.
            loop: time=0.1
                /playsound grevious.cough
        title:
            >Bossfight!
            >This is a subtitle.
            /scoreboard players set @a force 100
            run_once:
                /music play bossfight
        actionbar:
            >Objective: kill General Grevious
        blank: sound=starwars/rd2d/beep_boop.ogg time=1
```

The `camera` can either use a `time` property, which defines the duration of the camera movement, or have a list of message nodes in its sub-node called `timeline`. In this case, the camera uses the duration of the sequence of message nodes to define what is needed for the camera to move.

#### Coordinates
The coordinates can be written in one of three formats: Simple, Facing to Coordinates, or Facing to Selector:
- The Simple format is written as `<x> <y> <z> <yaw> <pitch>` and an example would be `1 2 3 45 90`.
- The Facing to Coordinates format is written as `<x> <y> <z> facing <x1> <y1> <z1>` and an example would be `1 2 3 facing 4 5 6`.
- The Facing to Selector format is written as `<x> <y> <z> facing <selector>` and an example would be `1 2 3 facing @p`.

The coordinate formats match the format used in Minecraft's `/tp` command. It's recommended to use only one format for the entire camera animation, as this allows the script to interpolate smoothly between frames. Mixing different formats in the same timeline is allowed, but not recommended. When using the Simple format, it's important to note that the interpolation treats the rotations as normal coordinates. Therefore, interpolating between 350° and 0° is almost a full rotation.

#### Interpolation Mode
The `camera` node also accepts the `interpolation_mode` property, which defines the type of interpolation used for camera movement. The argument takes an integer value from 0 to 3, which refers to the order of the spline interpolation:
- 0: no interpolation, resulting in discrete jumps between keyframes.
- 1: linear interpolation
- 2: quadratic interpolation
- 3: cubic interpolation

The default value is 3. The interpolation mode value must be less than the number of points to be interpolated. If there are not enough points, the interpolation mode is automatically reduced to the lowest possible value.

The camera's `tp_selector` property sets the target selector used for the `/tp` command. By default, it's set to @`a`.

#### Actor Paths
The actor paths are subnodes of the camera node, and multiple actor paths can exist within the same camera. Each actor path contains a list of coordinates to animate an entity other than the main animated entity. The actor path takes the same settings as the camera node, such as the interpolation_mode and tp_selector. However, the tp_selector is required for actor paths.

## Example File
```
settings: wpm=120 tp_selector=@a[tag=!dev] description="The is a camera entity
profiles:
    male:
        sounds:
        obi_wan=starwars/obi_wan/male
        grevious=starwars/grevious/spanish_accent
        variables:
        obi_wan_rank=General
    female:
        sounds:
        obi_wan=starwars/obi_wan/female
        grevious=starwars/grevious/french_accent
        variables:
        obi_wan_rank=Lieutenant

tell:
    >Long time ago in a galaxy far, far away...
tell:
    > ...tere was an epic fight between General Grevious and Obi-Wan Kenobi.
    
title:
    > Level 1
    > The fight
    
actionbar:
    > Cutscene initiating...

blank: time=5

camera: interpolation_mode=1
    10 10 10 90 0
    5 5 5 30 0
    5 10 5 0 0
    5 10 5 0 0
    
    ## This is a comment that could mention something explain something about the the actor_path
    actor_path: interpolation_mode=3 tp_selector=@e[type=grevious,c=1]
        1617 14 1482 facing 1625 19 1472
        1617 14 1482 facing 1633 3 1478
    timeline:
        blank: 
            loop: time=0.5
                /time add 100
        blank: time=10
            /scorebard players set @a force 0
            run_once:
                /summon shapescape:obi_wan 1 2 3
            schedule: time=2.3
                /execute @a[type=shapescape:clone] ~ ~ ~  function order_66
            on_exit:
                /event entity @e[type=shapescape:obi_wan] remove_high_ground
                
        tell: sound=obi_wan:hello.ogg
            >[Obi-Wan] Hello there!
            
        tell: wpm=90 sound=grevious:general_kenobi.ogg
            >[Grevious] {obi_wan_rank} Kenobi!
            >[this is just an example...] This is a multiline text.
            loop: time=0.1
                /playsound grevious.cough
                
        title:
            >Bossfight!
            >This is a subtitle.
            /scoreboard players set @a force 100
            run_once:
                /music play bossfight
                
        actionbar:
            >Objective: kill General Grevious
            
        blank: sound=starwars/rd2d/beep_boop.ogg time=1
```