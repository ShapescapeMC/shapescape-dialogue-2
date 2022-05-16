'''
Parser module implements a parser for custom dialogue syntax.
'''
from __future__ import annotations
import re
from enum import Enum, auto
from typing import Literal, NamedTuple, Optional, Any, List
from collections import deque

class ParseError(Exception):
    '''
    Raised when the parser encounters an error.
    '''

class TokenType(Enum):
    # Fake tokens for indentaiton
    INDENT = auto()
    DEDENT = auto()

    # Labels
    SETTINGS = auto()
    TIME = auto()
    WAIT = auto()
    SCHEDULE = auto()
    ON_EXTI = auto()
    TELL = auto()
    LOOP = auto()
    TITLE = auto()
    SOUND = auto()
    DIALOGUE = auto()
    DIALOGUE_OPTION = auto()
    DIALOGUE_EXIT = auto()
    CAMERA = auto()
    RUN_ONCE = auto()
    ON_EXIT = auto()

    # Other (more complex) tokens
    SETTING = auto()
    COORDINATES = auto()
    COMMAND = auto()
    TEXT = auto()

class Token(NamedTuple):
    '''
    Represents a token and it's parsed value
    '''
    token_type: TokenType
    value: Any
    line_number: int

# Token values
class Setting(NamedTuple):
    '''A setting of a label'''
    name: str
    value: str

class Coordinates(NamedTuple):
    '''Normal coordinates x y z [ry rx]'''
    x: float
    y: float
    z: float
    y_rot: Optional[float] = None
    x_rot: Optional[float] = None

class CoordinatesFacingEntity(NamedTuple):
    '''Coordinates and direction facing entity'''
    x: float
    y: float
    z: float
    facing_target: str

class CoordinatesFacingCoordinates(NamedTuple):
    '''Coordinates and direction facing another location'''
    x: float
    y: float
    z: float
    facing_x: float
    facing_y: float
    facing_z: float

# Helper classes
class Indent(NamedTuple):
    '''
    Class that represents indentation. This class is not returned as a part
    of the abstract syntax tree (INDENT and DEDENT tokens are used instead).
    This class is only used for getting the indent value in a well organized
    way.
    '''
    depth: int
    indent_type: Literal['space', 'tab', 'unknown']

    @staticmethod
    def of_string(indent_string: str) -> Indent:
        '''Returns an indentation object of a string.'''
        depth = 0
        indent_type = "unknown"
        if indent_string.startswith('\t'):
            indent_type = 'tab'
            while len(indent_string) > depth and indent_string[depth] in '\t ':
                if indent_string[depth] == ' ':
                    raise ParseError("Mixed indentation") 
                depth += 1
        elif indent_string.startswith(' '):
            indent_type = 'space'
            while len(indent_string) > depth and indent_string[depth] in '\t ':
                if indent_string[depth] == '\t':
                    raise ParseError("Mixed indentation") 
                depth += 1
        return Indent(depth, indent_type)

# Helper patterns for matching common parts of synteax like variables and
# numbers
var_pattern = r'[a-zA-Z_]+[a-zA-Z_0-9]*'
float_pattern = r'[+-]?(?:[0-9]+(?:[.][0-9]*)?|[.][0-9]+)'

SCANNER = re.Scanner([
    (r'\s+', lambda s, t: None),
    (r'settings:', lambda s, t: (TokenType.SETTINGS, t)),
    (r'time:', lambda s, t: (TokenType.TIME, t)),
    (r'wait:', lambda s, t: (TokenType.WAIT, t)),
    (r'schedule:', lambda s, t: (TokenType.SCHEDULE, t)),
    (r'on_exti:', lambda s, t: (TokenType.ON_EXTI, t)),
    (r'tell:', lambda s, t: (TokenType.TELL, t)),
    (r'loop:', lambda s, t: (TokenType.LOOP, t)),
    (r'title:', lambda s, t: (TokenType.TITLE, t)),
    (r'sound:', lambda s, t: (TokenType.SOUND, t)),
    (r'camera:', lambda s, t: (TokenType.CAMERA, t)),
    (r'run_once:', lambda s, t: (TokenType.RUN_ONCE, t)),
    (r'on_exit:', lambda s, t: (TokenType.ON_EXIT, t)),
    (r'dialogue:', lambda s, t: (TokenType.DIALOGUE, t)),
    (r'dialogue_option:', lambda s, t: (TokenType.DIALOGUE_OPTION, t)),
    (r'dialogue_exit:', lambda s, t: (TokenType.DIALOGUE_EXIT, t)),
    (
        r'('+var_pattern+')=(\S+)',
        lambda s, t: (TokenType.SETTING, Setting(s.match[1], s.match[2]))
    ),
    (
        f'({float_pattern}) ({float_pattern}) ({float_pattern}) facing'
        r' \S+',
        lambda s, t: (
            TokenType.COORDINATES,
            CoordinatesFacingCoordinates(
                float(s.match[1]), float(s.match[2]), float(s.match[3]),
                float(s.match[4]) if s.match[4] is not None else None,
                float(s.match[5]) if s.match[5] is not None else None,
                float(s.match[5]) if s.match[5] is not None else None,
            )
        )
    ),
    (
        f'({float_pattern}) ({float_pattern}) ({float_pattern}) facing'
            f' ({float_pattern}) ({float_pattern}) ({float_pattern})',
        lambda s, t: (
            TokenType.COORDINATES,
            CoordinatesFacingEntity(
                float(s.match[1]), float(s.match[2]), float(s.match[3]),
                s.match[4]
            )
        )
    ),
    (
        f'({float_pattern}) ({float_pattern}) ({float_pattern})'
            f'(?: ({float_pattern}) ({float_pattern}))?',
        lambda s, t: (
            TokenType.COORDINATES,
            Coordinates(
                float(s.match[1]), float(s.match[2]), float(s.match[3]),
                float(s.match[4]) if s.match[4] is not None else None,
                float(s.match[5]) if s.match[5] is not None else None,
            )
        )
    ),
    (r'/.+', lambda s, t: (TokenType.COMMAND, t[1:])),
    (r'.+', lambda s, t: (TokenType.TEXT, t[1:])),

])

def tokenize(source: List[str]) -> List[Token]:
    '''
    Splits a source file into tokens.
    '''
    line_number = 0
    tokens: List[Token] = []
    indent_stack = deque((0,))
    indent_type = 'unknown'
    for line in source:
        line_number += 1
        # Remove the new line characters and other whitespaces from the end of
        # the line if they exists
        line = line.rstrip(" ")
        # Skip empty lines
        if line.strip() == '':
            continue
        # Check the indentation rules
        try:
            indent = Indent.of_string(line)
        except ParseError as e:
            raise ParseError(f"{e} on line {line_number}:\n\n{line}\n")
        if indent_type != 'unknown' and indent_type != indent.indent_type:
            raise ParseError(f"Mixed indentation at line {line_number}:\n\n{line}\n")
        # We don't need the whitespaces in the line anymore, remove them before
        # further processing
        line = line.lstrip()
        # Insert INDENT or DEDENT tokens if necessary
        if indent.depth > indent_stack[-1]:
            indent_stack.append(indent.depth)
            tokens.append(Token(TokenType.INDENT, None, line_number))
        elif indent.depth < indent_stack[-1]:
            while indent.depth < indent_stack[-1]:
                indent_stack.pop()
                tokens.append(Token(TokenType.DEDENT, None, line_number))
            if indent.depth != indent_stack[-1]:
                raise ParseError(f"Invalid indentation at line {line_number}:\n\n{line}\n")
        # Tokenize the line
        tokenized_text, reminder = SCANNER.scan(line)
        if reminder != '':
            raise ParseError(f"Unable to tokenize line {line_number}:\n\n{line}\n")
        for token in tokenized_text:
            tokens.append(Token(token[0], token[1], line_number))
    return tokens
