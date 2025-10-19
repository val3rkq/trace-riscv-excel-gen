from pathlib import Path
from typing import List, Dict, Union


SPLIT_CHAR = "?"


def words_end_positions(text: str) -> Dict[int, str]:
    words: List[str] = text.split()
    positions: Dict[int, str] = {}
    start_index: int = 0

    for word in words:
        start_pos: int = text.find(word, start_index)
        if start_pos == -1:
            continue
        end_pos: int = start_pos + len(word) - 1
        positions[end_pos] = word
        start_index = end_pos + 1
        
    return positions


def find_first_data_line(lines: List[str]) -> int:
    for index, line in enumerate(lines):
        if line.strip().startswith("0"):
            return index
    raise Exception("First data line not found! Make sure first line of data starts with zero!")


def value_by_end_index(line: str, end_index: int) -> str:
    start_index: int = end_index
    while start_index > 0 and not line[start_index].isspace():
        start_index -= 1
    return line[start_index + 1: end_index + 1]


def replace_char_inside_braces(text: str, replacing_char: str, replaced_char: str) -> str:
    depth: int = 0
    result = []
    for char in text:
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
        if depth > 0 and char == replacing_char:
            result.append(replaced_char)
        else:
            result.append(char)
    return "".join(result)


def unnest_braces(value: str) -> Union[str, List]:
    if not value.startswith("{"):
        return value
    assert value.endswith("}")

    value = replace_char_inside_braces(value[1:-1], SPLIT_CHAR, " ")
    values = [replace_char_inside_braces(v, " ", SPLIT_CHAR) for v in value.split(SPLIT_CHAR)]
    return list(map(unnest_braces, values))


def parse(filename: Path) -> dict:
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    first_data_line_index = find_first_data_line(lines)
    header_lines, data_lines = lines[:first_data_line_index], lines[first_data_line_index:]

    # data processing
    processed_data_lines = [replace_char_inside_braces(line, " ", SPLIT_CHAR) for line in data_lines]

    # get headers
    headers_by_ends = {}
    for line in header_lines:
        headers_by_ends.update(words_end_positions(line))

    # get data by headers
    return {
        header: [unnest_braces(value_by_end_index(line, end_index)) 
                for line in processed_data_lines]
        for end_index, header in headers_by_ends.items()
    }