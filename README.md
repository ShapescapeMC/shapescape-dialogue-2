# 📝 Description
`shapescape-dialogue-2` is a Python package for generating dialogue and camera
sequences for Minecraft. It's the core of the
[shapescape_dialogue](https://github.com/ShapescapeMC/regolith-filters/tree/master/shapescape_dialogue)
Regolith filter but it can also be used as a standalone tool (not recommended).

# 💿 Installation

> **Note**
>
> If you want to use this package with Regolith, you don't need to install it.

You can install the package with `pip` command which should be available
in your system if you have Python properly installed. Simply use:
```
pip install git+https://github.com/ShapescapeMC/shapescape-dialogue-2
```

If you want to install specific version, for example `0.5.0`, you can pass
the tag name to pip like this:
```
pip install git+https://github.com/ShapescapeMC/shapescape-dialogue-2@0.5.0
```

# ⭐ Usage
In most cases you should use this tool with Regolith. Details related
to Regolith are explained on the
[filter page](https://github.com/ShapescapeMC/regolith-filters/tree/master/shapescape_dialogue)
and in the
[Regolith documentation](https://bedrock-oss.github.io/regolith/). The filter
runs the main script from this package, which can also be used as a standalone
tool. The main benefit of using the filter is that Regolith handles the
deletion of the files when you want to generate them again. The script itself
is not allowed to delete or overwrite any files so without Regolith you have
to do it yourself.

The main script is a command line tool, it should be available in your system
after the installation. All of its features are explained when you run:
```
shapescape-dialogue-2 --help
```
The options that start with `--debug` are for debugging purposes and they're
not important for normal usage. The script expects you to provide the,
source file, the namespace and the output resource pack and behavior pack
directories. When you run with Regolith, these settings are automatically
provided.

# 🔣 Syntax of the dialogue files

## Overview
Dialogue files use custom syntax similar to YAML. A dialogue file can be
divided into 3 sections:
- **settings** (optional) - settings contain a list of global settings of the
   file.
- **profiles** (optional) - profiles are used to generate alternate versions of
    dialogue that differ in sounds and some text.
- **dialogue definition** - dialogue definition consists of a list of nodes
    which are used to create the dialogue.

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
## Settings
Settings define the default values of some properties used later in the code.
Using them is optional. The following settings are supported:
- `wpm: float` - The default words-per-minute value used to determine the
    dialog duration.
- `cpm: float` - The default character-per-minute value used to determine the
    dialog duration. If `wpm` is defined, `cpm` is ignored.
- `title_max: int` - **NOT IMPLEMENTED** - maximum length of the title.
- `tp_selector: string` - the selector used in the `/tp` commands of the camera
   nodes. By default it uses `@a`.

## Profiles
The `profiles` node defines profiles. Each profile is used to generate an
alternate version of the dialog. A profile contains definitions of sound and
text variables. Profiles are useful when you want to have two very similar
dialogs, but with different voice acting or slightly different text (such as a
different character name). A profile can have any name, except for the names
reserved for other types of labels (like "settings", "camera", etc.)

A profile can contain the following nodes:
- `profiles->[profile]->sounds` - `sounds` is a node whose properties define
    the roots of sound files. To refer to the sound path from a profile in the
    dialogue, simply put it into the sound property of a message node before
    the actual sound, separating it with a colon.
    \
    \
    **Example:**\
    In the example above, there is a sound defined as
    `obi_wan=starwars/obi_wan/male`, the `obi_wan` variable is later reused
    in one of the sounds like `obi_wan:hello.ogg`. This means that the dialogue
    will use sound located at `starwars/obi_wan/male/hello.ogg`.
- `profiles->[profile]->variables` - the variables node defines variables to
    be reused in the text of the dialogues.
    \
    \
    **Example:**\
    There is a profile that defines `obi_wan_rank` as `General` and there is a
    message node which says: `>[Grevious] {obi_wan_rank} Kenobi!`, the the
    actual text used in the dialogue is be `>[Grevious] General Kenobi!`.

## Dialogue definition

### camera
The camera node is a special type of dialogue node, which controls the movement
of the camera. It can only be used in the root timeline of the dialogue.
Nesting camera nodes in other camera nodes is not allowed. Camera node has three
parts - the list of coordinates, optional section fo actor paths and the
timeline.

The coordinates can be written in one of 3 formats:
- `<x> <y> <z> <yaw> <pitch>` - for example `1 2 3 45 90`.
- `<x> <y> <z> facing <x1> <y1> <z1>` - example: `1 2 3 facing 4 5 6`
- `<x> <y> <z> facing <selector>` - example: `1 2 3 facing @p`

The coordinate formats match the format used in Minecraft `/tp` command. It's
recommended to use either first or second format for entire camera animation
because it lets the script to smoothly interpolate between frames. Mixing
different formats in the same timeline is allowed but not recommended. While
using the first format, it's important to know that the interpolation treats
the rotations as normal coordinates. So interpolating between 350° and 0° does
almost a full rotation.

The actor paths are the subnodes of the "camera" node. There can be multiple
actor paths in the same camera. The actor path contains a list of coordinates
to animate different entity than the player. Actor path thakes the same
settings asa camera (interpolation_mode and tp_selector) but the "tp_selector"
is required.

The `camera` can either use a `time` property which defines the
duration of the camera movement, or have a list of message nodes in its
sub-node called `timeline`. In the latter case, the camera uses the
duration of the sequence of message nodes to define the duration needed for
camera movement.

The `camera` node also accepts the `interpolation_mode` property, which defines
the type of interpolation used for the camera movement.  The argument accepts
an integer value from 0 to 3. The value refers to the order of the spline
interpolation:
- 0 - no interpolation, discrete jumps between keyframes.
- 1 - linear
- 2 - quadratic
- 3 - cubic
The default value is 3. The interpolation mode value must be lower than the
number of points to interpolate. If not enough points is provided the
interpolation mode is automatically downgraded to the lowest possible value.

The `tp_selector` property of the camera sets the target selector used for the
`/tp` command. By default it's set to `@a`.

### Message nodes: `tell`, `title`, `actionbar`, `blank`
Message nodes are the main feature of the dialogue. They behave in a very
similar way. The main difference is how they are displayed and how many lines
of text they can contain.

- `tell` node displays text using `tellraw` command.
- `title` node displays the first line with `titleraw ... title`, and
    the second line with `titleraw ... subtitle`. It can't contain more than
    two lines.
- `actionbar` node displays the text with `titleraw ... actionbar` command. It
    can contain only one line of text.
- `blank` node displays nothing. It's used for running commands, loops etc.
    The `blank` node requires a `time` or `sound` property as it can't use
    `wpm` or `cpm` to determine the duration because it has no text.

#### Message node properties
Message nodes can use following properties to define their length:
- `wpm: float` - words per minute.
- `cpm: float` - characters per minute.
- `time: float` - duration of the message.
- `sound: string` - path to the sound file.

Some of these properties can also be defined in the settings node. Here is the
priority list used to decide which property to use:
1. local `time`
2. local `wpm`
3. local `cpm`
4. local `sound`
5. settings `wpm`
6. settings `cpm`

Using a reference to a sound which doesn't exist is not an error however it
prints a warning. Such references are useful when you don't have sound
available and need to generate placeholder dialogue.

#### Text and commands
The main part of the message node is the message. Messages start with
`>`. Message nodes can also run commands. Commands in dialogues must use the
`/` prefix. Messages must be defined above the commands.

All Raw JSON text produced by the script uses structure:
```
{"rawtext":[{"translate":"AUTOMATICALLY_ASSIGNED_VALUE","with":["\n"]}]}
```
where `AUTOMATICALLY_ASSIGNED_VALUE` is a translation key assigned by the script.
Note that the `"with":["\n"]` is added so you can use the newline character in
your text (in a same way as in usual Minecraft addon creation). E.g.
`>Hello%1World!` would be displayed in game as:
```
Hello
World!
```



#### The subnodes of message nodes

Message nodes use subnodes for commands that have some additional conditions
for being executed:
- `run_once` - commands in this subsection of a message node are executed only
    once, even if a certain part of the dialogue is reached multiple times.
    This can happen when the world is reloaded while the dialogue is still
    playing. It should be used for commands that are not supposed to be
    executed multiple times for example when the player gets a reward or when
    the state of the game changes.
- `schedule` - schedule lets you run commands with a delay. The schedule
    label requires `time` property to be defined. The timer of the delay starts
    when the message is displayed.
- `on_exit` - on exit is a convenient way to put a command after the time of
    the message node. It's the same as putting it in the next message node.
- `loop` - loop repeats the message while the section of the message node is
    being played. It uses the `time` property to determine the duration of
    the loop.

Internally, the `schedule`, `loop` and `on_exit` commands are just inserted
into the timeline of the Minecraft BP animation. The `run_once` is handled
by generating a tag which marks the commands as executed.

##  Comments
Everything after `##` in a line is a comment.
