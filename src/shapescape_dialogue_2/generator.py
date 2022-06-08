'''
The generator module uses the data produced by the compiler to generate
Minecraft files.
'''
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class JsonFile:
    '''
    A class that represents a JSON file.
    '''
    path: Path
    data: dict

    def save(self):
        '''
        Saves the JSON file
        '''
        with open(self.path, 'w', encoding='utf8') as f:
            json.dump(self.data, f, indent='\t', ensure_ascii=False)


