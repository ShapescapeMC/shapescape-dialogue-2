'''
This scripts generates/updates the doctree in the documentation and the
README file.
'''
from pathlib import Path
from typing import List, Tuple

class DocTreeGeneratorException(Exception):
    pass

def get_page_name(path: Path):
    '''
    Gets the name of the page based on the first title (line with '#' prefix).
    The page should have at least one page or the function will raise
    DocTreeGeneratorException.

    :param path: the path to the .md file
    '''
    with path.open('r', encoding='utf8') as f:
        lines = f.readlines()
    for line in lines:
        if line.startswith('#'):
            return line[1:].strip()
    raise DocTreeGeneratorException("Unable to find a line that starts with '#'")

def md_link(text: str, link: str):
    '''
    Returns markdown formatted link.
    :param text: the text of the link
    :param link: the target of the link
    '''
    return f"[{text}]({link})"

def delete_md_section(section_name: str, lines: List[str]):
    '''
    Deletes the section of an MD file marked with comments that follow the
    pattern:
    <!-- section_name start-->
    ...
    <!-- section_name end-->
    If the section is not found, the function will return lines.

    :param section_name: the name of the section of the text to delete
    :param lines: the text
    '''
    start = -1
    end = -1
    for i, line in enumerate(lines):
        if line.strip() == f"<!-- {section_name} start -->" and start == -1:
            start = i
        if line.strip() == f"<!-- {section_name} end -->" and end == -1:
            end = i
        if start != -1 and end != -1:
            return lines[:start] + lines[end+1:]
    if start == -1 and end != -1:
        raise DocTreeGeneratorException(
            f"Unable to find start of the section {section_name}")
    if end == -1 and start != -1:
        raise DocTreeGeneratorException(
            f"Unable to find end of the section {section_name}")
    if start > end:
        raise DocTreeGeneratorException(
            f"The starting index of the section {section_name} is greater than"
            "the ending index.")
    # Nothing to delete
    return lines

def generate_doctree(paths: List[Path]) -> List[str]:
    '''
    Generates the lines of the doctree. The doctree follows the pattern:
    <!-- doctree start -->
    - [Page name](page_link)
    ...
    <!-- doctree end -->
    The paths of the doctree are sorted alphabetically.

    :param paths: the list of the paths to include in the doctree
    '''

    doctree_items: List[Tuple[str, str]] = []
    # The list of files
    for p in paths:
        link = "/" + p.as_posix()
        text = get_page_name(p)
        doctree_items.append((text, link))
    doctree_items.sort()
    return [
        *[f"- {md_link(text, link)}\n" for text, link in doctree_items],
    ]

def generate_list_of_titles(path: Path):
    with path.open('r', encoding='utf8') as f:
        lines = f.readlines()
    result: List[str] = []
    for line in lines:
        if line.startswith('#'):
            # Count the number of '#' characters
            level = len(line) - len(line.lstrip('#'))
            if level == 1:  # Don't include the main title
                continue
            title = line[level:].strip()
            title_link = "".join([  # Ugly hack to only allow alphanumerics, '-' and '_'
                i for i in
                title.lower().replace(' ', '-')
                if i in 'abcdefghijklmnopqrstuvwxyz0123456789-_'
            ])
            result.append(f"{'  ' * (level - 2)}- [{title}](#{title_link})\n")
    return result

def main():
    doc_paths = [
        p for p in Path("docs").rglob("*.md")
    ]
    doctree = generate_doctree(doc_paths)
    print("NEW DOCTREE CONTENT:")
    print("".join(doctree))
    for path in doc_paths:
        titles = generate_list_of_titles(path)
        full_doctree = (
            [
                f"<!-- doctree start -->\n",
                "Table of contents:\n"
            ] +
            doctree +
            ["\nIn this article you can read about:\n"] +
            titles +
            [f"<!-- doctree end -->\n"]
        )
        with path.open('r', encoding='utf8') as f:
            lines = f.readlines()
        lines = full_doctree + delete_md_section("doctree", lines)
        with path.open('w', encoding='utf8') as f:
            f.writelines(lines)

if __name__ == "__main__":
    main()