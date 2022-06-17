'''
Compiler module is responsible for processing the AST produced by the parser
and do some additiona validation. It doesn't generate any code, but it changes
the AST to a format that is used for the code generation.
'''
from __future__ import annotations
import re
import math
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Literal, Optional, Union

import numpy as np
import scipy.interpolate

from itertools import count

from .message_duration import cpm_duration, sound_duration, wpm_duration
from .parser import (CameraNode, CoordinatesFacingCoordinates,
                     CoordinatesFacingEntity, CoordinatesNode,
                     CoordinatesRotated, DialogueNode, MessageNode,
                     SettingsList, SettingsNode, ProfileNode, var_pattern,
                     Token)

class CompileError(Exception):
    '''
    Raised when the compiler encounters an error. This can happen when the code
    has some invalid logic (after parsing is done)
    '''
    @staticmethod
    def from_invalid_setting(
            message_node: MessageNode, setting_name: str) -> CompileError:
        return CompileError(
            f'Invalid property "{setting_name}" on line '
            f'{message_node.token.line_number}')

    @staticmethod
    def from_invalid_setting_value(
            message_node: MessageNode, setting_name: str) -> CompileError:
        return CompileError(
            f'Invalid value for property "{setting_name}" on line '
            f'{message_node.token.line_number}')

@dataclass
class TranslationCodeProvider:
    '''
    Translation code provide provides the short names for the translations in
    the lang file. The translation codes are created based on a prefix combined
    with a number.
    '''
    prefix: str
    _counter: dict[str, int] = field(
        default_factory=lambda: defaultdict(lambda: 1))
    _cached_translations: dict[str, str] = field(default_factory=dict)

    def get_translation_code(self, translation: str) -> str:
        '''
        Returns the translation code for given string. If the translation
        already exists it returns the code to the previously assigned
        code.
        '''
        try:
            return self._cached_translations[translation]
        except KeyError:
            result_text = f"{self.prefix}.{self._counter[self.prefix]}"
            self._counter[self.prefix] += 1
            self._cached_translations[translation] = result_text
            return result_text

    def get_translation_file(self) -> list[str]:
        '''
        Returns a list of strings to be inserted into the .lang file.
        '''
        return [
            f'{key}={value}'
            # The key and value are reversed here this is not a bug.
            for value, key in self._cached_translations.items()
        ]

@dataclass
class SoundCodeProvider:
    '''
    Sound code provider provides and remembers the short names for the sounds
    based on the file paths.
    '''
    _cached_names: dict[Path, str] = field(default_factory=dict)

    def get_sound_code(self, sound_path: Path) -> str:
        '''
        Returns the sound code for given sound path. If the sound path already
        exists it returns the code to the previously assigned code.
        '''
        try:
            return self._cached_names[sound_path]
        except KeyError:
            # with_suffix removes the .ogg extension from the name
            result = '.'.join(sound_path.with_suffix("").parts)
            self._cached_names[sound_path] = result
            return result

    def walk_names(self) -> Iterable[tuple[str, str]]:
        '''
        Returns the keys and the values of the names in cache, ready to be
        used in the sound_definitions.json file.
        '''
        for k, v in self._cached_names.items():
            path = k.with_suffix("").as_posix()
            yield v, path

    def inspect_sound_paths(self, rp_path: Path) -> None:
        for path, key in self._cached_names.items():
            if not (rp_path / path).exists():
                print(
                    f"WARNING: The sound definition '{key}' has a reference "
                    f"to a path that doesn't exist:\n"
                    f"\t'{(rp_path / path).as_posix()}'",
                    file=sys.stderr)

class ConfigProvider:
    '''
    ConfigProvider handles access to the configuration of the dialogue file.
    The configuratino includes the global settings and a sound profile.
    '''
    def __init__(
            self, settings: Optional[SettingsNode],
            profile: Optional[ProfileNode]=None):
        self.settings = (
            {} if settings is None else
            ConfigProvider.parse_settings(settings.settings))
        self.sounds: dict[str, str] = {}
        self.variables: dict[str, str] = {}
        if profile is not None:
            if profile.sounds is not None:
                self.sounds = ConfigProvider.parse_settings(
                    profile.sounds.settings)
            if profile.variables is not None:
                self.variables = ConfigProvider.parse_settings(
                    profile.variables.settings)

    def insert_variables(self, text: str, line_number: Optional[int]) -> str:
        '''
        Inserts the variables into text and returns modified text.

        :param text: The string to be modified
        :param line_number: The line number for error messages
        '''
        cursor: int = 0
        replace = []
        insertion_pattern = re.compile(r"\{("+var_pattern+")\}")
        while (
                cursor < len(text) and
                (match := insertion_pattern.search(text[cursor:]))):
            start, end = cursor+match.start(), cursor+match.end()
            try:
                replace.append((start, end, self.variables[match[1]])) 
            except KeyError as e:
                raise CompileError(
                    f"Reference to undefined variable \"{e}\"" +
                    # In practice this the line number should always be
                    # available.
                    f"on line {line_number}"
                    if line_number is not None else "")
            cursor = end
        if len(replace) > 0:
            result_list = []
            prev_end = 0
            for r in replace:
                result_list.append(text[prev_end:r[0]])  # prefix
                result_list.append(r[2])  # value
                prev_end = r[1]
            # Last item (python's variable scope is weeeird :O, but awesome)
            result_list.append(text[r[1]:])  # sufix
            return "".join(result_list)
        return text

    @staticmethod
    def parse_settings(settings: SettingsList) -> dict[str, str]:
        '''
        Returns a dictionary of settings from SettingsNode, chceks if there
        is no duplicate keys.
        '''
        settings_dict: dict[str, str] = {}
        for setting in settings:
            if setting.name in settings_dict:
                raise CompileError(
                    f'Duplicate setting {setting.name} at line '
                    f'{setting.token.line_number}')
            settings_dict[setting.name] = setting.value
        return settings_dict

    def message_node_duration(
            self, message_node: MessageNode, rp_path: Path) -> int:
        '''
        Message node duration decides how to calculate the duration of an
        message event and returns its value in Minecraft ticks. If it's
        impossible to calculate the duration it raises the CompileError.

        The priorities of calculating that value are described here:
        - local 'time' property
        - local 'wpm' (words per minute) property
        - local 'cpm' (characters per minute) property
        - local sound duration (the time of the ogg file)
        - global 'wpm' property
        - global 'cpm' property
        '''
        # Get the text length for text messages
        full_text = ""
        if message_node.node_type != 'blank':
            full_text = " ".join(
                node.text for node in message_node.text_nodes)
        # The settings of THIS node
        node_settings = ConfigProvider.parse_settings(message_node.settings)
        # Try using local settings
        if 'time' in node_settings:
            return seconds_to_halfticks(node_settings['time'])
        if 'wpm' in node_settings:
            if message_node.node_type == 'blank':
                raise CompileError.from_invalid_setting(message_node, 'wpm')
            try:
                wpm = float(node_settings['wpm'])
            except (ValueError, TypeError):
                raise CompileError.from_invalid_setting_value(
                    message_node, 'wpm')
            return seconds_to_halfticks(wpm_duration(full_text, wpm))
        if 'cpm' in node_settings:
            if message_node.node_type == 'blank':
                raise CompileError.from_invalid_setting(message_node, 'cpm')
            try:
                cpm = float(node_settings['cpm'])
            except (ValueError, TypeError):
                raise CompileError.from_invalid_setting_value(
                    message_node, 'cpm')
            return seconds_to_halfticks(cpm_duration(full_text, cpm))
        if 'sound' in node_settings:
            sound_path = self.resolve_sound_path(
                node_settings['sound'], message_node)
            duration = sound_duration(rp_path / sound_path)
            if duration is not None:
                return seconds_to_halfticks(duration)
        # 'wpm' and 'cpm' shouldn't give errors from 'blank' message nodes
        # if these properties are implemented in global settings
        if 'wpm' in self.settings and message_node.node_type != 'blank':
            return seconds_to_halfticks(wpm_duration(full_text, float(self.settings['wpm'])))
        if 'cpm' in self.settings and message_node.node_type != 'blank':
            return seconds_to_halfticks(cpm_duration(full_text, float(self.settings['cpm'])))
        # TODO - Should I use 'time' property from global settings? Should
        # the local and global settings be converted to a proper type before
        # we reach this point?
        raise CompileError(
            f'Cannot calculate duration of message node at line '
            f'{message_node.token.line_number}')

    def try_get_sound_timeline_event_action(
            self, message_node: MessageNode) -> Optional[TimelineEventAction]:
        '''
        Takes a MessageNode, if it has the 'sound' setting it returns the the
        sound TimelineEventAction, otherwise it returns None.
        '''
        # The settings of THIS node
        node_settings = ConfigProvider.parse_settings(message_node.settings)
        # Try using local settings
        if 'sound' in node_settings:
            sound_path = self.resolve_sound_path(
                node_settings['sound'], message_node)
            return TimelineEventAction(
                'playsound', sound_path.as_posix(),
                message_node.token.line_number)
        return None

    def resolve_sound_path(
            self, sound: str, message_node: MessageNode) -> Path:
        '''
        Resolves the path to a sound file. The 'sound' is a value of the sound
        property of a message_node. The message_node is used for error
        messages.
        '''
        sound_path: Path
        if ":" in sound:
            sound_variant, sound_name = sound.split(':')
            if sound_variant not in self.sounds:
                raise CompileError(
                    f"Trying to use undefined sound variant "
                    f"'{sound_variant}' of the sound '{sound_name}' on "
                    f"line {message_node.token.line_number}.\n"
                    f"Available variants: "
                    f"{', '.join(self.sounds.keys())}")
            sound_path = Path(self.sounds[sound_variant]) / sound_name
        else:
            sound_path = Path(sound)
        return Path("sounds") / sound_path


@dataclass
class TimelineEventAction:
    '''
    TimelineEventAction is a single action that is executed during a timeline
    event. Actions are instand and don't have duration. Single timeline event
    can have multiple actions.
    '''
    action_type: Literal["tell", "title", "actionbar", "command", "subtitle", "playsound"]
    value: str

    # Line number for error messages (sometimes doesn't apply because) some
    # actions are not created based on a specific line.
    line_number: Optional[int]

    def to_command(
            self, tc_provider: TranslationCodeProvider,
            sc_provider: SoundCodeProvider,
            config_provider: ConfigProvider) -> str:
        '''
        Returns the command to be executed in Minecraft sequence.
        '''
        if self.action_type == "tell":
            resolved_value = config_provider.insert_variables(
                self.value, self.line_number)
            translation_code = tc_provider.get_translation_code(resolved_value)
            return  (
                'tellraw @a '
                f'{{"rawtext":[{{"translate":"{translation_code}"}}]}}')
        elif self.action_type == "title":
            resolved_value = config_provider.insert_variables(
                self.value, self.line_number)
            translation_code = tc_provider.get_translation_code(resolved_value)
            return  (
                'titleraw @a title '
                f'{{"rawtext":[{{"translate":"{translation_code}"}}]}}')
        elif self.action_type == "actionbar":
            resolved_value = config_provider.insert_variables(
                self.value, self.line_number)
            translation_code = tc_provider.get_translation_code(resolved_value)
            return  (
                'titleraw @a actionbar '
                f'{{"rawtext":[{{"translate":"{translation_code}"}}]}}')
        elif self.action_type == "subtitle":
            resolved_value = config_provider.insert_variables(
                self.value, self.line_number)
            translation_code = tc_provider.get_translation_code(resolved_value)
            return  (
                'titleraw @a subtitle '
                f'{{"rawtext":[{{"translate":"{translation_code}"}}]}}')
        elif self.action_type == "command":
            return self.value
        elif self.action_type == "playsound":
            return f'playsound {sc_provider.get_sound_code(Path(self.value))} @a'
        else:
            raise ValueError(f"Unknown action type: {self.action_type}")

@dataclass
class TimelineEvent:
    '''
    Timeline event is a single event that takes place on a timeline.
    '''
    actions: list[TimelineEventAction]

@dataclass
class AnimationTimeline:
    '''
    AnimationTimeline is a class that represents sequence of events. Possible
    timeline events are:
    - run command
    - display tellraw text
    - display title text

    Timeline can be created in a 3 ways:
    - from a list of camera coordinates and the camera animation duration
    - from a list of events of known length (either a timeline of the root
        node or a time of the camera node)
    - from merging different timelines
    '''
    events: dict[int, TimelineEvent]
    time: int

    @staticmethod
    def from_message_node_list(
            settings: ConfigProvider,
            timeline_nodes: list[MessageNode],
            rp_path: Path, run_once_counter: count[int]) -> AnimationTimeline:
        '''
        Creates a AnimationTimeline from a list of MessageNodes.
        '''
        events: dict[int, TimelineEvent] = {}

        def add_event_action(
                time: int, *actions: TimelineEventAction) -> None:
            if time not in events:
                events[time] = TimelineEvent(actions=[])
            events[time].actions.extend(actions)

        # time is the time of the event on the timeline measured in Minecraft
        # ticks
        time: int = 0
        for node in timeline_nodes:
            duration = settings.message_node_duration(node, rp_path)
            optional_sound_node = settings.try_get_sound_timeline_event_action(
                node)
            if optional_sound_node is not None:
                add_event_action(time, optional_sound_node)
            actions: list[TimelineEventAction]
            if node.node_type == 'tell':
                actions = [  # The messages
                    TimelineEventAction(
                        'tell', text_node.text, text_node.token.line_number)
                    for text_node in node.text_nodes
                ]
            elif node.node_type == 'blank':
                actions = []
            elif node.node_type == 'title':
                if len(node.text_nodes) == 1:
                    actions = [  # The title
                        TimelineEventAction(
                            'title', node.text_nodes[0].text, 
                            node.text_nodes[0].token.line_number)
                    ]
                elif len(node.text_nodes) == 2:
                    actions = [  # The title and subtitle
                        TimelineEventAction(
                            'title', node.text_nodes[0].text,
                            node.text_nodes[0].token.line_number),
                        TimelineEventAction(
                            'subtitle', node.text_nodes[1].text,
                            node.text_nodes[1].token.line_number)
                    ]
                else:
                    raise CompileError(
                        "Title node should have 1 or 2 text nodes but it"
                        f"has {len(node.text_nodes)}. Line "
                        f"{node.token.line_number}") 
            elif node.node_type == 'actionbar':
                if len(node.text_nodes) != 1:
                    raise CompileError(
                        "Actionbar node should have exactly one text "
                        f"node {node.token.line_number}")
                actions = [  # The messages
                    TimelineEventAction(
                        'actionbar', text_node.text,
                        text_node.token.line_number)
                    for text_node in node.text_nodes
                ]
            else:
                raise ValueError("Unknown MessageNode type")
            actions += [
                TimelineEventAction(
                        'command', text_node.text,
                        text_node.token.line_number)
                for text_node in node.command_nodes
            ]
            if node.on_exit_node is not None:
                on_exit_actions = [
                    TimelineEventAction(
                        'command', text_node.text,
                        text_node.token.line_number)
                    for text_node in node.on_exit_node.command_nodes
                ]
                add_event_action(time + duration, *on_exit_actions)
            if node.run_once_node is not None:
                run_once_id = f"run_once{next(run_once_counter)}"
                run_once_actions = [
                    TimelineEventAction(
                        'command',
                        f'execute @s[tag=!{run_once_id}] ~ ~ ~ '
                            f'{text_node.text}',
                        text_node.token.line_number)
                    for text_node in node.run_once_node.command_nodes
                ]
                run_once_actions.append(TimelineEventAction(
                    'command', f"tag @s add {run_once_id}", None))
                add_event_action(time, *run_once_actions)
            for schedule_node in node.schedule_nodes:
                schedule_time = seconds_to_halfticks(  # Should be safe (parser checks that)
                    ConfigProvider.parse_settings(
                        schedule_node.settings)['time'])
                scheduled_actions = [
                    TimelineEventAction(
                        'command', text_node.text,
                        text_node.token.line_number)
                    for text_node in schedule_node.command_nodes
                ]
                add_event_action(time + schedule_time, *scheduled_actions)
            for loop_node in node.loop_nodes:
                loop_time = seconds_to_halfticks(  # This should be safe (parser checks that)
                    ConfigProvider.parse_settings(
                        loop_node.settings)['time'])
                if loop_time <= 0:
                    loop_time = 1  # TODO - should I log a warning?
                looping_actions = [
                    TimelineEventAction(
                        'command', text_node.text,
                        text_node.token.line_number)
                    for text_node in loop_node.command_nodes
                ]
                loop_time_sum = 0
                while loop_time_sum < duration:
                    add_event_action(time + loop_time_sum, *looping_actions)
                    loop_time_sum += loop_time
            add_event_action(time, *actions)
            time = time + duration
        return AnimationTimeline(events, time)

    @staticmethod
    def from_coordinates_list(
            camera_node: CameraNode,
            time: int, spline_fit_degree: int=3) -> AnimationTimeline:
        '''
        Creates a AnimationTimeline from a CameraNode.
        '''
        keyframes: list[int] = list(np.linspace(
            0, time, len(camera_node.coordinates), dtype=int))
        # A stack for processing the keyframes
        frames_stack: deque[tuple[int, CoordinatesNode]] = deque(
            (keyframe, c)
            for keyframe, c in zip(keyframes, camera_node.coordinates)
        )
        # Get the end part of the command (the rotation)
        rotation_suffixes: dict[int, str] = {}
        while len(frames_stack) > 1:
            _, c = frames_stack[0]
            # Map the coordinates to the keyframes for later use
            # Get the current type of node
            if isinstance(c.coordinates, CoordinatesRotated):
                AnimationTimeline._get_tp_suffixes_crds_rotated(
                    frames_stack, rotation_suffixes, spline_fit_degree)
            elif isinstance(c.coordinates, CoordinatesFacingCoordinates):
                AnimationTimeline._get_tp_suffixes_crds_facing_crds(
                    frames_stack, rotation_suffixes, spline_fit_degree)
            elif isinstance(c.coordinates, CoordinatesFacingEntity):
                raise NotImplementedError()
            else:
                raise ValueError()  # Should never happen
        # Get the start part of the command (the position) and combine it
        # with the rotation
        xs: list[float] = []
        ys: list[float] = []
        zs: list[float] = []
        for c in camera_node.coordinates:
            xs.append(c.coordinates.x)
            ys.append(c.coordinates.y)
            zs.append(c.coordinates.z)
        n_frames = keyframes[-1] - keyframes[0]
        frames, xs = interp1d_magic(
            xs, keyframes[0], keyframes[-1], n_frames, spline_fit_degree)
        _, ys = interp1d_magic(
            ys, keyframes[0], keyframes[-1], n_frames, spline_fit_degree)
        _, zs = interp1d_magic(
            zs, keyframes[0], keyframes[-1], n_frames, spline_fit_degree)
        events: dict[int , TimelineEvent] = {}
        for frame, x, y, z in zip(frames, xs, ys, zs):
            frame = int(frame)
            if frame not in events:
                events[frame] = TimelineEvent([])
            output_value = f"tp @a {x:.2f} {y:.2f} {z:.2f} {rotation_suffixes[frame]}"
            events[frame].actions.append(
                TimelineEventAction("command", output_value, None))
        return AnimationTimeline(events, time)

    @staticmethod
    def _get_tp_suffixes_crds_rotated(
            frames_stack: deque[tuple[int, CoordinatesNode]],
            ouptut: dict[int, str], spline_fit_degree: int) -> None:
        '''
        Used by from_coordinates_list.

        Gets suffixes of the /tp command for 'rotated tp' nodes and adds them
        to the 'output' dictionary. The 'rotated tp' command is the command
        that follows pattern '/tp {x} {y} {z} {ry} {rx}'. This function takes
        care of the 'ry' and 'rx' part.
        '''
        first_frame, c = frames_stack[0]
        last_frame = first_frame  # The last CoordinatesRotated frame
        next_frame = first_frame  # The frame after the last frame
        ys: list[float] = []
        xs: list[float] = []
        while isinstance(c.coordinates, CoordinatesRotated):
            last_frame = next_frame
            ys.append(c.coordinates.y_rot)
            xs.append(c.coordinates.x_rot)
            if len(frames_stack) == 0:
                break
            next_frame, c = frames_stack.popleft()
        frame_steps = last_frame - first_frame
        frames, ys = interp1d_magic(
            ys, first_frame, last_frame, frame_steps, spline_fit_degree)
        _, xs = interp1d_magic(
            xs, first_frame, last_frame, frame_steps, spline_fit_degree)
        output_value = ""
        for frame, y, x in zip(frames, ys, xs):
            output_value = f"{y:.2f} {x:.2f}"
            ouptut[int(frame)] = output_value
        # Repeat the last frame until the next frame
        for frame in range(last_frame, next_frame):
            ouptut[int(frame)] = output_value

    @staticmethod
    def _get_tp_suffixes_crds_facing_crds(
            frames_stack: deque[tuple[int, CoordinatesNode]],
            ouptut: dict[int, str], spline_fit_degree: int) -> None:
        '''
        Used by from_coordinates_list.

        Gets suffixes of the /tp command for 'facing coordinates tp' nodes and
        adds them to the 'output' dictionary. The 'facing coordinates tp'
        command is the command that follows pattern
        '/tp {x} {y} {z} {fx} {fy} {fz}'. This function takes care of the
        'fx'm 'fy' and 'fz' part.
        '''
        first_frame, c = frames_stack[0]
        last_frame = first_frame  # The last CoordinatesRotated frame
        next_frame = first_frame  # The frame after the last frame
        xs: list[float] = []
        ys: list[float] = []
        zs: list[float] = []
        while isinstance(c.coordinates, CoordinatesFacingCoordinates):
            last_frame = next_frame
            xs.append(c.coordinates.facing_x)
            ys.append(c.coordinates.facing_y)
            zs.append(c.coordinates.facing_z)
            if len(frames_stack) == 0:
                break
            next_frame, c = frames_stack.popleft()
        frame_steps = last_frame - first_frame
        frames, xs = interp1d_magic(
            xs, first_frame, last_frame, frame_steps, spline_fit_degree)
        _, ys = interp1d_magic(
            ys, first_frame, last_frame, frame_steps, spline_fit_degree)
        _, zs = interp1d_magic(
            zs, first_frame, last_frame, frame_steps, spline_fit_degree)
        output_value = ""
        for frame, x, y, z in zip(frames, xs, ys, zs):
            output_value = f"facing {x:.2f} {y:.2f} {z:.2f}"
            ouptut[int(frame)] = output_value
        # Repeat the last frame until the next frame
        for frame in range(last_frame, next_frame):
            ouptut[int(frame)] = output_value

@dataclass
class AnimationControllerTimeline:
    '''
    AnimationControllerTimeline is a class that represents the main timeline
    of the dialogue file. It's a collection of AnimationTimeline objects.
    AnimationControllerTimeline produces a Minecraft animation controller with
    which sequentially plays the animations (from AnimationTimeline objects)
    using the 'q.all_animations_finished' Molang query.

    The states from the AnimationControllerTimeline are grouped together in
    as little groups as possible. Jump between animation states may cause
    creation of multiple timelines.

    The states list is a list of tuples of AnimationTimeline objects. The
    AnimationTimelines groupped together in the same tuple are intended to
    be played simultaneously during the same state.
    '''
    states: list[tuple[AnimationTimeline, ...]]

    @staticmethod
    def from_timeline_nodes(
            timeline: list[Union[MessageNode, DialogueNode, CameraNode]],
            config_provider: ConfigProvider,
            rp_path: Path) -> AnimationControllerTimeline:
        run_once_counter = count()
        events: list[tuple[AnimationTimeline, ...]] = []
        timeline_deque = deque(timeline)
        while len(timeline_deque) > 0:
            node = timeline_deque[0]
            if isinstance(node, MessageNode):
                message_nodes: list[MessageNode] = []
                while isinstance(node, MessageNode):
                    message_nodes.append(node)
                    timeline_deque.popleft()
                    if len(timeline_deque) <= 0:
                        break
                    node = timeline_deque[0]
                    
                animation_timeline = AnimationTimeline.from_message_node_list(
                    config_provider, message_nodes, rp_path, run_once_counter)
                events.append((animation_timeline,))
            elif isinstance(node, DialogueNode):
                timeline_deque.popleft()
                raise NotImplementedError()
            elif isinstance(node, CameraNode):
                timeline_deque.popleft()
                time_settings = SettingsNode.settings_list_to_dict(
                    node.time.settings)
                # spline_fit_degree
                try:
                    spline_fit_degree = int(
                        time_settings["spline_fit_degree"])
                except KeyError:
                    spline_fit_degree = 3
                except ValueError:
                    raise CompileError(
                        "Unable to parse spline_fit_degree as an integer. "
                        f"Line: {node.time.token.line_number}")
                time: int
                # Not all camera nodes have messages
                messages_timeline: Optional[AnimationTimeline] = None
                if len(node.time.messages) > 0:
                    if 'time' in time_settings:
                        raise CompileError(
                            "When using message nodes in the camera node,"
                            " the 'time' setting is not allowed. "
                            f"Line: {node.token.line_number}")
                    messages_timeline = (
                        AnimationTimeline.from_message_node_list(
                            config_provider, node.time.messages, rp_path,
                            run_once_counter)
                    )
                    time = messages_timeline.time
                else:
                    if 'time' not in time_settings:
                        raise CompileError(
                            "When using message nodes in the camera node,"
                            " the 'time' setting is required. "
                            f"Line: {node.token.line_number}")
                    try:
                        time = seconds_to_halfticks(time_settings['time'])
                    except ValueError:
                        raise CompileError(
                            "Unable to convert the 'time' property to a "
                            f"number. Line: {node.token.line_number}")
                    if time < 0:
                        raise CompileError(
                            "The 'time' property must be greater than 0. "
                            f"Line: {node.token.line_number}")
                camera_timeline = AnimationTimeline.from_coordinates_list(
                    node, time, spline_fit_degree=spline_fit_degree)
                if messages_timeline is not None:
                    events.append((camera_timeline, messages_timeline))
                else:
                    events.append((camera_timeline,))
            else:
                raise ValueError(f"Unknown node type: {node}")
        return AnimationControllerTimeline(events)

def seconds_to_halfticks(duration: Union[float, str, int]) -> int:
    '''
    Converts duration in seconds to half-tick count. The values are always
    rounded up. A half-tick is a half of a tick. There is 40 half-ticks in
    a second.

    The generator uses half-ticks instead of ticks to make camera movement
    in animations move more smoothly in case of skipping frames.
    '''
    return int(math.ceil(float(duration) * 40))


def b_spline_magic(
        y: list[float], x_start: float, x_end: float,
        n_points: int, k: int=3) -> tuple[list[float], list[float]]:
    '''
    The b_spline_magic function uses science to magically calculate evenly
    separated points on a B-spline of 'k' degree that goes through xy points.
    The 'x' values are calculated from 'x_start', 'x_end' and
    'n_points'. They evenly distributed between start and end.

    Returns two lists of coordinates, the first one is for x and the secod is
    for y.

    - k=1 - linear
    - k=2 - quadratic
    - k=3 - cubic
    ...goes up to 5

    THIS IS A LEGACY CODE. THE FUNCTION IS DEPRECATED, USE THE interp1d_magic
    FUNCTION INSTEAD.
    '''
    # Useful links:
    # https://www.delftstack.com/howto/python/python-spline/
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.splev.html
    x = np.linspace(x_start, x_end, len(y))

    # B-spline magic
    tck = scipy.interpolate.splrep(x, y, s=0, k=k)
    x_fit = np.linspace(x_start, x_end, n_points)
    y_fit = scipy.interpolate.splev(x_fit, tck, der=0)

    # Recast that to lists of floats just to make sure that errors are
    # detected early.
    return [float(x) for x in x_fit], [float(y) for y in y_fit]

def interp1d_magic(
        y: list[float], x_start: float, x_end: float,
        n_points: int, k: int=3) -> tuple[list[float], list[float]]:
    '''
    Thie iterp1d_magic function uses science to magically calculate points
    interpolated between values passed to the function. The difference between
    this function and the b_spline_magic is that the points are evenly spaced
    on the x-axis, not on the curve (or at least I think it's the difference,
    I'm not sure because it's all done in Scipy).

    The interp1d_magic uses scipy.interpolate.interp1d and the b_spline_magic
    uses scipy.interpolate.splev.
    '''
    # https://docs.scipy.org/doc/scipy/reference/generated/scipy.interpolate.interp1d.html#scipy.interpolate.interp1d
    # The kind values for scipy.interpolate.interp1d are:
    # - 'zero', 'slinear', 'linear', 'cubic', 'quadratic' - for different
    #   spline interpolation degree. 'slinear' is spline of degree 1. It
    #   returns the same (very similar) result as 'linear' but is slower.
    # - 'nearest', 'nearest-up', 'previous', 'next' - not used. Look into docs.
    #   You can use it to get the stepped animation.
    if k < 0 or k > 3:
        raise CompileError(
            "The interpolation level parameter must be between 0 and 3.")
    kind: Literal['zero', 'linear', 'quadratic', 'cubic'] = (
        'zero', 'linear', 'quadratic', 'cubic')[k]
    x = np.linspace(x_start, x_end, len(y))
    interp_func = scipy.interpolate.interp1d(x, y, kind=kind)

    interp_x = np.linspace(x_start, x_end, n_points)
    interp_y = interp_func(interp_x)
    return (
        [float(x_val) for x_val in interp_x],
        [float(y_val) for y_val in interp_y]
    )
