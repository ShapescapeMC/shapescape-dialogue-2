'''
The generator module uses the data produced by the compiler to generate
Minecraft files.
'''
from __future__ import annotations

import json
from dataclasses import dataclass, field
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Optional, Union

from .compiler import (AnimationControllerTimeline, AnimationTimeline,
                       ConfigProvider, SoundCodeProvider, TimelineEvent,
                       TranslationCodeProvider)
from .parser import RootAstNode, SoundProfileNode


def ticks_to_seconds(ticks: int) -> float:
    '''
    Converts ticks to seconds.
    '''
    return ticks / 20.0

class GeneratorError(Exception):
    pass

def try_load_json_resource(
        path: Path, resource_name: str) -> Optional[dict[str, Any]]:
    '''
    Loads a JSON resource from the given path, or returns None. Raises
    GeneratorError if the path exists but the resource cannot be loaded.
    '''
    if path.exists():
        if not path.is_file():
            raise GeneratorError(
                f"'{path.as_posix()}' is not a file. Expected an "
                f"empty path or a file to save {resource_name} to.")
        try:
            with open(path, 'r', encoding='utf8') as f:
                return json.load(f)  # type: ignore
        except (JSONDecodeError, OSError):
            raise GeneratorError(
                f"Failed to load '{path.as_posix()}' as JSON file. "
                f"Expected a valid JSON with an {resource_name}.")
    return None

@dataclass
class BpacWriter:
    '''
    Writes BPAC files. Can create new ones or overwrite. If existing file
    already has a controller with the same name, it raises an GeneratorError.
    '''
    path: Path
    '''The path to the BPAC relative to BP/animation_controllers'''
    short_id: str
    '''The ID of the animation controller without the prefix.'''
    data: dict[str, Any]
    '''The JSON contents of the BPAC'''

    def write(self, bp_path: Path) -> None:
        '''
        Saves the data of the behavior pack animation controller into the file.
        '''
        full_path = bp_path / 'animation_controllers' / self.path
        # Get the existing file data or use the default if it doesn't exist
        full_file_content = try_load_json_resource(
            full_path, 'animation controller')
        if full_file_content is None:
            full_file_content = {
                "format_version": "1.17.0", "animation_controllers": {}
            }
        full_identifier = BpacWriter.get_full_name(self.short_id)

        # Try to insert the new controller into the file
        try:
            if full_identifier in full_file_content['animation_controllers']:
                raise GeneratorError(
                    f"Animation controller '{self.short_id}' already exists in "
                    f"'{self.path.as_posix()}'. Unable to overwrite.")
        except (ValueError, TypeError, KeyError):
            raise GeneratorError(
                f"Unable to access animation controller of "
                f"'{self.path.as_posix()}'")
        full_file_content['animation_controllers'][full_identifier] = self.data

        # Save the data
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with full_path.open('w', encoding='utf8') as f:
            json.dump(full_file_content, f, indent='\t', ensure_ascii=False)

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
    '''The path to the BPA relative to BP/animations'''
    short_id: str
    '''The ID of the animation without the prefix.'''
    data: dict[str, Any]
    '''The JSON content of the animation'''

    def write(self, bp_path: Path) -> None:
        '''
        Saves the data of the behavior pack animation into the file.
        '''
        full_path = bp_path / 'animations' / self.path
        # Get the existing file data or use the default
        full_file_content = try_load_json_resource(
            full_path, 'animation')
        if full_file_content is None:
            full_file_content = {
                "format_version": "1.18.0", "animations": {}}

        # Try to insert the new controller into the file
        full_identifier = BpaWriter.get_full_name(self.short_id)
        try:
            if full_identifier in full_file_content['animations']:
                raise GeneratorError(
                    f"Animation '{self.short_id}' already exists in "
                    f"'{self.path.as_posix()}'. Unable to overwrite.")
        except (ValueError, TypeError, KeyError):
            raise GeneratorError(
                f"Unable to access animation of "
                f"'{self.path.as_posix()}'")
        full_file_content['animations'][full_identifier] = self.data

        # Save the data
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with full_path.open('w', encoding='utf8') as f:
            json.dump(full_file_content, f, indent='\t', ensure_ascii=False)

    @staticmethod
    def get_full_name(name: str) -> str:
        return f'animation.{name}'

@dataclass
class LangFileWriter:
    path: Path
    '''The path to the lang file relative to the RP/texts'''
    data: list[str]
    '''The list of the translations to be added to the file'''

    def write(self, rp_path: Path) -> None:
        '''Appends the translations to the lang file or creates a new one.'''
        data = []
        full_path = rp_path / 'texts' /self.path
        if full_path.exists():
            with full_path.open('r', encoding='utf8') as f:
                data.append(f.read())
        data.extend(self.data)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with full_path.open('w', encoding='utf8') as f:
            f.write('\n'.join(data))

@dataclass
class SoundDefinitionsJsonWriter:
    data: dict[str, Any]

    def write(self, rp_path: Path) -> None:
        full_path = rp_path / Path("sounds/sound_definitions.json")
        # Get the existingfile data or use default
        full_file_content = try_load_json_resource(
            full_path, '"sound_definitions.json"')
        if full_file_content is None:
            full_file_content = {
                "format_version": "1.14.0", "sound_definitions": {}}
        if 'sound_definitions' not in full_file_content:
            raise GeneratorError(
                f"Missing sound_definitions property in "
                f"'{full_path.as_posix()}'")

        # Try to insert the keys into the file
        for k, v in self.data.items():
            if k in full_file_content['sound_definitions']:
                raise GeneratorError(
                    f"Sound '{k}' already exists in "
                    f"'{full_path.as_posix()}'. Unable to overwrite.")
            full_file_content['sound_definitions'][k] = v

        # Save the data
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with full_path.open('w', encoding='utf8') as f:
            json.dump(full_file_content, f, indent='\t', ensure_ascii=False)

@dataclass
class BpeWriter:
    path: Path
    '''The path to BPE relative to BP/entities'''
    data: dict[str, Any]
    '''The JSON content of the BPE'''

    def write(self, bp_path: Path) -> None:
        '''
        Tries to write the entity file. If it already exists it throws an
        GeneratorError.
        '''
        # Check the file
        if self.path.exists():
            raise GeneratorError(
                f"Unable to generate entity because the file already exists: "
                f"'{self.path.as_posix()}'")
        # Save the file
        full_path = bp_path / 'entities' / self.path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with full_path.open('w', encoding='utf8') as f:
            json.dump(self.data, f, indent='\t', ensure_ascii=False)

@dataclass
class McfunctionWriter:
    path: Path
    '''The path to the mcfunction relative to the BP/functions'''
    data: list[str]
    '''The list of the commands to be added to the file'''

    def write(self, bp_path: Path) -> None:
        '''
        Writes the mcfunction file. If it exists raises an GeneratorError.
        '''
        # Check the file
        if self.path.exists():
            raise GeneratorError(
                f"'{self.path.as_posix()}' already exists. Unable to "
                "overwrite. Expected an empty path to save mcfunction to.")
        # Save the file
        full_path = bp_path / 'functions' / self.path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with full_path.open('w',encoding='utf8') as f:
                f.writelines("\n".join(self.data))
        except OSError:
            raise GeneratorError(f"Failed write to '{self.path.as_posix()}'")

@dataclass
class McfunctionGenerator:
    '''
    Manages the generation of mcfunciton files.
    '''
    writers: list[McfunctionWriter] = field(default_factory=list)

    def add_writer(
            self, function_id: str, event: TimelineEvent, 
            context: Context) -> None:
        # Check the content, the function needs to have at least 1 command
        len_events = len(event.actions)
        if len_events == 0:
            raise GeneratorError(
                f"Unable to generate the '{function_id} function because "
                "it contains no commands.")

        # Resolve the commands text
        commands: list[str] = []
        for action in event.actions:
            command = action.to_command(
                context.tc_provider,
                context.sc_provider)
            commands.append(command)

        # Append the writer
        function_path = Path(f"{function_id}.mcfunction")
        self.writers.append(McfunctionWriter(function_path, commands))

@dataclass
class BpaGenerator:
    '''
    Manages the generation of behavior pack animation files.
    '''
    writers: list[BpaWriter] = field(default_factory=list)

    def add_writer(
            self, bpac_state_name: str, state_animation_index: int,
            timeline: AnimationTimeline, context: Context,
            mcfunction_generator: McfunctionGenerator) -> None:
        '''
        Adds BpaWriter (and its mcfunctions), the name of the animation is
        based on the BPAC state that calls this and an index (if there are
        multiple animations for the same state)
        '''
        # shorter_bpa_id: the short ID of animation with the context.subpath
        # stripped
        # short_bpa_id: The ID of the animation without the prefix
        shorter_bpa_id = f'{bpac_state_name}_{state_animation_index}'
        short_bpa_id = f"{context.subpath}.{shorter_bpa_id}"

        # Check if timeline is not empty
        len_timeline = len(timeline.events)
        if len_timeline == 0:
            raise GeneratorError(
                f"Unable to generate the '{short_bpa_id}' animation because "
                "provided animation timeline is empty.")

        # Create animation content
        data: dict[str, Any] = {
            "loop": False,
            "animation_length": ticks_to_seconds(timeline.time + 1),
            "timeline": {}
        }
        sorted_event_keys = sorted(timeline.events.keys())
        for t in sorted_event_keys:
            time = ticks_to_seconds(t)
            event = timeline.events[t]
            full_function_id = (
                Path(context.subpath) / f'{shorter_bpa_id}_{t}').as_posix()
            if len(event.actions) == 1:
                command = event.actions[0].to_command(
                    context.tc_provider,
                    context.sc_provider)
                data['timeline'][str(time)] = [f"/{command}"]
            else:
                mcfunction_generator.add_writer(
                    full_function_id, event, context)
                data['timeline'][str(time)] = [f"/function {full_function_id}"]

        # Append the writer
        writer_path = Path(f'{context.subpath}.bpa.json')
        self.writers.append(
            BpaWriter(writer_path, short_bpa_id, data))

@dataclass
class BpacGenerator:
    '''
    Manages the generation of behavior pack animation controller files.
    '''
    writers: list[BpacWriter] = field(default_factory=list)

    def add_writer(
            self, sound_profile_name: str, timeline: AnimationControllerTimeline,
            context: Context, bpa_generator: BpaGenerator,
            mcfunction_generator: McfunctionGenerator) -> None:
        '''
        Adds BpacWriter (and its animations, and mcfunctions), the name of the
        BPAC is based on the sound profile name.
        '''
        # Generate the name and path for BPAC
        short_bpac_id = f"{context.subpath}.{sound_profile_name}"
        writer_path = Path(f'{context.subpath}.bpac.json')

        # Check if timeline is not empty
        len_timeline = len(timeline.states)
        if len_timeline == 0:
            raise GeneratorError(
                f"Unable to generate the '{short_bpac_id}' animation controller because"
                " provided animation controller timeline is empty.")

        # Create BPAC content
        data: dict[str, Any] = {
            "initial_state": "default",
            "states": {
                "default": {"transitions": [{f"{sound_profile_name}_s0": "1.0"}]},
                "end": {"on_entry": ["@s despawn"]}
            }
        }
        for i, state in enumerate(timeline.states):
            state_name = f'{sound_profile_name}_s{i}'
            if i == len_timeline - 1:
                next_state = "end"  # Last state
            else:
                next_state = f"{sound_profile_name}_s{i + 1}"
            animation_names: list[str] = []
            for j, animation_timeline in enumerate(state):
                # Generate animations
                bpa_generator.add_writer(
                    state_name, j, animation_timeline, context,
                    mcfunction_generator)
                # TODO - This is ugly, getting the name of the animation from
                # the recently added writer
                animation_names.append(
                    bpa_generator.writers[-1].short_id)
            data['states'][state_name] = {
                "transitions": [
                    {next_state: "q.all_animations_finished"}
                ],
                "animations": animation_names
            }

        # Append the writer
        self.writers.append(BpacWriter(writer_path, short_bpac_id, data))

@dataclass
class BpeGenerator:
    '''
    Manages the generato of the behavior pack entity files.
    '''
    writers: list[BpeWriter] = field(default_factory=list)
    
    def add_writer(
            self, entity_name: str, context: Context,
            bpa_generator: BpaGenerator,
            bpac_generator: BpacGenerator) -> None:
        '''
        Adds an entity writer to the list. This function uses the data
        from animation and animation controller generators. To add the
        animations to the entity.
        ''' 
        # Generate file content
        data: dict[str, Any] = {
            "format_version": "1.17.0",
            "minecraft:entity": {
                "description": {
                    "identifier": f"{context.namespace}:{entity_name}",
                    "is_spawnable": False,
                    "is_summonable": True,
                    "animations": {},
                    "scripts": {
                        "animate": []
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
        description = data["minecraft:entity"]["description"]
        animations = description["animations"]
        scripts_animate = description["scripts"]["animate"]
        for anim in bpa_generator.writers:
            # Add to the list of available animations
            animations[anim.short_id] = BpaWriter.get_full_name(anim.short_id)
        for i, ac in enumerate(bpac_generator.writers):
            # Add to the list of available animations
            animations[f"{ac.short_id}_controller"] = BpacWriter.get_full_name(
                ac.short_id)
            # Add to the list of conditionally played animations
            scripts_animate.append({f"{ac.short_id}_controller": f"q.variant == {i}"})
            # Add corresponding component groups
            data['minecraft:entity']['component_groups'][f'{ac.short_id}'] = {
                "minecraft:variant": {
                    "value": i
                }
            }
            # Add corresponding events
            data['minecraft:entity']['events'][f'{ac.short_id}'] = {
                "add": {
                    "component_groups": [
                        f'{ac.short_id}'
                    ]
                }
            }

        # Add the writer
        writer_path = Path(f'{entity_name}.bpe.json')
        self.writers.append(BpeWriter(writer_path, data))


@dataclass
class Context:
    bp_path: Path
    '''The path to the behavior pack.'''

    rp_path: Path
    '''The path to the resourcepath.'''

    subpath: str
    '''The subpath to the resource. Affects where files are generated.'''

    namespace: str
    '''The namespace to be used in generated files.'''

    tc_provider: TranslationCodeProvider = field(
        default_factory=lambda: TranslationCodeProvider("default"))
    '''The translation code provider.'''

    sc_provider: SoundCodeProvider = field(default_factory=SoundCodeProvider)
    '''The sound code provider.'''

def generate(tree: RootAstNode, context: Context) -> None:
    '''
    Generates everything from the given tree and context, and saves it to
    the filesystem.
    '''
    # The generators
    mcfunction_generator=McfunctionGenerator()
    bpac_generator =BpacGenerator()
    bpa_generator = BpaGenerator()
    bp_entity_generator = BpeGenerator()

    # The writers (simple files don't need generators)
    sounds_definitions_writer: Optional[SoundDefinitionsJsonWriter] = None
    lang_file_writer: Optional[LangFileWriter] = None

    def generate_bpac_anim_and_mcfunction(
            sound_profile_name: str,
            sound_profile: Optional[SoundProfileNode]) -> None:
        # Setup config provider
        config_provider = ConfigProvider(tree.settings, sound_profile)
        # Create timeline for BPAC
        ac_timeline = AnimationControllerTimeline.from_timeline_nodes(
            tree.timeline, config_provider, context.rp_path)
        # Generate BPAC, BPA and mcfunction
        bpac_generator.add_writer(
            sound_profile_name, ac_timeline, context, bpa_generator,
            mcfunction_generator)

    # The prefix is the same for all profiles because the text is the same
    context.tc_provider.prefix = f'dialogue.{context.subpath}'

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
    context.sc_provider.inspect_sound_paths(context.rp_path)
    for k, v in context.sc_provider.walk_names():
        sounds_data[k] = {
            "category": "music",
            "sounds": [v]
        }
    sounds_definitions_writer = SoundDefinitionsJsonWriter(sounds_data)

    # Generate en_US.lang
    translation_data = context.tc_provider.get_translation_file()
    lang_file_writer = LangFileWriter(
        Path('en_US.lang'), translation_data)

    # Generate the entity
    bp_entity_generator.add_writer(
        context.subpath, context, bpa_generator, bpac_generator)
    
    # Write everything to the filesystem
    for writer in mcfunction_generator.writers:
        writer.write(context.bp_path)
    for writer in bpac_generator.writers:
        writer.write(context.bp_path)
    for writer in bpa_generator.writers:
        writer.write(context.bp_path)
    for writer in bp_entity_generator.writers:
        writer.write(context.bp_path)
    sounds_definitions_writer.write(context.rp_path)
    lang_file_writer.write(context.rp_path)
    # TODO - Return the writers here for easier debugging?
