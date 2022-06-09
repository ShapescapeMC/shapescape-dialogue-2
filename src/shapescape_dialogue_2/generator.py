'''
The generator module uses the data produced by the compiler to generate
Minecraft files.
'''
from __future__ import annotations

import json
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Callable, Optional

from .parser import RootAstNode, SoundProfileNode
from .compiler import (AnimationControllerTimeline, AnimationTimeline,
                       SoundCodeProvider, TimelineEvent,
                       TranslationCodeProvider, ConfigProvider)


def ticks_to_seconds(ticks: int) -> float:
    '''
    Converts ticks to seconds.
    '''
    return ticks / 20.0

class GeneratorError(Exception):
    pass

def load_json_resource_or_return_default(
        path: Path, resource_name: str,
        default_generator: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    '''
    Loads a JSON resource from the given path. If the path doesn't exist,
    calls the default generator and returns its result. Converts the exceptions
    into GeneratorErrors with more meaningful messages for the user.
    '''
    if path.exists():
        if not path.is_file():
            raise GeneratorError(
                f"'{path.as_posix()}' is not a file. Expected an "
                f"empty path or a file to save {resource_name} to.")
        try:
            with open(path, 'r', encoding='utf8') as f:
                return json.load(f)
        except (JSONDecodeError, OSError):
            raise GeneratorError(
                f"Failed to load '{path.as_posix()}' as JSON file. "
                f"Expected a valid JSON with an {resource_name}.")
    return default_generator()

@dataclass
class BpacWriter:
    '''
    A class that represents a behavior pack animation controller, can save it
    to a file. The internal data doesn't store entire file.
    '''
    path: Path
    name: str
    data: dict[str, Any]

    def save(self) -> None:
        '''
        Saves the data of the behavior pack animation controller into the file.
        '''
        # Get the existing file data or use the default if it doesn't exist
        data = load_json_resource_or_return_default(
            self.path, 'animation controller', self._get_default_file)
        # Access path to the animation controller, check if it exists (
        # overwritting is not allowed)
        full_identifier = BpacWriter.get_full_name(self.name)
        try:
            if full_identifier in data['animation_controllers']:
                raise GeneratorError(
                    f"Animation controller '{self.name}' already exists in "
                    f"'{self.path.as_posix()}'. Unable to overwrite.")
        except (ValueError, TypeError, KeyError):
            raise GeneratorError(
                f"Unable to access animation controller of "
                f"'{self.path.as_posix()}'")
        # Save the data
        data['animation_controllers'][full_identifier] = self.data
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w', encoding='utf8') as f:
            json.dump(data, f, indent='\t', ensure_ascii=False)

    def _get_default_file(self) -> dict[str, Any]:
        '''
        Returns the default JSON file.
        '''
        return {
            "format_version": "1.17.0",
            "animation_controllers": {}
        }

    @staticmethod
    def get_full_name(name: str) -> str:
        return f'controller.animation.{name}'

@dataclass
class BpaWriter:
    '''
    A class that represents a behavior pack animation, can save it
    to a file. The internal data doesn't store entire file.
    '''
    path: Path
    name: str
    data: dict[str, Any]

    def save(self) -> None:
        '''
        Saves the data of the behavior pack animation into the file.
        '''
        # Get the existing file data or use the default if it doesn't exist
        data = load_json_resource_or_return_default(
            self.path, 'animation', self._get_default_file)
        # Access path to the animation, check if it exists (
        # overwritting is not allowed)
        full_identifier = BpaWriter.get_full_name(self.name)
        try:
            if full_identifier in data['animations']:
                raise GeneratorError(
                    f"Animation '{self.name}' already exists in "
                    f"'{self.path.as_posix()}'. Unable to overwrite.")
        except (ValueError, TypeError, KeyError):
            raise GeneratorError(
                f"Unable to access animation of "
                f"'{self.path.as_posix()}'")
        # Save the data
        data['animations'][full_identifier] = self.data
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w', encoding='utf8') as f:
            json.dump(data, f, indent='\t', ensure_ascii=False)

    def _get_default_file(self) -> dict[str, Any]:
        '''
        Returns the default JSON file.
        '''
        return {
            "format_version": "1.18.0",
            "animations": {}
        }

    @staticmethod
    def get_full_name(name: str) -> str:
        return f'animation.{name}'

@dataclass
class LangFileWriter:
    path: Path
    data: list[str]

    def save(self) -> None:
        data = []
        if self.path.exists():
            with open(self.path, 'r', encoding='utf8') as f:
                data.append(f.read())
        data.extend(self.data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.path, 'w', encoding='utf8') as f:
            f.write('\n'.join(data))

@dataclass
class SoundDefinitionsJsonWriter:
    path: Path
    data: dict[str, Any]

    def save(self) -> None:
        if self.path.exists():
            with self.path.open('r', encoding='utf8') as f:
                data = json.load(f)
        else:
            data = {
                "format_version": "1.14.0",
                "sound_definitions": {}
            }
        for k, v in self.data.items():
            if k in data['sound_definitions']:
                raise GeneratorError(
                    f"Sound '{k}' already exists in "
                    f"'{self.path.as_posix()}'. Unable to overwrite.")
            data['sound_definitions'][k] = v
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('w', encoding='utf8') as f:
            json.dump(data, f, indent='\t', ensure_ascii=False)

    def inspect_sound_definition(self, name: str, value: str):
        '''
        Inspects sound definition checking whether the provided sound exists
        or not and prints a warning if it doesn't.
        '''
        print(f'{name}: {value}')

@dataclass
class BpEntityWriter:
    path: Path
    data: dict[str, Any]

    def save(self) -> None:
        if self.path.exists():
            raise GeneratorError(
                f"Unable to generate entity because the file already exists: "
                f"'{self.path.as_posix()}'")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open('w', encoding='utf8') as f:
            json.dump(self.data, f, indent='\t', ensure_ascii=False)

@dataclass
class McfunctionWriter:
    path: Path
    data: list[str]

    def save(self) -> None:
        '''
        Saves the mcfunction file
        '''
        if self.path.exists():
            raise GeneratorError(
                f"'{self.path.as_posix()}' already exists. Unable to "
                "overwrite. Expected an empty path to save mcfunction to.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.path, 'w', encoding='utf8') as f:
                f.writelines("\n".join(self.data))
        except OSError:
            raise GeneratorError(f"Failed write to '{self.path.as_posix()}'")

@dataclass
class McfunctionGenerator:
    '''
    A class that manages the generation of mcfunciton files.
    '''
    writers: list[McfunctionWriter] = field(default_factory=list)

    def add_writer(
            self, function_name: str, event: TimelineEvent, 
            generation_settings: DialogueGenerator):
        # Check if function to generate has at least one command
        # TODO - 1 command also shouldn't be allowed it's better to just put
        # it directly into the animation
        len_events = len(event.actions)
        if len_events == 0:
            raise GeneratorError(
                f"Unable to generate the '{function_name} function because "
                "it contains no commands.")
        commands: list[str] = []
        for action in event.actions:
            command = action.to_command(
                generation_settings.tc_provider,
                generation_settings.sc_provider)
            commands.append(command)
        # Save the writer
        function_path = (
            generation_settings.bp_path / 'functions' /
            f"{function_name}.mcfunction")
        self.writers.append(McfunctionWriter(function_path, commands))

@dataclass
class BpaGenerator:
    '''
    A class that manages the generation of behavior pack animation files.
    '''
    writers: list[BpaWriter] = field(default_factory=list)

    def add_writer(
            self, name: str, timeline: AnimationTimeline,
            generation_settings: DialogueGenerator):
        # Check if timeline is not empty
        len_timeline = len(timeline.events)
        if len_timeline == 0:
            raise GeneratorError(
                f"Unable to generate the '{name}' animation because "
                "provided animation timeline is empty.")
        # The default result
        data: dict[str, Any] = {
            "loop": False,
            "animation_length": ticks_to_seconds(timeline.time + 1),
            "timeline": {}
        }
        sorted_event_keys = sorted(timeline.events.keys())
        for t in sorted_event_keys:
            time = ticks_to_seconds(t)
            event = timeline.events[t]
            function_name = (
                Path(generation_settings.subpath) / f'{name}_{t}').as_posix()
            if len(event.actions) == 1:
                command = event.actions[0].to_command(
                    generation_settings.tc_provider,
                    generation_settings.sc_provider)
                data['timeline'][str(time)] = [f"/{command}"]
            else:
                generation_settings.mcfunction_generator.add_writer(
                    function_name, event, generation_settings)
                data['timeline'][str(time)] = [f"/function {function_name}"]
        # Add the writer
        writer_path = (
            generation_settings.bp_path / 'animations' /
            f'{generation_settings.subpath}.bpa.json')
        self.writers.append(
            BpaWriter(
                writer_path, f"{generation_settings.subpath}.{name}", data))

@dataclass
class BpacGenerator:
    '''
    A class that manages the generation of behavior pack animation controller
    files.
    '''
    writers: list[BpacWriter] = field(default_factory=list)

    def add_writer(
            self, name: str, timeline: AnimationControllerTimeline,
            generation_settings: DialogueGenerator):
        # Check if timeline is not empty
        len_timeline = len(timeline.states)
        if len_timeline == 0:
            raise GeneratorError(
                f"Unable to generate the '{name}' animation controller because"
                " provided animation controller timeline is empty.")
        # The default result
        data: dict[str, Any] = {
            "initial_state": "default",
            "states": {
                "default": {
                    "transitions": [
                        {f"{name}_s0": "1.0"}
                    ]
                },
                "end": {
                    "on_entry": [
                        "@s despawn"
                    ]
                }
            }
        }
        # Populate the states with animations
        for i, state in enumerate(timeline.states):
            # Last state is called 'end' and is empty (defined above)
            state_name = f'{name}_s{i}'
            if i == len_timeline - 1:
                next_state = "end"
            else:
                next_state = f"{name}_s{i + 1}"
            # Generate animations and their names for this data structure
            animation_names: list[str] = []
            for j, animation_timeline in enumerate(state):
                animation_name = f'{state_name}_{j}'
                generation_settings.bpa_generator.add_writer(
                    animation_name, animation_timeline, generation_settings)
                # Ugly hack, getting the name of the animation from the
                # recently added writer
                animation_names.append(
                    generation_settings.bpa_generator.writers[-1].name)
            data['states'][state_name] = {
                "transitions": [
                    {next_state: "q.all_animations_finished"}
                ],
                "animations": animation_names
            }
        # Add the writer
        writer_path = (
            generation_settings.bp_path / 'animation_controllers' /
            f'{generation_settings.subpath}.bpac.json')
        self.writers.append(
            BpacWriter(
                writer_path, f"{generation_settings.subpath}.{name}", data)
        )

@dataclass
class BpEntityGenerator:
    writers: list[BpEntityWriter] = field(default_factory=list)
    
    def add_writer(
            self, name: str,
            generation_settings: DialogueGenerator):
        data: dict[str, Any] = {
            "format_version": "1.17.0",
            "minecraft:entity": {
                "description": {
                    "identifier": f"{generation_settings.namespace}:{name}",
                    "is_spawnable": False,
                    "is_summonable": True,
                    "animations": {
                        anim.name: BpaWriter.get_full_name(anim.name)
                        for anim in generation_settings.bpa_generator.writers
                    } | {
                        f"{ac.name}_controller": BpacWriter.get_full_name(ac.name)
                        for ac in generation_settings.bpac_generator.writers
                    },
                    "scripts": {
                        "animate": [
                            {f"{ac.name}_controller": f"q.variant == {i}"}
                            for i, ac in enumerate(
                                generation_settings.bpac_generator.writers)
                        ]
                    }

                },
                "component_groups": {
                    "despawn": {
                        "minecraft:instant_despawn": {}
                    }
                },
                "components": {
                    "minecraft:pushable": {
                        "is_pushable": False,
                        "is_pushable_by_piston": False
                    },
                    "minecraft:damage_sensor": {
                        "triggers": [
                            {
                                "cause": "all",
                                "deals_damage": False
                            }
                        ]
                    },
                    "minecraft:physics": {
                        "has_collision": False,
                        "has_gravity": False
                    },
                    "minecraft:knockback_resistance": {
                        "value": 0
                    }
                },
                "events": {
                    "despawn": {
                        "add": {
                            "component_groups": [
                                "despawn"
                            ]
                        }
                    }
                }
            }
        }
        animations = {}
        scripts_animate = []
        for anim in generation_settings.bpa_generator.writers:
            # Add to the list of available animations
            animations[anim.name] = BpaWriter.get_full_name(anim.name)
        for i, ac in enumerate(generation_settings.bpac_generator.writers):
            # Add to the list of available animations
            animations[anim.name] = BpacWriter.get_full_name(anim.name)
            # Add to the list of conditionally played animations
            scripts_animate.append({ac.name: f"q.variant == {i}"})
            # Add corresponding component groups
            data['minecraft:entity']['component_groups'][f'{ac.name}'] = {
                "minecraft:variant": {
                    "value": i
                }
            }
            # Add corresponding events
            data['minecraft:entity']['events'][f'{ac.name}'] = {
                "add": {
                    "component_groups": [
                        f'{ac.name}'
                    ]
                }
            }
        # Add the writer
        writer_path = (
            generation_settings.bp_path / 'entities' /
            f'{name}.bpe.json')
        self.writers.append(BpEntityWriter(writer_path, data))

@dataclass
class DialogueGenerator:
    '''
    The main gnerator class that handles the generation of everything. For
    one sound profile setting.
    '''
    bp_path: Path
    rp_path: Path
    subpath: str  # The subpath from the main folder of given resource
    namespace: str  # The namespace used for the name of the entity

    mcfunction_generator: McfunctionGenerator = field(
        default_factory=McfunctionGenerator)
    bpac_generator: BpacGenerator = field(default_factory=BpacGenerator)
    bpa_generator: BpaGenerator = field(default_factory=BpaGenerator)
    tc_provider: TranslationCodeProvider = field(
        default_factory=lambda: TranslationCodeProvider("default"))
    bp_entity_generator: BpEntityGenerator = field(default_factory=BpEntityGenerator)

    sc_provider: SoundCodeProvider = field(default_factory=SoundCodeProvider)

    sounds_definitions_writer: Optional[SoundDefinitionsJsonWriter] = None
    lang_file_writer: Optional[LangFileWriter] = None

    def generate(self, tree: RootAstNode):
        def generate_bpac_anim_and_mcfunction(
                sound_profile_name: str,
                sound_profile: Optional[SoundProfileNode]):
            config_provider = ConfigProvider(tree.settings, sound_profile)
            ac_timeline = AnimationControllerTimeline.from_timeline_nodes(
                tree.timeline, config_provider, self.rp_path)
            # Bpac generator generates, bpac, anim and mcfunctions
            self.bpac_generator.add_writer(
                sound_profile_name, ac_timeline, self)

        # The text is the same for all variants, so there is no need to include
        # sound profile name in the dialogue prefix.
        self.tc_provider.prefix = (
                f'dialogue.{self.subpath}')
        # Generate bpac, anim, mcfunctions
        if tree.sound_profiles is not None:
            for sound_profile in tree.sound_profiles.sound_profiles:
                generate_bpac_anim_and_mcfunction(
                    sound_profile.name, sound_profile)
        else:
            generate_bpac_anim_and_mcfunction(
                "default", None)
        # Generate sound_definitions.json
        sounds_data = {}
        self.sc_provider.inspect_sound_paths(self.rp_path)
        for k, v in self.sc_provider.walk_names():
            sounds_data[k] = {
                "category": "music",
                "sounds": [v]
            }
            
        self.sounds_definitions_writer = SoundDefinitionsJsonWriter(
            self.rp_path / 'sounds/sound_definitions.json', sounds_data)
        # Generate en_us.lang file
        translation_data = self.tc_provider.get_translation_file()
        self.lang_file_writer = LangFileWriter(
            self.rp_path / 'texts/en_US.lang', translation_data)
        # Generate the entity
        self.bp_entity_generator.add_writer(self.subpath, self)

    def save_all(self):
        for writer in self.mcfunction_generator.writers:
            writer.save()
        for writer in self.bpac_generator.writers:
            writer.save()
        for writer in self.bpa_generator.writers:
            writer.save()
        for writer in self.bp_entity_generator.writers:
            writer.save()
        self.sounds_definitions_writer.save()
        self.lang_file_writer.save()
