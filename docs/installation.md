<!-- doctree start -->
Table of contents:
- [# Writing the Documentation](/docs/writing_the_documentation.md)
- [About the documentation](/docs/README.md)
- [Installation as Regolith Filter](/docs/installation.md)
- [Syntax of the dialogue files](/docs/syntax.md)
- [Usage](/docs/usage_as_module.md)
- [Usage](/docs/usage_with_regolith_filter.md)

In this article you can read about:
- [Installation Steps](#installation-steps)
- [Configuration settings](#configuration-settings)
<!-- doctree end -->
# Installation as Regolith Filter
This module is a component of the Shapescape Dialogue filter. To install the Shapescape Dialogue Filter, follow the steps below. If you prefer to install it as a Python module, you can follow the instructions in the [Installation as Python Module](#Installation-as-Python-Module) section.

## Installation Steps
**1.** Install the filter with command:
```
regolith install github.com/Shapescape-Software/regolith-filters/shapescape_dialogue
```

You can also set up the Shapescape resolver by once typing this command:
```
regolith config resolvers github.com/Shapescape-Software/public_regolith_resolver/resolver.json
```

After that you can use this command to install this filter:
```
regolith install shapescape_dialogue
```

**2.** Add the filter to the `filters` list in the `config.json` file of the Regolith
project:
```json
                    {
                        "filter": "shapescape_dialogue",
                        "settings": {
                            "namespace": "shapescape"
                        }
                    }
```

## Configuration settings
- `namespace: str` - the namespace to be added to the name of the entities
  generated from the script. The default value is `shapescape` you don't need
  to specify it.


You can now either learn about the [usage as part of the regolith filter](/docs/usage_with_regolith_filter.md)  or learn about the [syntax](/docs/syntax.md) of dialogue files.



# Installation as Python Module

> **Note**
>
> There is no need to install this package if you are using Regolith. 

You can install the package using the `pip` command, which should be available on your system if you have Python properly installed.  Simply use:
```
pip install git+https://github.com/Shapescape-Software/shapescape-dialogue-module
```

If you want to install a specific version, for example `0.5.0`, you can pass the tag name to pip like this:
```
pip install git+https://github.com/Shapescape-Software/shapescape-dialogue-module@0.5.0
```


You can now either learn about the [usage as python module](/docs/usage_as_module.md)  or learn about the [syntax](/docs/syntax.md) of dialogue files.
