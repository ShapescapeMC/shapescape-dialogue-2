# 📝 Description
`shapescape-dialogue-2` is a Python library for generating dialogue and camera
sequences for Minecraft. It's the core of the
[shapescape_dialogue](https://github.com/ShapescapeMC/regolith-filters/tree/master/shapescape_dialogue)
Regolith filter but it can also be used as a standalone tool (not recommended).

# 💿 Installation

> **Note**
>
> If you want to use this with Regolith, you don't need to install it.

You can install the library with `pip` command which should be available
in your system if you have Python properly installed. Simply use:
```
pip install git+https://github.com/ShapescapeMC/shapescape-dialogue-2
```

If you want to install specific version, for example `0.0.3`, you can pass
the tag name to pip like this:
```
pip install git+https://github.com/ShapescapeMC/shapescape-dialogue-2@0.0.3
```

# ⭐ Usage
In most cases you should use this tool with Regolith. Details related
to Regolith are explained on the [filter page](https://github.com/ShapescapeMC/regolith-filters/tree/master/shapescape_dialogue) and in the
[Regolith documentation](https://bedrock-oss.github.io/regolith/). The filter
runs the main script from this library, which can also be used as a standalone
tool. The main benefit of using the filter is that the tool is not allowed to
delete any files, so you'll have to manually clean up the generated files every
time you run it. Regolith works on a copy of the source and handles the
deletion of unwanted files.

The main script is accessed via command line, and it should be available once
you have installed the library. You can use it like this:
```
shapescape-dialogue-2
```
Running `shapescape-dialogue-2 --help` will show the list of available options.
The options that start with `--debug` are for debugging purposes and they're
not important for normal usage. The script expects you to provide the,
source file, the namespace and the output resource pack and behavior pack
directories. When you run with Regolith, these settings are automatically
provided.

# 🔣 Syntax of the dialogue files

## Overview
Dialogue files use custom syntax similar to YAML. A dialogue file can be
devided into 3 sections:
- **settings** (optional) - contains a list of global settings of the file.
  Currently (version 0.0.3) it only lets you set the default properties for
  calculating the delay lengths between the dialogue lines. These options can
  be overritten by the individual lines.
- **profiles** (optional) - profiles are used to generate alternative versions
    of the dialogue. Profiles define sounds, and variables which can be later
    used in the dialogue definition
- **dialogue definition** - everything below the settings and profiles is the
    dialogue definition. Dialogue definition consists of a list of nodes which
    are used to create the dialogue.

The nodes are described in more detail based on the example below.
## Example
```yaml
settings: wpm=120
profiles:
    male:
        sounds:
        obi_wan=starwars/obi_wan/male
        grevious=starwars/grevious/male
        variables:
        obi_wan_rank=General
    female:
        sounds:
        obi_wan=starwars/obi_wan/female
        grevious=starwars/grevious/apache_helicopter
        variables:
        obi_wan_rank=Lieutenant

tell:
    >Long time ago in a galaxy far, far away...
tell:
    > ...tere was an epic fight between General Grevious and Obi-Wan Kenobi.

camera:
    10 10 10 90 0
    5 5 5 30 0
    5 10 5 0 0
    5 10 5 0 0
    time:
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
## Settings
**Path:** `settings` (optional, must be on top of the file)

Settings are used to define default properties of some nodes. Available
settings:
- `wpm: float` - default values of words per minute in the dialogue delays.
- `cpm: float` - default value of the characters per minute in the dialogue
    delays. Works only if `wpm` is not defined. Otherwise it's ignored.
- `title_max: int` - **NOT IMPLEMENTED** - maximum length of the title.

## Profiles
**Path:** `profiles` (optional, must be below the `settings`)

The profile nodes contains a list of subnodes with any name, which isn't
reserved for other labels. Every profile contains two sections: `sounds` and
`variables`.

- `profiles->[profile]->sounds` - contains a list of custom properties with
    which file paths which can be later used in the `sound` property of
    message nodes. For example if `obi_wan` property in `sounds` is equal
    to `starwars/obi_wan/male` and there is a message node which defines
    `sound` as `obi_wan:hello.ogg`, then the actual path used for generating
    code from this profile will be `starwars/obi_wan/male/hello.ogg`.
- `profiles->[profile]->variables` - contains a list of variables which can
   be inserted into text of the message nodes. For example if a profile defines
   `obi_wan_title` as `General` and there is a message node which says:
   `>[Grevious] {obi_wan_title} Kenobi!`, the the actual text used in the
    dialogue will be `>[Grevious] General Kenobi!`.

## Dialogue definition

### camera
**Path:** `camera` (must be below the `profiles` cannot be used inside a
timeline of another camera)

The camera node is a special type of dialogue node, which controlls the movment
of the camera. It can only be used in the root timeline of the dialogue.
Camera node has two parts - the list of coordinates and the timeline.

The coordinates (definedt at the top of the content of the node) can be written
in one of 3 formats:
- `<x> <y> <z> <yaw> <pitch>` - for exmaple `1 2 3 45 90`.
- `<x> <y> <z> facing <x1> <y1> <z1>` - example: `1 2 3 facing 4 5 6`
- `<x> <y> <z> facing <selector>` - exmaple: `1 2 3 facing @p`

The coordinate formats match the format used in Minecraft `/tp` command. Long
chains of coordinates that use only first or only third format can have better
interpolation. The rotation values used in the first format don't detect
cycles, so if you write two successive coordinates, where the first one is
using 0 degrees rotation and the second one is using 360 degrees rotation,
the interpolation between these two steps of animation will make the player
do a full rotation.

The `camera->timeline` can either have a `time` property which defines the
duration of the camera movement, or have a list of message nodes. In the latter
case, the camera will use the duration of the sequence of message nodes to
define the duration of the camera movement.

### Message nodes: tell, title, actionbar, blank
**Path:** `[message node]` or `camera->[message node]` (must be below
`profiles`, can be used inside camera timelines)

Message nodes are the main feature of the dialogue. There is 4 types of message
nodes: `tell`, `title`, `actionbar`, and `blank`. They behave in a very similar
way, but have some differences. The main difference is how they are displayed.

- `tell` node displays text usig `tellraw` command.
- `title` node displays the first line using `titleraw ... title` command, and
    the second line using `titleraw ... subtitle`. Adding more lines to the
    title is not supported.
- `actionbar` node displays the text using `titleraw ... actionbar` command. It
    can have only one message.
- `blank` node displays nothing. It's used for running commands, loops etc.
   without showing any message. The blank node doesn't use `wpm` and `cpm`
   properties because there is no text to be used for calculating the delays.

#### Message node properties
Message nodes can use following properties to define their length:
- `wpm: float` - words per minute.
- `cpm: float` - characters per minute. Works only if `wpm` is not defined.
- `time: float` - duration of the message.
- `sound: string` - path to the sound file.

If none of these are defined, the message node will use the default values
from `settings`. If multiple properties are defined, the message will use
the one with the highest priority:
1. local `time`
2. local `wpm`
3. local `cpm`
4. local `sound`
5. settings `wpm`
6. settings `cpm`

Using a reference to a sound which doesn't exist is not an error however it
will print a warning. This is useful when you don't have the sound available
and need to generate placeholder dialogue.

#### Other elements of message nodes
The main part of the message node is the message. Messages start with
`>`. Message nodes can also run commands. Commands in dialogues must use the
`/` prefix.

Message nodes also can have subnodes:
- `run_once` - a list of commands to be executed only onece from the animation.
   When player leaves the game during the dialogue it will start playing again
   including all of the commands. If some commands should never be executed
   twice (even if player exits the game) they should be marked with the
   run_once label. Commands that give the player a reward after quest or change
   the state the game should use this label.
- `schedule` - shedule lets you add a delay to some commands. The schedule
    label requires `time` property to be defined. The scheduled commands run
    with the delay defined in time, after the message node.
- `on_exit` - on exit is a convinient way to put a command after the time of
    the message node. It's the same as putting it in the next message node.

##  Comments
Everything after `##` in a line is a comment.
