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
Settings define the default values of some properties used later in the code. Their use is optional. The following settings are supported:
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
        grevious=starwars/grevious/male
        variables:
        obi_wan_rank=General
    female:
        sounds:
        obi_wan=starwars/obi_wan/female
        grevious=starwars/grevious/apache_helicopter
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
