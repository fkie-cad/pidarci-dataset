import json
import pathlib
import re

def get_results_for_file_content(content, operation):
    operation_sign = {
        "mulu": "\*",
        "muls": "\*",
        "divs": "/",
        "divu": "/",
        "mods": "%",
        "modu": "%",
    }[operation]
    correctly_matched_constants = set()
    correct_matches = set()
    for function_match in re.finditer(r"func_(?P<original_constant>(neg)?\d+)\([^\)]*\)\s*\{(?P<block>[^\}]+)\}", content):
        function_body = function_match.group("block").strip()
        original_constant = int(function_match.group("original_constant").strip().replace("neg", "-"))
        if    ((match := re.search(f"[^/]{operation_sign}\s*(?P<matched_constant>\-?((0x[0-9a-fA-F]+)|(\d+)))", function_body))
            or (match := re.search(f"[^/](?P<matched_constant>\-?((0x[0-9a-fA-F]+)|(\d+)))\s*{operation_sign}", function_body))):
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
        for source_code_file in (path / compiler).glob('*'):
            print(source_code_file)
            if not source_code_file.is_file(): continue
            if not str(source_code_file).endswith(".decompiled"): continue
            with source_code_file.open(mode="r") as infile:
                src = infile.read()
            arch = "x64" if "x64" in source_code_file.stem else "x86"
            if src:
                results[compiler][arch][source_code_file.stem] = get_results_for_file_content(src, operation=source_code_file.stem[:4])
            else: results[compiler][arch][source_code_file.stem] = "File Empty"
    return results


if __name__ == "__main__":
    result = get_results_for_path(pathlib.Path("path_with_ida_decompiled_output"))
    with open("ida_results.json", "w") as outfile:
        json.dump(result, outfile, sort_keys=True, indent=4)
