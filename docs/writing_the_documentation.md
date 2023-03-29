<!-- doctree start -->
Table of contents:
- [# Writing the Documentation](/docs/writing_the_documentation.md)
- [About the documentation](/docs/README.md)
- [Installation as Regolith Filter](/docs/installation.md)
- [Syntax of the dialogue files](/docs/syntax.md)
- [Usage](/docs/usage_as_module.md)
- [Usage](/docs/usage_with_regolith_filter.md)

In this article you can read about:
- [Writing the Documentation](#writing-the-documentation)
<!-- doctree end -->
## Writing the Documentation

All of the documentation files are saved in the "docs" directory of this repository. We chose this solution over a Wiki because it is easier to maintain and allows you to easily access documentation for any version of the program.

The list of pages at the top of the documentation is automatically generated with the `generate_doctree.py` script. If you add or remove a page, please run the script to update the list. The first title of each page is used as the name in the doctree.

When creating links within the documents, please use paths relative to the root of this project. For example, a link to this file would be formatted as:

```
[About the Documentation](/docs/README.md)
```

This ensures that links in the documentation remain functional even for older versions of the filter.