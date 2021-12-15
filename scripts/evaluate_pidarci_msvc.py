import json
import pathlib
from dataclasses import dataclass
from typing import Dict

from icecream import ic

from compiler_idioms.disassembly.smda_disassembly import SMDADisassembly
from compiler_idioms.match import Match
from compiler_idioms.matcher import Matcher
from config import TEST_DIR
from scripts.evaluate_pidarci_gcc import FunctionInfo

LOG_DIR = TEST_DIR / 'evaluation' / 'logs'
MSVC_DIR = TEST_DIR / 'evaluation' / 'msvc' / 'function-info'
def get_function_address_ranges(filename: str) -> Dict[str, FunctionInfo]:
    """maps constants to the functions where they should be matched:
    e.g.

    5 -> FunctionInfo( func_5, start address: 0x00, end address: 0x140)
    """
    constant_function_mapping = {}
    file_path = pathlib.Path(filename)
    name = file_path.stem
    info_path = MSVC_DIR / f'{name}.json'
    with info_path.open('r') as f:
        data = json.load(f)
        for f_name, range in data.items():
            constant = f_name.split('_')[-1]
            if constant.startswith('neg'):
                constant = constant.replace('neg', '-')
            constant_function_mapping[constant] = FunctionInfo(f_name, range['start'], range['end'])
    return constant_function_mapping


def evaluate():
    eval_dict = {}
    for operation_file in ('bin').glob("*msvc*O*.exe"):
        import scripts.evaluate_gcc as evalgcc
        evalgcc.get_function_address_ranges = get_function_address_ranges
        evalgcc.evaluate_operation(operation_file, eval_dict)
    stats = LOG_DIR.joinpath('stats.json')
    with stats.open('w+') as f:
        json.dump(eval_dict, f)


if __name__ == '__main__':
    evaluate()
