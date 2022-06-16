'''
The message_duration module provides utilities for getting the duration of an
animation needed for a text message.
'''
from pathlib import Path
from typing import Optional

import mutagen


def cpm_duration(text:str , cpm: float) -> float:
    '''
    Returns duration of reading text based characters per minute speed.
    '''
    length = len(text)
    return (length*60)/cpm

def wpm_duration(text:str, wpm: float) -> float:
    '''
    Returns duration of reading text based words per minute speed.
    '''
    length = len(text.split(' '))
    print(f"DEBUG: {text} -> {length} -> duration: {(length*60)/wpm}")
    return (length*60)/wpm


def sound_duration(path: Path) -> Optional[float]:
    '''
    Returns duration of an `.ogg` file. In case of error returns None.
    '''
    try:
        mutFile = mutagen.File(path)
    except mutagen.MutagenError:
        return None
    if mutFile is not None and type(mutFile) is mutagen.oggvorbis.OggVorbis:
        return mutFile.info.length  # type: ignore
    return None
