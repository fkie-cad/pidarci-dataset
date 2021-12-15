import json
import pathlib
import re

def get_results_for_file_content(content, operation, constant_to_address):
    operation_sign = {
        "mulu": "\\*",
        "muls": "\\*",
        "divs": "/",
        "divu": "/",
        "mods": "%",
        "modu": "%",
    }[operation]
    correctly_matched_constants = set()
    correct_matches = set()

    def value_to_funcname(value):
        return f"func_{value}".replace("-", "neg")


    for function_match in re.finditer(r"function_(?P<func_address>[0-9a-f]+)\([^\)]*\)\s*\{(?P<block>[^\}]+)\}", content):
        function_body = function_match.group("block").strip()
        function_address = int(function_match.group("func_address"), 16)

        def const_matches(value):
            fn = value_to_funcname(value)
            if fn not in constant_to_address: return False
            address = constant_to_address[fn]
            if (function_address >= address["start"]) and (function_address <= address["end"]): return value

        if    ((match := re.search(f"[^/]{operation_sign}\s*(?P<matched_constant>\-?((0x[0-9a-f]+)|(\d+)))", function_body))
            or (match := re.search(f"[^/](?P<matched_constant>\-?((0x[0-9a-f]+)|(\d+)))\s*{operation_sign}", function_body))):
            correct = False
            if "0x" in match.group("matched_constant"):
                if res := const_matches(int(match.group("matched_constant"), 16)):
                    correct = res
                elif operation.startswith("mod") and (res := const_matches(-1 * int(match.group("matched_constant"), 16))):
                    correct = res
                elif "return -(" in function_body and (res := const_matches(-1 * (int(match.group("matched_constant"), 16)))):
                    correct = res
            else:
                if res := const_matches(int(match.group("matched_constant"))):
                    correct = res
                elif operation.startswith("mod") and (res := const_matches(-1 * int(match.group("matched_constant")))):
                    correct = res
            if correct:
                correct_matches.add(correct)
                correctly_matched_constants.add(correct)

    # gcc files
    for function_match in re.finditer(r"func_(?P<original_constant>(neg)?\d+)\([^\)]*\)\s*\{(?P<block>[^\}]+)\}(?=[^\{]+\{(?P<next_block>[^\}]+)\})", content):
        function_body = function_match.group("block").strip() + function_match.group("next_block").strip()
        original_constant = int(function_match.group("original_constant").strip().replace("neg", "-"))
        if    ((match := re.search(f"[^/]{operation_sign}\s*(?P<matched_constant>\-?(0x[0-9a-f]+)|(\d+))", function_body))
            or (match := re.search(f"(?P<matched_constant>\-?(0x[0-9a-f]+)|(\d+))\s*{operation_sign}", function_body))):
            correct = False
            if "0x" in match.group("matched_constant"):
                if int(match.group("matched_constant"), 16) == original_constant:
                    correct = True
                elif operation.startswith("mod") and int(match.group("matched_constant"), 16) == -original_constant:
                    correct = True
                elif "return -(" in function_body and (int(match.group("matched_constant"), 16) == -original_constant):
                    correct = True
            else:
                if int(match.group("matched_constant")) == original_constant:
                    correct = True
                elif operation.startswith("mod") and int(match.group("matched_constant")) == -original_constant:
                    correct = True
            if correct:
                correct_matches.add(original_constant)
                correctly_matched_constants.add(original_constant)

    if operation.endswith("u"): to_be_matched = set(range(2,2048,1))
    elif operation == 'mods': to_be_matched = set(range(2, 1025))
    else: to_be_matched = set(range(-1023,1024,1)) - set([-1,0,1])

    fn = len(to_be_matched - correctly_matched_constants) * (2 if operation == 'mods' else 1)
    tp = len(correct_matches)
    return {
        "false_negatives": fn,
        "true_positives": tp,
        "percentage": round((tp / (tp + fn)) * 100, 1)
    }


def get_results_for_path(path):
    results = {}
    for compiler in ["gcc", "msvc"]:
        results[compiler] = {
            "x64": {},
            "x86": {}
        }
        for source_code_file in (path / f"retdec-output-{compiler}").glob('*.c'):
            if not source_code_file.is_file(): continue
            fn_addr = {}
            if "msvc" in source_code_file.stem:
                fn_addr_path = str(pathlib.Path("tests") / "evaluation" / "msvc" / "function-info" / source_code_file.stem[:-4]) + ".json"
                fn_addr_path = pathlib.Path(fn_addr_path)
                with fn_addr_path.open(mode="r") as infile:
                    fn_addr = json.load(infile)

            with source_code_file.open(mode="r") as infile:
                src = infile.read()
            arch = "x64" if "x64" in source_code_file.stem else "x86"
            if src:
                results[compiler][arch][source_code_file.stem] = get_results_for_file_content(src, operation=source_code_file.stem[:4], constant_to_address=fn_addr)
            else: results[compiler][arch][source_code_file.stem] = "File Empty"
    return results


if __name__ == "__main__":
    result = get_results_for_path(pathlib.Path("path_with_retdec_decompiled_output"))
    with open("retdec_results.json", "w") as outfile:
        json.dump(result, outfile, sort_keys=True, indent=4)
