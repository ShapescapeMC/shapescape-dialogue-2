'''
Parser module implements a parser for custom dialogue syntax.
'''
from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Literal, NamedTuple, Optional, Union


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
            "".join(f"\t- {t.descriptive_str()}\n" for t in expected)
        )

    @staticmethod
    def from_unexpected_token_value(
            token: Token, expected: str) -> ParseError:
        return ParseError(
            f"Unexpected token value {token.value} of token type "
            f"{token.token_type} at line "
            f"{token.line_number}. Expected: {expected}")

    @staticmethod
    def from_duplicate_token(token: Token, duplicate: Token) -> ParseError:
        return ParseError(
            f"Duplicate {token.token_type.descriptive_str()} at line "
            f"{token.line_number} and line {duplicate.line_number}."
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
    ACTIONBAR = auto()
    DIALOGUE = auto()
    DIALOGUE_OPTION = auto()
    DIALOGUE_EXIT = auto()
    CAMERA = auto()
    RUN_ONCE = auto()
    ON_EXIT = auto()
    NAMED_LABEL = auto()  # any kind of label with custom name

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
        if self == TokenType.ACTIONBAR:
            return '"actionbar:"'
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

class Token(NamedTuple):
    '''
    Represents a token and it's parsed value
    '''
    token_type: TokenType
    value: Any
    line_number: int

    def get_str_from_named_label_token(self) -> str:
        '''
        Validates a token for having 'str' as it's value, and the token type
        TEXT and if it succeeds it returns the 'str' value.
        '''
        if self.token_type != TokenType.NAMED_LABEL:
            raise ParseError.from_unexpected_token(self, TokenType.NAMED_LABEL)
        if not isinstance(self.value, str):
            raise ParseError.from_unexpected_token_value(self, "string")
        return self.value

    def get_str_from_text_token(self) -> str:
        '''
        Validates a token for having 'str' as it's value, and the token type
        TEXT and if it succeeds it returns the 'str' value.
        '''
        if self.token_type != TokenType.TEXT:
            raise ParseError.from_unexpected_token(self, TokenType.TEXT)
        if not isinstance(self.value, str):
            raise ParseError.from_unexpected_token_value(self, "string")
        return self.value

    def get_setting(self) -> Setting:
        '''
        Validates a token for having Settings as it's value and if it succeeds
        it returns the settings.
        '''
        if (
                not isinstance(self.value, Setting) or
                self.token_type != TokenType.SETTING):
            raise ParseError(
                f"Unexpected value of token {self} "
                f"at line {self.line_number}. Expected setting pair like: "
                "<key>=<value>")
        return self.value

# Token values
class Setting(NamedTuple):
    '''A setting of a label'''
    name: str
    value: str

class CoordinatesRotated(NamedTuple):
    '''Normal coordinates x y z ry rx'''
    x: float
    y: float
    z: float
    y_rot: float
    x_rot: float

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
    (r'actionbar:', lambda s, t: (TokenType.ACTIONBAR, t)),
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
            f' ({float_pattern}) ({float_pattern})',
        lambda s, t: (
            TokenType.COORDINATES_ROTATED,
            CoordinatesRotated(
                float(s.match[1]), float(s.match[2]), float(s.match[3]),
                float(s.match[4]), float(s.match[5]),
            )
        )
    ),
    (r'/.+', lambda s, t: (TokenType.COMMAND, t[1:])),
    (r'>.+', lambda s, t: (TokenType.TEXT, t[1:])),
    (var_pattern + r':', lambda s, t: (TokenType.NAMED_LABEL, t[:-1])),
])

def tokenize(source: list[str]) -> list[Token]:
    '''
    Splits a source file into tokens.
    '''
    line_number = 0
    tokens: list[Token] = []
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
    timeline: list[Union[MessageNode, DialogueNode, CameraNode]]
    settings: Optional[SettingsNode] = None
    sound_profiles: Optional[SoundProfilesNode] = None

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> RootAstNode:
        token = tokens[0]
        # Settings
        settings = None
        if token.token_type is TokenType.SETTINGS:
            settings = SettingsNode.from_token_stack(tokens)
            token = tokens[0]
        # Sound profiles
        sound_profiles = None
        if token.token_type is TokenType.SOUND_PROFILES:
            sound_profiles = SoundProfilesNode.from_token_stack(tokens)
            token = tokens[0]
        # Timeline
        timeline: list[Union[MessageNode, DialogueNode, CameraNode]] = []
        while token.token_type is not TokenType.EOF:
            if token.token_type in (
                    TokenType.TELL, TokenType.TITLE, TokenType.ACTIONBAR,
                    TokenType.BLANK):
                timeline.append(MessageNode.from_token_stack(tokens))
            elif token.token_type is TokenType.DIALOGUE:
                raise NotImplementedError()
            elif token.token_type is TokenType.CAMERA:
                timeline.append(CameraNode.from_token_stack(tokens))
            else:
                raise ParseError.from_unexpected_token(
                    token, TokenType.TELL, TokenType.BLANK, TokenType.TITLE,
                    TokenType.ACTIONBAR, TokenType.DIALOGUE, TokenType.EOF)
            token = tokens[0]
        return RootAstNode(timeline, settings, sound_profiles)

@dataclass
class SettingsNode:
    settings: SettingsList
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> SettingsNode:
        token = tokens.popleft()
        root_token = token
        if token.token_type is not TokenType.SETTINGS:
            raise ParseError.from_unexpected_token(
                token, TokenType.SETTINGS)
        settings = SettingsNode.parse_settings(
            tokens,
            accepted_settings={"wpm": float, "cpm": float, "title_max": int}
        )
        return SettingsNode(settings, root_token)

    @staticmethod
    def parse_settings(
            tokens: deque[Token], *,
            expected_settings: Optional[dict[str, Callable[[Any], Any]]]=None,
            accepted_settings: Optional[dict[str, Callable[[Any], Any]]]=None
    ) -> SettingsList:
        '''
        Parse settings is a helper function used to parse settings of any
        label that allows having them. Performs setting validation.
        - No duplicate settings are allowed
        - Settings from "expected_settings" must be present and must be
            of the expected type
        - If "accepted_settings" is not None, only settings from this list
            are allowed
        If expected_settings or accepted_settings are None then it only
        checks for duplicate settings.

        The Callables from expected and accepted settings are functions that
        take the value of the setting and try to convert it to the expected
        type. If callable doesn't fail, the function assumes that the value is
        valid.
        '''
        token = tokens[0]
        settings: SettingsList = []
        logged_settings: dict[str, SettingNode] = {}
        while token.token_type is TokenType.SETTING:
            setting = SettingNode.from_token_stack(tokens)
            # Check accepted settings
            if accepted_settings is not None:
                # Does key exist?
                if setting.name not in accepted_settings:
                    raise ParseError(
                        f"The '{setting.name}' is not allowed in this "
                        f"context. Line {token.line_number}. Only following"
                        "settings are accepted:"
                        +
                        "\n".join(
                            f"\t-{setting}"
                            for setting in accepted_settings)
                        )
                # Is the type correct?
                try:
                    accepted_settings[setting.name](setting.value)
                except Exception:
                    raise ParseError(
                        f"The '{setting.name}' has an invalid value. "
                        f"Line {token.line_number}.")
            # Check duplicate settings
            if setting.name in logged_settings:
                raise ParseError(
                    f"Duplicate setting {setting.name} at line "
                    f"{setting.token.line_number}")
            logged_settings[setting.name] = setting
            settings.append(setting)
            token = tokens[0]
        # Check if there are all the expected settings
        if expected_settings is not None:
            for key, func in expected_settings.items():
                if key not in logged_settings:
                    raise ParseError(
                        f"Missing setting '{key}' at line "
                        f"{token.line_number}")
                try:
                    func(logged_settings[key].value)
                except Exception:
                    raise ParseError(
                        f"Invalid value for setting '{key}' at line "
                        f"{token.line_number}")
        return settings

    @staticmethod
    def settings_list_to_dict(settings: SettingsList) -> dict[str, str]:
        '''
        Returns the dictionary representation of the settings list. Doesn't do
        safety checks for duplicate properties.
        '''
        return {setting.name: setting.value for setting in settings}

@dataclass
class SettingNode:
    name: str
    value: str
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> SettingNode:
        token = tokens.popleft()
        root_token = token
        if token.token_type is not TokenType.SETTING:
            raise ParseError.from_unexpected_token(
                token, TokenType.SETTING)
        name, value = Token.get_setting(token)
        # TODO - perhaps I should check types of specific settings here?
        return SettingNode(name, value, root_token)

@dataclass
class SoundProfilesNode:
    sound_profiles: list[SoundProfileNode]
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> SoundProfilesNode:
        token = tokens.popleft()
        root_token = token
        if token.token_type is not TokenType.SOUND_PROFILES:
            raise ParseError.from_unexpected_token(
                token, TokenType.SOUND_PROFILES)
        # Expect indentation or finish parsing message node
        token = tokens[0]
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
            token = tokens[0]
        else:
            return SoundProfilesNode([], root_token)
        sound_profiles: list[SoundProfileNode] = []
        while token.token_type == TokenType.NAMED_LABEL:
            sound_profiles.append(SoundProfileNode.from_token_stack(tokens))
            token = tokens[0]
        # Expect DEDENT or EOF, don't pop EOF
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        elif token.token_type is not TokenType.EOF:  # not DEDENT and not EOF
            raise ParseError.from_unexpected_token(
                token, TokenType.DEDENT, TokenType.EOF)
        return SoundProfilesNode(sound_profiles, root_token)

@dataclass
class SoundProfileNode:
    name: str
    sound_profile_variants: list[SoundProfileVariant]
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> SoundProfileNode:
        token = tokens.popleft()
        root_token = token

        name = token.get_str_from_named_label_token()
        # Expect indentation or finish parsing message node
        token = tokens[0]
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
            token = tokens[0]
        else:
            return SoundProfileNode(name, [], root_token)
        sound_profile_variant: list[SoundProfileVariant] = []
        while token.token_type == TokenType.NAMED_LABEL:
            sound_profile_variant.append(
                SoundProfileVariant.from_token_stack(tokens))
            token = tokens[0]
        # Expect DEDENT or EOF, don't pop EOF
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        elif token.token_type is not TokenType.EOF:  # not DEDENT and not EOF
            raise ParseError.from_unexpected_token(
                token, TokenType.DEDENT, TokenType.EOF)
        return SoundProfileNode(name, sound_profile_variant, root_token)

    def as_dictionary(self) -> dict[str, str]:
        '''
        Returns the dictionary representation of this sound profile.
        '''
        result: dict[str, str] = {}
        for spv in self.sound_profile_variants:
            settings = SettingsNode.settings_list_to_dict(spv.settings)
            sound = settings['sound']  # No KeyError check here, should be safe
            result[spv.name] = sound
        return result

@dataclass
class SoundProfileVariant:
    name: str
    settings: SettingsList
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> SoundProfileVariant:
        token = tokens.popleft()
        root_token = token
        name = token.get_str_from_named_label_token()
        settings = SettingsNode.parse_settings(
            tokens,
            accepted_settings={"sound": str},
            expected_settings={"sound": str})
        return SoundProfileVariant(name, settings, root_token)

@dataclass
class MessageNode:
    node_type: Literal["tell", "blank", "title", "actionbar"]
    text_nodes: list[TextNode]
    command_nodes: list[CommandNode]
    schedule_nodes: list[ScheduleNode]
    settings: SettingsList
    loop_nodes: list[LoopNode]
    token: Token
    run_once_node: Optional[RunOnceNode] = None
    on_exit_node: Optional[OnExitNode] = None

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> MessageNode:
        token = tokens.popleft()
        root_token = token

        node_type: Literal["tell", "blank", "title", "actionbar"]
        if token.token_type is TokenType.TELL:
            node_type = "tell"
        elif token.token_type is TokenType.ACTIONBAR:
            node_type = "actionbar"
        elif token.token_type is TokenType.BLANK:
            node_type = "blank"
        elif token.token_type is TokenType.TITLE:
            node_type = "title"
        else:
            raise ParseError.from_unexpected_token(
                token, TokenType.TELL, TokenType.ACTIONBAR, TokenType.BLANK,
                TokenType.TITLE)
        token = tokens[0]
        # Settings
        settings: SettingsList = []
        if token.token_type is TokenType.SETTING:
            if node_type == "blank":
                settings = SettingsNode.parse_settings(
                    tokens,
                    accepted_settings={"time": float, "sound": str})
            else:
                settings = SettingsNode.parse_settings(
                    tokens,
                    accepted_settings={
                        "wpm": float, "cpm": float, "time": float,
                        "sound": str
                    }
                )
            token = tokens[0]
        # Expect indentation or finish parsing message node
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
            token = tokens[0]
        else:
            return MessageNode(node_type, [], [], [], settings, [], root_token)
        # Text nodes
        text_nodes = []
        token = tokens[0]
        while token.token_type is TokenType.TEXT:
            if node_type == "blank":  # Blank node can't have text
                raise ParseError.from_unexpected_token(
                    token, TokenType.TEXT)
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
        schedule_nodes: list[ScheduleNode] = []
        loop_nodes: list[LoopNode] = []
        while token.token_type in (
                TokenType.SCHEDULE, TokenType.RUN_ONCE, TokenType.ON_EXIT,
                TokenType.LOOP):
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
            # Loop nodes
            if token.token_type is TokenType.LOOP:
                loop_nodes.append(LoopNode.from_token_stack(tokens))
            token = tokens[0]
        # Expect DEDENT or EOF, don't pop EOF
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        return MessageNode(
            node_type, text_nodes, command_nodes, schedule_nodes, settings,
            loop_nodes, root_token, run_once_node, on_exit_node)


@dataclass
class DialogueNode:
    text: TextNode
    dialogue_options: list[DialogueOptionNode]
    dialogue_exit: Optional[DialogueOptionNode]
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> DialogueNode:
        raise NotImplementedError()

@dataclass
class DialogueOptionNode:
    text_nodes: list[TextNode]
    command_nodes: list[CommandNode]
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> DialogueOptionNode:
        raise NotImplementedError()

@dataclass
class CameraNode:
    coordinates: list[CoordinatesNode]
    token: Token
    time: TimeNode

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> CameraNode:
        token = tokens.popleft()
        root_token = token
        if token.token_type is not TokenType.CAMERA:
            raise ParseError.from_unexpected_token(
                token, TokenType.CAMERA)
        # Expect indentation or finish parsing camera node
        token = tokens[0]
        if token.token_type is not TokenType.INDENT:
            raise ParseError.from_unexpected_token(
                token, TokenType.INDENT)
        tokens.popleft()
        # Coordinates
        coordinates = []
        token = tokens[0]
        while token.token_type in (
                TokenType.COORDINATES_ROTATED,
                TokenType.COORDINATES_FACING_COORDINATES,
                TokenType.COORDINATES_FACING_ENTITY):
            coordinates.append(CoordinatesNode.from_token_stack(tokens))
            token = tokens[0]
        # Time
        if token.token_type is not TokenType.TIME:
            raise ParseError.from_unexpected_token(token, TokenType.TIME)
        time = TimeNode.from_token_stack(tokens)

        #  Why was this here? This type was impossible due to the previous 
        # check:
        # Expecte DEDENT or EOF, don't pop EOF
        # if token.token_type is TokenType.DEDENT:
        #     tokens.popleft()
        return CameraNode(coordinates, root_token, time)

@dataclass
class TimeNode:
    settings: SettingsList
    messages: list[MessageNode]
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> TimeNode:
        token = tokens.popleft()
        root_token = token
        if token.token_type is not TokenType.TIME:
            raise ParseError.from_unexpected_token(
                token, TokenType.TIME)
        token = tokens[0]
        # Settings
        settings: SettingsList = []
        if token.token_type is TokenType.SETTING:
            settings = SettingsNode.parse_settings(
                tokens, accepted_settings={"time": float})
            token = tokens[0]
        # Expect indentation or finish parsing time node
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
            token = tokens[0]
        elif token.token_type == TokenType.DEDENT:
            tokens.popleft()
            return TimeNode(settings, [], root_token)
        else:
            raise ParseError.from_unexpected_token(
                token, TokenType.INDENT, TokenType.DEDENT)
        # Message nodes
        messages: list[MessageNode] = []
        while token.token_type in (
                TokenType.TELL, TokenType.TITLE, TokenType.BLANK,
                TokenType.ACTIONBAR):
            messages.append(MessageNode.from_token_stack(tokens))
            token = tokens[0]
        # Expect DEDENT or EOF, don't pop EOF
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        # Double dedent. This part of code is reachable only if 'time' has
        # subnodes
        if token.token_type is TokenType.DEDENT:
            tokens.popleft()
        return TimeNode(settings, messages, root_token)

@dataclass
class CoordinatesNode:
    coordinates: AnyCoordinates
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> CoordinatesNode:
        root_token = tokens.popleft()
        crds_tokens = (
            TokenType.COORDINATES_ROTATED,
            TokenType.COORDINATES_FACING_COORDINATES,
            TokenType.COORDINATES_FACING_ENTITY)
        if root_token.token_type not in crds_tokens:
            raise ParseError.from_unexpected_token(root_token, *crds_tokens)
        any_coordinates_type = (
            CoordinatesRotated,
            CoordinatesFacingCoordinates,
            CoordinatesFacingEntity)
        if not isinstance(root_token.value, any_coordinates_type):
            raise ParseError(
                f"Unable to parse coordinates from line "
                f"{root_token.line_number}")
        coordinates = root_token.value
        return CoordinatesNode(coordinates, root_token)

@dataclass
class TextNode:
    text: str
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> TextNode:
        token = tokens.popleft()
        root_token = token
        if token.token_type is not TokenType.TEXT:
            raise ParseError.from_unexpected_token(
                token, TokenType.TEXT)
        if not isinstance(token.value, str):
            raise ParseError.from_unexpected_token_value(
                token, "string")
        return TextNode(token.value, root_token)

@dataclass
class CommandNode:
    text: str
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> CommandNode:
        token = tokens.popleft()
        root_token = token
        if token.token_type is not TokenType.COMMAND:
            raise ParseError.from_unexpected_token(
                token, TokenType.COMMAND)
        if not isinstance(token.value, str):
            raise ParseError.from_unexpected_token_value(
                token, "string")
        return CommandNode(token.value, root_token)

@dataclass
class RunOnceNode:
    command_nodes: list[CommandNode]
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> RunOnceNode:
        token = tokens.popleft()
        root_token = token
        if token.token_type is not TokenType.RUN_ONCE:
            raise ParseError.from_unexpected_token(
                token, TokenType.RUN_ONCE)
        # Expect indentation or finish parsing run once node
        token = tokens[0]
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
            token = tokens[0]
        else:
            return RunOnceNode([], root_token)
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
        return RunOnceNode(command_nodes, root_token)

@dataclass
class ScheduleNode:
    command_nodes: list[CommandNode]
    settings: SettingsList
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> ScheduleNode:
        token = tokens.popleft()
        root_token = token

        if token.token_type is not TokenType.SCHEDULE:
            raise ParseError.from_unexpected_token(
                token, TokenType.SCHEDULE)
        token = tokens[0]
        # Settings
        settings: SettingsList = []
        if token.token_type is TokenType.SETTING:
            settings = SettingsNode.parse_settings(
                tokens,
                accepted_settings={"time": float},
                expected_settings={"time": float})
            token = tokens[0]
        # Expect indentation or finish parsing schedule node
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
            token = tokens[0]
        else:
            return ScheduleNode([], [], root_token)
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
        return ScheduleNode(command_nodes, settings, root_token)

@dataclass
class OnExitNode:
    command_nodes: list[CommandNode]
    token: Token
    
    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> OnExitNode:
        token = tokens.popleft()
        root_token = token
        if token.token_type is not TokenType.ON_EXIT:
            raise ParseError.from_unexpected_token(
                token, TokenType.ON_EXIT)
        token = tokens[0]
        # Expect indentation or finish parsing on exit node
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
            token = tokens[0]
        else:
            return OnExitNode([], root_token)
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
        return OnExitNode(command_nodes, root_token)

@dataclass
class LoopNode:
    command_nodes: list[CommandNode]
    settings: SettingsList
    token: Token

    @staticmethod
    def from_token_stack(tokens: deque[Token]) -> LoopNode:
        token = tokens.popleft()
        root_token = token

        if token.token_type is not TokenType.LOOP:
            raise ParseError.from_unexpected_token(
                token, TokenType.LOOP)
        token = tokens[0]
        # Settings
        settings: SettingsList = []
        if token.token_type is TokenType.SETTING:
            settings = SettingsNode.parse_settings(
                tokens,
                accepted_settings={"time": float},
                expected_settings={"time": float})
            token = tokens[0]
        # Expect indentation or finish parsing run once node
        if token.token_type == TokenType.INDENT:
            tokens.popleft()
            token = tokens[0]
        else:
            return LoopNode([], settings, root_token)
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
        return LoopNode(command_nodes, settings, root_token)


# The main AST builder function
def build_ast(tokens: list[Token]) -> RootAstNode:
    '''
    Builds an abstract syntax tree from a list of tokens.
    '''
    tokens_stack = deque(tokens)
    return RootAstNode.from_token_stack(tokens_stack)


# Type aliases
SettingsList = list[SettingNode]

AnyCoordinates = Union[
    CoordinatesFacingCoordinates, CoordinatesFacingEntity, CoordinatesRotated]
