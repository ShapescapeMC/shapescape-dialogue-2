'''
Parser module implements a parser for custom dialogue syntax.
'''
from __future__ import annotations
from msilib.schema import Dialog

import re
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import (
    Any, Deque, List, Literal, NamedTuple, Optional, Union)


class ParseError(Exception):
    '''
    Raised when the parser encounters an error.
    '''
    @staticmethod
    def from_unexpected_token(
            token: Token, *expected: TokenType) -> ParseError:
        return ParseError(
            f"Unexpected token type {token.token_type} at line "
            f"{token.line_number}. Expected one of:\n"
            +
            f"\t- {t.descriptive_str()}\n" for t in expected
        )

    @staticmethod
    def from_duplicate_token(token: Token, duplicate: Token) -> ParseError:
        return ParseError(
            f"Duplicate {token.token_type.descriptive_str()} at line "
            f"{token.line_numbera} and line {duplicate.line_number}."
        )

class TokenType(Enum):
    # Fake tokens for indentaiton
    INDENT = auto()
    DEDENT = auto()
    EOF = auto()

    # Labels
    SETTINGS = auto()
    SOUND_PROFILES = auto()
    TIME = auto()
    BLANK = auto()
    SCHEDULE = auto()
    ON_EXTI = auto()
    TELL = auto()
    LOOP = auto()
    TITLE = auto()
    DIALOGUE = auto()
    DIALOGUE_OPTION = auto()
    DIALOGUE_EXIT = auto()
    CAMERA = auto()
    RUN_ONCE = auto()
    ON_EXIT = auto()

    # Arbitrarily named labels (tokenizer categorizes them as text but they
    # have different meaning in the parser)
    SOUND_PROFILE = auto()
    SOUND_PROFILE_VARIANT = auto()

    # Other (more complex) tokens
    SETTING = auto()
    COORDINATES_ROTATED = auto()
    COORDINATES_FACING_COORDINATES = auto()
    COORDINATES_FACING_ENTITY = auto()
    COMMAND = auto()
    TEXT = auto()

    def descriptive_str(self) -> str:
        '''
        Returns descriptive string which can be used for pretty printing in
        error messages.
        '''
        # Pretty print the labels
        if self == TokenType.SETTINGS:
            return '"settings:"'
        if self == TokenType.TIME:
            return '"time:"'
        if self == TokenType.BLANK:
            return '"blank:"'
        if self == TokenType.SCHEDULE:
            return '"schedule:"'
        if self == TokenType.ON_EXTI:
            return '"on_exti:"'
        if self == TokenType.TELL:
            return '"tell:"'
        if self == TokenType.LOOP:
            return '"loop:"'
        if self == TokenType.TITLE:
            return '"title:"'
        if self == TokenType.DIALOGUE:
            return '"dialogue:"'
        if self == TokenType.DIALOGUE_OPTION:
            return '"dialogue_option:"'
        if self == TokenType.DIALOGUE_EXIT:
            return '"dialogue_exit:"'
        if self == TokenType.CAMERA:
            return '"camera:"'
        if self == TokenType.RUN_ONCE:
            return '"run_once:"'
        if self == TokenType.ON_EXIT:
            return '"on_exit:"'
        # Other tokens
        if self == TokenType.SETTING:
            return "setting pair (<name>=<value>)"
        if self == TokenType.COORDINATES_ROTATED:
            return "coordinates (<x> <y> <z> [<ry> <rx>])"
        if self == TokenType.COORDINATES_FACING_COORDINATES:
            return "coordinates (<x> <y> <z> <facing_x> <facing_y> <facing_z>)"
        if self == TokenType.COORDINATES_FACING_ENTITY:
            return "coordinates (<x> <y> <z> facing <entity>)"
        if self == TokenType.COMMAND:
            return "command (/<command>)"
        if self == TokenType.TEXT:
            return "text (any string)"
        # Fake tokens
        if self == TokenType.INDENT:
            return "indentation"
        if self == TokenType.DEDENT:
            return "dedentation"
        if self == TokenType.EOF:
            return "end of file"
        # Unimplemented tokens return the string representation
        return f"{self}"

# Labels that can't be categorized by the tokenizer
ArbitrailyNamedLabel = Literal[
    TokenType.SOUND_PROFILE,
    TokenType.SOUND_PROFILE_VARIANT]

class Token(NamedTuple):
    '''
    Represents a token and it's parsed value
    '''
    token_type: TokenType
    value: Any
    line_number: int

    def get_label_token(self, new_type: ArbitrailyNamedLabel) -> Token:
        '''
        If current token is a text token tries to return a token with same
        properties but with different type (new_type, an arbitrarily named
        label).
        '''
        if self.token_type != TokenType.TEXT:
            raise ParseError.from_unexpected_token(self, new_type)
        return Token(new_type, self.value, self.line_number)

SettingsList = List[Token]

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
        indent_type: Literal['space', 'tab', 'unknown'] = "unknown"
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

TOKENIZER = re.Scanner([  # type: ignore
    # Ignore blank lines and comments
    (r'\s+', lambda s, t: None),
    (r'##.+', lambda s, t: None),

    (r'settings:', lambda s, t: (TokenType.SETTINGS, t)),
    (r'sound_profiles:', lambda s, t: (TokenType.SOUND_PROFILES, t)),
    (r'time:', lambda s, t: (TokenType.TIME, t)),
    (r'blank:', lambda s, t: (TokenType.BLANK, t)),
    (r'schedule:', lambda s, t: (TokenType.SCHEDULE, t)),
    (r'on_exti:', lambda s, t: (TokenType.ON_EXTI, t)),
    (r'tell:', lambda s, t: (TokenType.TELL, t)),
    (r'loop:', lambda s, t: (TokenType.LOOP, t)),
    (r'title:', lambda s, t: (TokenType.TITLE, t)),
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
            f' ({float_pattern}) ({float_pattern}) ({float_pattern})',
        lambda s, t: (
            TokenType.COORDINATES_FACING_COORDINATES,
            CoordinatesFacingCoordinates(
                float(s.match[1]), float(s.match[2]), float(s.match[3]),
                float(s.match[4]), float(s.match[5]), float(s.match[5]),
            )
        )
    ),
    (
        f'({float_pattern}) ({float_pattern}) ({float_pattern}) facing'
            r' \S+',
        lambda s, t: (
            TokenType.COORDINATES_FACING_ENTITY,
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
            TokenType.COORDINATES_ROTATED,
            Coordinates(
                float(s.match[1]), float(s.match[2]), float(s.match[3]),
                float(s.match[4]) if s.match[4] is not None else None,
                float(s.match[5]) if s.match[5] is not None else None,
            )
        )
    ),
    (r'/.+', lambda s, t: (TokenType.COMMAND, t[1:])),
    (r'.+', lambda s, t: (TokenType.TEXT, t)),

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
        tokenized_text, reminder = TOKENIZER.scan(line)
        if reminder != '':
            raise ParseError(f"Unable to tokenize line {line_number}:\n\n{line}\n")
        for token in tokenized_text:
            tokens.append(Token(token[0], token[1], line_number))
    # Insert DEDENT tokens if necessary
    while len(indent_stack) > 1:
        indent_stack.pop()
        tokens.append(Token(TokenType.DEDENT, None, line_number))
    # Insert EOF token
    tokens.append(Token(TokenType.EOF, None, line_number))
    return tokens

# AST builder
@dataclass
class RootAstNode:
    timeline: List[Union[MessageNode, DialogueNode]]
    settings: Optional[SettingsNode] = None
    sound_profiles: Optional[SoundProfilesNode] = None

    @staticmethod
    def from_token_stack(tokens: Deque[Token]):
        token = tokens[0]
        # Settings
        settings = None
        if token.token_type is TokenType.SETTINGS:
            settings = SettingsNode.from_token_stack(tokens)
        # Sound profiles
        sound_profiles = None
        if token.token_type is TokenType.SOUND_PROFILE:
            sound_profiles = SoundProfilesNode.from_token_stack(tokens)
        # Timeline
        timeline: List[Union[MessageNode, DialogueNode]] = []
        while token.token_type is not TokenType.EOF:
            if token.token_type in (
                    TokenType.TELL, TokenType.TITLE, TokenType.BLANK):
                timeline.append(MessageNode.from_token_stack(tokens))
            elif token.token_type is TokenType.DIALOGUE:
                raise NotImplementedError()
            else:
                raise ParseError.from_unexpected_token(
                    token, TokenType.TELL, TokenType.BLANK, TokenType.TITLE,
                    TokenType.DIALOGUE, TokenType.EOF)
        return RootAstNode(timeline, settings, sound_profiles)

@dataclass
class SettingsNode:
    settings: SettingsList
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> SettingsNode:
        token = tokens.popleft()
        if token.token_type is not TokenType.SETTINGS:
            raise ParseError.from_unexpected_token(
                token, TokenType.SETTINGS)
        settings = SettingsNode.parse_settings(tokens)
        return SettingsNode(settings)

    @staticmethod
    def parse_settings(tokens: Deque[Token]) -> SettingsList:
        '''
        Parse settings is a helper function used to parse settings of any
        label that allows having them.
        '''
        token = tokens[0]
        settings: SettingsList = []
        while token.token_type is TokenType.SETTING:
            settings.append(tokens.popleft())
            token = tokens[0]
        return settings

@dataclass
class SoundProfilesNode:
    sound_profiles: List[SoundProfileNode]
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> SoundProfilesNode:
        token = tokens.popleft()
        if token.token_type is not TokenType.SOUND_PROFILES:
            raise ParseError.from_unexpected_token(
                token, TokenType.SOUND_PROFILES)
        token = tokens[0]
        # Expect indentation or finish parsing message node
        token = tokens[0]
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
        else:
            return SoundProfilesNode([])
        sound_profiles: List[SoundProfileNode] = []
        while token.token_type == TokenType.TEXT:
            sound_profiles.append(SoundProfileNode.from_token_stack(tokens))
            token = tokens[0]
        # Expect DEDENT or EOF, don't pop EOF
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        elif token.token_type is not TokenType.EOF:  # not DEDENT and not EOF
            raise ParseError.from_unexpected_token(
                token, TokenType.DEDENT, TokenType.EOF)
        return SoundProfilesNode(sound_profiles)

@dataclass
class SoundProfileNode:
    name: Token
    sound_profile_variant: List[SoundProfileVariant]
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> SoundProfileNode:
        token = tokens.popleft()
        token = token.get_label_token(TokenType.SOUND_PROFILE)
        name = token
        # Expect indentation or finish parsing message node
        token = tokens[0]
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
        else:
            return SoundProfileNode(name, [])
        sound_profile_variant: List[SoundProfileVariant] = []
        while token.token_type == TokenType.TEXT:
            sound_profile_variant.append(
                SoundProfileVariant.from_token_stack(tokens))
            token = tokens[0]
        # Expect DEDENT or EOF, don't pop EOF
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        elif token.token_type is not TokenType.EOF:  # not DEDENT and not EOF
            raise ParseError.from_unexpected_token(
                token, TokenType.DEDENT, TokenType.EOF)
        return SoundProfileNode(name, sound_profile_variant)

@dataclass
class SoundProfileVariant:
    name: Token
    settings: SettingsList
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> SoundProfileVariant:
        token = tokens.popleft()
        token = token.get_label_token(TokenType.SOUND_PROFILE_VARIANT)
        name = token
        settings = SettingsNode.parse_settings(tokens)
        return SoundProfileVariant(name, settings)

@dataclass
class MessageNode:
    node_type: Literal["tell", "blank", "title"]
    text_nodes: List[TextNode]
    command_nodes: List[CommandNode]
    schedule_nodes: List[ScheduleNode]
    settings: SettingsList
    run_once_node: Optional[RunOnceNode] = None
    on_exit_node: Optional[OnExitNode] = None

    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> MessageNode:
        token = tokens.popleft()
        node_type: Literal["tell", "blank", "title"]
        if token.token_type is TokenType.TELL:
            node_type = "tell"
        elif token.token_type is TokenType.BLANK:
            node_type = "blank"
        elif token.token_type is TokenType.TITLE:
            node_type = "title"
        else:
            raise ParseError.from_unexpected_token(
                token, TokenType.TELL, TokenType.BLANK, TokenType.TITLE)
        # Settings
        settings: SettingsList = []
        if token.token_type is TokenType.SETTINGS:
            settings = SettingsNode.parse_settings(tokens)
        # Expect indentation or finish parsing message node
        token = tokens[0]
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
        else:
            return MessageNode(node_type, [], [], [], settings)
        # Text nodes
        text_nodes = []
        token = tokens[0]
        if node_type != 'blank':  # Blank nodes don't accept text
            while token.token_type is TokenType.TEXT:
                text_nodes.append(TextNode.from_token_stack(tokens))
                token = tokens[0]
        # Command nodes
        command_nodes = []
        while token.token_type is TokenType.COMMAND:
            command_nodes.append(CommandNode.from_token_stack(tokens))
            token =  tokens[0]
        # Run once, schedule, and/or exit nodes
        run_once_node: Optional[RunOnceNode] = None
        registered_run_once_token: Optional[Token] = None  # used for errrors
        on_exit_node: Optional[OnExitNode] = None
        registered_exit_token: Optional[Token] = None  # used for errors
        schedule_nodes: List[ScheduleNode] = []
        while token.token_type in (
                TokenType.SCHEDULE, TokenType.RUN_ONCE, TokenType.ON_EXIT):
            # Run once node
            if token.token_type is TokenType.RUN_ONCE:
                if registered_run_once_token is not None:
                    raise ParseError.from_duplicate_token(
                        token, registered_run_once_token)
                registered_run_once_token = token
                run_once_node = RunOnceNode.from_token_stack(tokens)
            # On exit node
            if token.token_type is TokenType.ON_EXIT:
                if registered_exit_token is not None:
                    raise ParseError.from_duplicate_token(
                        token, registered_exit_token)
                registered_exit_token = token
                on_exit_node = OnExitNode.from_token_stack(tokens) 
            # Shedule nodes
            if token.token_type is TokenType.SCHEDULE:
                schedule_nodes.append(ScheduleNode.from_token_stack(tokens))
        # Expect DEDENT or EOF, don't pop EOF
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        elif token.token_type is not TokenType.EOF:  # not DEDENT and not EOF
            raise ParseError.from_unexpected_token(
                token, TokenType.DEDENT, TokenType.EOF)
        return MessageNode(
            node_type, text_nodes, command_nodes, schedule_nodes, settings,
            run_once_node, on_exit_node)


@dataclass
class DialogueNode:
    text: TextNode
    dialogue_options: List[DialogueOptionNode]
    dialogue_exit: Optional[DialogueOptionNode]
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> DialogueNode:
        raise NotImplementedError()

@dataclass
class DialogueOptionNode:
    text_nodes: List[TextNode]
    command_nodes: List[CommandNode]
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> DialogueOptionNode:
        raise NotImplementedError()

@dataclass
class CameraNode:
    coordinates: List[CoordinateNode]
    time: Optional[TimeNode] = None
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> CameraNode:
        token = tokens.popleft()
        if token.token_type is not TokenType.CAMERA:
            raise ParseError.from_unexpected_token(
                token, TokenType.CAMERA)
        # Expect indentation or finish parsing camera node
        token = tokens[0]
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
        else:
            return CameraNode([], None)
        # Coordinates
        coordinates = []
        token = tokens[0]
        while token.token_type is (
                TokenType.COORDINATES_ROTATED,
                TokenType.COORDINATES_FACING_COORDINATES,
                TokenType.COORDINATES_FACING_ENTITY):
            coordinates.append(CoordinateNode.from_token_stack(tokens))
            token = tokens[0]
        # Time
        time: Optional[TimeNode] = None
        if token.token_type is TokenType.TIME:
            time = TimeNode.from_token_stack(tokens)
        # Expecte DEDENT or EOF, don't pop EOF
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        elif token.token_type is not TokenType.EOF:  # not DEDENT and not EOF
            raise ParseError.from_unexpected_token(
                token, TokenType.DEDENT, TokenType.EOF)
        return CameraNode(coordinates, time)

@dataclass
class TimeNode:
    settings: SettingsList
    messages: List[MessageNode]

    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> TimeNode:
        token = tokens.popleft()
        if token.token_type is not TokenType.TIME:
            raise ParseError.from_unexpected_token(
                token, TokenType.TIME)
        # Settings
        settings: SettingsList = []
        if token.token_type is TokenType.SETTINGS:
            settings = SettingsNode.parse_settings(tokens)
        # Expect indentation or finish parsing time node
        token = tokens[0]
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
        else:
            return TimeNode(settings, [])
        # Message nodes
        messages: List[MessageNode] = []
        token = tokens[0]
        while token.token_type in (
                TokenType.TELL, TokenType.TITLE, TokenType.BLANK):
            messages.append(MessageNode.from_token_stack(tokens))
            token = tokens[0]
        # Expect DEDENT or EOF, don't pop EOF
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        elif token.token_type is not TokenType.EOF:
            raise ParseError.from_unexpected_token(
                token, TokenType.DEDENT, TokenType.EOF)
        return TimeNode(settings, messages)

@dataclass
class CoordinateNode:
    coordinates: Token
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> CoordinateNode:
        token = tokens.popleft()
        crds_tokens = (
            TokenType.COORDINATES_ROTATED,
            TokenType.COORDINATES_FACING_COORDINATES,
            TokenType.COORDINATES_FACING_ENTITY)
        if token.token_type not in crds_tokens:
            raise ParseError.from_unexpected_token(token, *crds_tokens)
        return CoordinateNode(token)

@dataclass
class TextNode:
    text: Token
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> TextNode:
        token = tokens.popleft()
        if token.token_type is not TokenType.TEXT:
            raise ParseError.from_unexpected_token(
                token, TokenType.TEXT)
        return TextNode(token)

@dataclass
class CommandNode:
    command: Token
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> CommandNode:
        token = tokens.popleft()
        if token.token_type is not TokenType.COMMAND:
            raise ParseError.from_unexpected_token(
                token, TokenType.COMMAND)
        return CommandNode(token)

@dataclass
class RunOnceNode:
    command_nodes: List[CommandNode]
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> RunOnceNode:
        token = tokens.popleft()
        if token.token_type is not TokenType.RUN_ONCE:
            raise ParseError.from_unexpected_token(
                token, TokenType.RUN_ONCE)
        # Expect indentation or finish parsing run once node
        token = tokens[0]
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
        else:
            return RunOnceNode([])
        # Command nodes
        command_nodes = []
        token = tokens[0]
        while token.token_type is TokenType.COMMAND:
            command_nodes.append(CommandNode.from_token_stack(tokens))
            token = tokens[0]
        # Expect DEDENT or EOF, don't pop EOF
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        elif token.token_type is not TokenType.EOF:
            raise ParseError.from_unexpected_token(
                token, TokenType.DEDENT, TokenType.EOF)
        return RunOnceNode(command_nodes)

@dataclass
class ScheduleNode:
    command_nodes: List[CommandNode]
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> ScheduleNode:
        token = tokens.popleft()
        if token.token_type is not TokenType.SCHEDULE:
            raise ParseError.from_unexpected_token(
                token, TokenType.SCHEDULE)
        # Expect indentation or finish parsing schedule node
        token = tokens[0]
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
        else:
            return ScheduleNode([])
        # Command nodes
        command_nodes = []
        token = tokens[0]
        while token.token_type is TokenType.COMMAND:
            command_nodes.append(CommandNode.from_token_stack(tokens))
            token = tokens[0]
        # Expect DEDENT or EOF, don't pop EOF
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        elif token.token_type is not TokenType.EOF:
            raise ParseError.from_unexpected_token(
                token, TokenType.DEDENT, TokenType.EOF)
        return ScheduleNode(command_nodes)

@dataclass
class OnExitNode:
    command_nodes: List[CommandNode]
    @staticmethod
    def from_token_stack(tokens: Deque[Token]) -> OnExitNode:
        token = tokens.popleft()
        if token.token_type is not TokenType.ON_EXIT:
            raise ParseError.from_unexpected_token(
                token, TokenType.ON_EXIT)
        # Expect indentation or finish parsing on exit node
        token = tokens[0]
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
        else:
            return OnExitNode([])
        # Command nodes
        command_nodes = []
        token = tokens[0]
        while token.token_type is TokenType.COMMAND:
            command_nodes.append(CommandNode.from_token_stack(tokens))
            token = tokens[0]
        # Expect DEDENT or EOF, don't pop EOF
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        elif token.token_type is not TokenType.EOF:
            raise ParseError.from_unexpected_token(
                token, TokenType.DEDENT, TokenType.EOF)
        return OnExitNode(command_nodes)


# The main AST builder function
def build_ast(tokens: List[Token]) -> RootAstNode:
    '''
    Builds an abstract syntax tree from a list of tokens. 
    '''
    tokens_stack = deque(tokens)
    return RootAstNode.from_token_stack(tokens_stack)
