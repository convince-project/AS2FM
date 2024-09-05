# Copyright (c) 2024 - for information on the respective copyright owner
# see the NOTICE file

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Collection of various utilities for scxml entries."""

from typing import Any, Dict, Type, MutableSequence

from scxml_converter.scxml_entries import ScxmlBase

# TODO: add lower and upper bounds depending on the n. of bits used.
# TODO: add support to uint
SCXML_DATA_STR_TO_TYPE: Dict[str, Type] = {
    "bool": bool,
    "float32": float,
    "float64": float,
    "int8": int,
    "int16": int,
    "int32": int,
    "int64": int,
    "int32[]": MutableSequence[int],  # array.array('i): https://stackoverflow.com/a/67775675
}


def all_non_empty_strings(*in_args) -> bool:
    """
    Check if all the arguments are non-empty strings.

    :param kwargs: The arguments to be checked.
    :return: True if all the arguments are non-empty strings, False otherwise.
    """
    for arg_value in in_args:
        if not isinstance(arg_value, str) or len(arg_value) == 0:
            return False
    return True


def is_non_empty_string(scxml_type: Type[ScxmlBase], arg_name: str, arg_value: str) -> bool:
    """
    Check if a string is non-empty.

    :param scxml_type: The scxml entry where this function is called, to write error msgs.
    :param arg_name: The name of the argument, to write error msgs.
    :param arg_value: The value of the argument to be checked.
    :return: True if the string is non-empty, False otherwise.
    """
    valid_str = isinstance(arg_value, str) and len(arg_value) > 0
    if not valid_str:
        print(f"Error: SCXML entry from {scxml_type.__name__}: "
              f"Expected non-empty argument {arg_name}.")
    return valid_str


def convert_string_to_type(value: str, data_type: str) -> Any:
    """
    Convert a value to the provided data type. Raise if impossible.
    """
    assert data_type in SCXML_DATA_STR_TO_TYPE, \
        f"Error: SCXML conversion of data entry: Unknown data type {data_type}."
    assert isinstance(value, str), \
        f"Error: SCXML conversion of data entry: expected a string, got {type(value)}."
    assert len(value) > 0, "Error: SCXML conversion of data entry: Empty string."
    assert '[' not in data_type, \
        f"Error: SCXML conversion of data entry: Cannot convert array type {data_type}."
    return SCXML_DATA_STR_TO_TYPE[data_type](value)
