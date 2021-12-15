import json
import pathlib
from dataclasses import dataclass
from typing import Dict

from icecream import ic

from compiler_idioms.disassembly.smda_disassembly import SMDADisassembly
from compiler_idioms.match import Match
from compiler_idioms.matcher import Matcher

@dataclass
class FunctionInfo:
    name: str
    start_address: int
    end_address: int


def _get_constant_from_function_name(name: str) -> str:
    const = name.split('_')[-1]
    if const.startswith('neg'):
        const = const.split('g')[-1]
        const = f"-{const}"
    return const


def get_function_address_ranges(filename: str) -> Dict[str, FunctionInfo]:
    """maps constants to the functions where they should be matched:
    e.g.

    5 -> FunctionInfo( func_5, start address: 0x00, end address: 0x140)
    """
    smda = SMDADisassembly(filename)
    constant_function_mapping = {}
    for _, smda_function in smda.disassembly.xcfg.items():
        name = smda_function.function_name
        # we check only func_const()-functions
        if name.startswith('func_') or name == "main":
            instr = [i for i in smda_function.getInstructions()]
            start_address = instr[0].offset
            end_address = instr[-1].offset
            if name == "main":
                constant_function_mapping[name] = FunctionInfo(name, start_address, end_address)
            else:
                const = _get_constant_from_function_name(name)
                constant_function_mapping[const] = FunctionInfo(name, start_address, end_address)
    return constant_function_mapping


def match_is_correct(match: Match, constant_function_mapping, operation):
    if (const := str(match.constant)) in constant_function_mapping and (match.operation == 'modulo'):
        function = constant_function_mapping[const]
        function_start = function.start_address
        function_end = function.end_address
        if f'-{const}' not in constant_function_mapping:
            return function_start <= match.address <= function_end
        negative_function = constant_function_mapping[f'-{const}']
        negative_function_start = negative_function.start_address
        negative_function_end = negative_function.end_address
        return function_start <= match.address <= function_end or negative_function_start <= match.address <= negative_function_end
    if (const := str(match.constant)) in constant_function_mapping and (match.operation == operation or (match.operation == "multiplication" and operation == "multiplication unsigned")):
        function = constant_function_mapping[const]
        function_start = function.start_address
        function_end = function.end_address
        return function_start <= match.address <= function_end


def match_is_in_main(match: Match, constant_function_mapping):
    function = constant_function_mapping["main"]
    function_start = function.start_address
    function_end = function.end_address
    return function_start <= match.address <= function_end


def evaluate_operation(operation_file: pathlib.Path, eval_dict):
    operations = {
        "divs": 'division',
        "divu": 'division unsigned',
        "mods": 'modulo',
        "modu": 'modulo unsigned',
        "muls": 'multiplication',
        "mulu": 'multiplication unsigned',
    }
    matcher = Matcher()
    operation_abrev = operation_file.stem.split('_')[0]
    operation = operations[operation_abrev]
    ranges = get_function_address_ranges(str(operation_file))
    correct_matches = 0
    correct_matches_constants = set()
    inlined_matches = 0
    matches = 0
    filename = operation_file.stem
    for m in matcher.find_idioms_in_file(str(operation_file)):
        if match_is_correct(m, ranges, operation):
            correct_matches += 1
            correct_matches_constants.add(m.constant)
        elif match_is_in_main(m, ranges):
            inlined_matches += 1
            continue
        matches += 1
    if operation_abrev.endswith("u"): to_be_matched = set(range(2,2048,1))
    elif operation_abrev == 'mods': to_be_matched = set(range(2, 1025))
    else: to_be_matched = set(range(-1023,1024,1)) - set([-1,0,1])
    unmatched_constants = to_be_matched - correct_matches_constants
    print(f'Idiom: {filename}')
    print(f'True Positives: {correct_matches}')
    print(f'False Positives: {matches-correct_matches}' + (f' (and {inlined_matches} matches of inlined functions)' if inlined_matches else ""))
    print(f"False Negatives: {len(unmatched_constants)} (Unmachted values: {sorted(list(unmatched_constants))}")
    eval_dict[filename] = {"total matches": matches, "correct": correct_matches}


def evaluate():
    eval_dict = {}
    for operation_file in ('bin').glob("*gcc11_O*"):
        evaluate_operation(operation_file, eval_dict)
    with open('results.json', 'w+') as f:
        json.dump(eval_dict, f)


if __name__ == '__main__':
    evaluate()
