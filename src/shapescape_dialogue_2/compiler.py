from __future__ import annotations
import functools
from .parser import CameraNode, DialogueNode, MessageNode, SettingsNode, SoundProfileNode
from .message_duration import (
    cpm_duration, wpm_duration, sound_duration)
from .parser import SettingsList
from dataclasses import dataclass, field
from typing import List, Literal, NamedTuple, Optional, Union, Dict
from pathlib import Path
import math

def tick(duration: Union[float, str, int]) -> int:
    '''
    Converts duration in seconds to tick count. The values are always rounded
    up.
    '''
    return int(math.ceil(float(duration) * 20))


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
    _prefix: str
    _counter: int = 1
    _cached_translations: Dict[str, int] = field(default_factory=dict)

    def get_translation_code(self, translation: str) -> str:
        '''
        Returns the translation code for given string. If the translation
        already exists it returns the code to the previously assigned
        code.
        '''
        try:
            return f'{self._prefix}{self._cached_translations[translation]}'
        except:
            result_number = self._counter
            self._counter += 1
            self._cached_translations[translation] = result_number
            return f'{self._prefix}.{result_number}'

    def get_translation_file(self) -> List[str]:
        '''
        Returns a list of strings to be inserted into the .lang file.
        '''
        return [
            f'{self._prefix}.{index}={value}'
            for value, index in self._cached_translations.items()
        ]

class ConfigProvider:
    '''
    ConfigProvider handles access to the configuration of the dialogue file.
    The configuratino includes the global settings and a sound profile.
    '''
    def __init__(
            self, settings: SettingsNode,
            sound_profile: Optional[SoundProfileNode]=None):
        self.settings = ConfigProvider.parse_settings(settings.settings)
        self.sound_profile: Optional[Dict[str, Path]] = (
            None if sound_profile is None else
            ConfigProvider.parse_sound_profile(sound_profile))

    @staticmethod
    def parse_settings(settings: SettingsList) -> Dict[str, str]:
        '''
        Returns a dictionary of settings from SettingsNode, chceks if there
        is no duplicate keys.
        '''
        settings_dict: Dict[str, str] = {}
        for setting in settings:
            if setting.name in settings_dict:
                raise CompileError(
                    f'Duplicate setting {setting.name} at line '
                    f'{setting.token.line_number}')
            settings_dict[setting.name] = setting.value
        return settings_dict

    @staticmethod
    def parse_sound_profile(
            sound_profile: SoundProfileNode) -> Dict[str, Path]:
        '''
        Returns a dictionary with available mappings of the sound profile
        to file paths.
        '''
        sound_profile_dict: Dict[str, Path] = {}
        for variant in sound_profile.sound_profile_variant:
            variant_settings = variant.settings
            if variant.name in sound_profile_dict:
                raise CompileError(
                    f'Duplicate sound profile entry '
                    f'{variant.name} at line '
                    f'{variant.token.line_number}')
            settings = ConfigProvider.parse_settings(variant_settings)
            if 'sound' not in settings:
                raise CompileError(
                    f'Missing sound setting on line '
                    f'{variant.token.line_number}')
            sound_profile_dict[variant.name] = Path(settings['sound'])
        return sound_profile_dict

    def message_node_duration(self, message_node: MessageNode) -> int:
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
        if message_node.node_type == 'blank':
            full_text = " ".join(
                node.text for node in message_node.text_nodes)
        # The settings of THIS node
        node_settings = ConfigProvider.parse_settings(message_node.settings)
        # Try using local settings
        if 'time' in node_settings:
            return tick(node_settings['time'])
        if 'wpm' in node_settings:
            if message_node.node_type == 'blank':
                raise CompileError.from_invalid_setting(message_node, 'wpm')
            try:
                wpm = float(node_settings['wpm'])
            except (ValueError, TypeError):
                raise CompileError.from_invalid_setting_value(
                    message_node, 'wpm')
            return tick(wpm_duration(full_text, wpm))
        if 'cpm' in node_settings:
            if message_node.node_type == 'blank':
                raise CompileError.from_invalid_setting(message_node, 'cpm')
            try:
                cpm = float(node_settings['cpm'])
            except (ValueError, TypeError):
                raise CompileError.from_invalid_setting_value(
                    message_node, 'cpm')
            return tick(cpm_duration(full_text, cpm))
        if 'sound' in node_settings:
            if (
                    self.sound_profile is not None and
                    ":" in node_settings['sound']):
                sound_variant, sound_name = node_settings['sound'].split(':')
                if sound_variant not in self.sound_profile:
                    raise CompileError(
                        f"Trying to use undefined sound variant "
                        f"{sound_variant} of the sound {sound_name} on "
                        f"line {message_node.token.line_number}")
                sound_path = self.sound_profile[sound_variant] / sound_name
            else:
                sound_path = Path(node_settings['sound'])
            duration = sound_duration(sound_path)
            if duration is not None:
                return tick(duration)
        # 'wpm' and 'cpm' shouldn't give errors from 'blank' message nodes
        # if these properties are implemented in global settings
        if 'wpm' in self.settings and message_node.node_type != 'blank':
            return tick(wpm_duration(full_text, float(self.settings['wpm'])))
        if 'cpm' in self.settings and message_node.node_type != 'blank':
            return tick(cpm_duration(full_text, float(self.settings['cpm'])))
        # TODO - Should I use 'time' property from global settings? Should
        # the local and global settings be converted to a proper type before
        # we reach this point?
        raise CompileError(
            f'Cannot calculate duration of message node at line '
            f'{message_node.token.line_number}')

@dataclass
class TimelineEventAction:
    '''
    TimelineEventAction is a single action that is executed during a timeline
    event. Actions are instand and don't have duration. Single timeline event
    can have multiple actions.
    '''
    action_type: Literal["tell", "title", "actionbar", "command", "subtitle"]
    value: str

    def to_command(self, tc_provider: TranslationCodeProvider) -> str:
        '''
        Returns the command to be executed in Minecraft sequence.
        '''
        if self.action_type == "tellraw":
            translation_code = tc_provider.get_translation_code(self.value)
            return  (
                '/tellraw @a '
                f'{{"rawtext":[{{"translate":"{translation_code}"}}]}}')
        elif self.action_type == "title":
            translation_code = tc_provider.get_translation_code(self.value)
            return  (
                '/titleraw @a title'
                f'{{"rawtext":[{{"translate":"{translation_code}"}}]}}')
        elif self.action_type == "actionbar":
            translation_code = tc_provider.get_translation_code(self.value)
            return  (
                '/titleraw @a actionbar'
                f'{{"rawtext":[{{"translate":"{translation_code}"}}]}}')
        elif self.action_type == "subtitle":
            translation_code = tc_provider.get_translation_code(self.value)
            return  (
                '/titleraw @a subtitle'
                f'{{"rawtext":[{{"translate":"{translation_code}"}}]}}')
        elif self.action_type == "command":
            return self.value
        else:
            raise ValueError(f"Unknown action type: {self.action_type}")

@dataclass
class TimelineEvent:
    '''
    Timeline event is a single event that takes place on a timeline.
    '''
    actions: List[TimelineEventAction]

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
    events: Dict[int, TimelineEvent]

    @staticmethod
    def from_events_list(
            settings: ConfigProvider,
            timeline_nodes: List[MessageNode],
            tc_provider_prefix: str) -> AnimationTimeline:
        '''
        Creates a Timeline from a list of CameraNodes and MessageNodes.
        '''
        tc_provider = TranslationCodeProvider(tc_provider_prefix)
        events: Dict[int, TimelineEvent] = {}

        def add_event_action(time: int, *actions: TimelineEventAction):
            if time not in events:
                events[time] = TimelineEvent(actions=[])
            events[time].actions.extend(actions)

        # time is the time of the event on the timeline measured in Minecraft
        # ticks
        time: int = 0
        for node in timeline_nodes:
            duration = settings.message_node_duration(node)
            actions: List[TimelineEventAction]
            if node.node_type == 'tell':
                actions = [  # The messages
                    TimelineEventAction('tell', text_node.text)
                    for text_node in node.text_nodes
                ]
            elif node.node_type == 'blank':
                actions = []
            elif node.node_type == 'title':
                if len(node.text_nodes) == 1:
                    actions = [  # The title
                        TimelineEventAction('title', node.text_nodes[0].text)
                    ]
                elif len(node.text_nodes) == 2:
                    actions = [  # The title and subtitle
                        TimelineEventAction('title', node.text_nodes[0].text),
                        TimelineEventAction('subtitle', node.text_nodes[1].text)
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
                    TimelineEventAction('actionbar', text_node.text)
                    for text_node in node.text_nodes
                ]
            else:
                raise ValueError("Unknown MessageNode type")
            actions += [
                TimelineEventAction('command', text_node.text)
                for text_node in node.command_nodes
            ]
            if node.on_exit_node is not None:
                on_exit_actions = [
                    TimelineEventAction('command', text_node.text)
                    for text_node in node.on_exit_node.command_nodes
                ]
                add_event_action(time + duration, *on_exit_actions)
            for schedule_node in node.schedule_nodes:
                schedule_time = tick(  # Should be safe (parser checks that)
                    ConfigProvider.parse_settings(
                        schedule_node.settings)['time'])
                scheduled_actions = [
                    TimelineEventAction('command', text_node.text)
                    for text_node in schedule_node.command_nodes
                ]
                add_event_action(time + schedule_time, *scheduled_actions)
            for loop_node in node.loop_nodes:
                loop_time = tick(  # This should be safe (parser checks that)
                    ConfigProvider.parse_settings(
                        loop_node.settings)['time'])
                if loop_time <= 0:
                    loop_time = 1  # TODO - should I log a warning?
                looping_actions = [
                    TimelineEventAction('command', text_node.text)
                    for text_node in loop_node.command_nodes
                ]
                loop_time_sum = 0
                while loop_time_sum < duration:
                    add_event_action(time + loop_time_sum, *looping_actions)
                    loop_time_sum += loop_time
            add_event_action(time, *actions)
            time = time + duration
        return AnimationTimeline(events)
