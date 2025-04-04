# Copyright (c) 2025 - for information on the respective copyright owner
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

import re
from typing import Any, Dict, MutableSequence, Optional, Type

from as2fm.as2fm_common.ecmascript_interpretation import interpret_ecma_script_expr

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
    "int8[]": MutableSequence[int],  # array('i'): https://stackoverflow.com/a/67775675
    "int16[]": MutableSequence[int],
    "int32[]": MutableSequence[int],
    "int64[]": MutableSequence[int],
    "float32[]": MutableSequence[float],  # array('d'): https://stackoverflow.com/a/67775675
    "float64[]": MutableSequence[float],
    "string": str,
}


def is_type_string_array(data_type: str) -> bool:
    """Check if the data type defined in the string is related to an array."""
    return re.match(r"^.+\[[0-9]*\]$", data_type) is not None


def get_type_string_of_array(data_type: str) -> str:
    """Remove the array bit from the type string (works only with 1D array declarations)."""
    assert is_type_string_array(data_type)
    matches = re.match(r"^(.+)(\[[0-9]*\])$", data_type)
    assert matches is not None
    match_type = matches.group(1)
    assert match_type.count("[") == 0, "Currently only 1D arrays are supported."
    return match_type


def is_type_string_base_type(data_type: str) -> bool:
    """
    Check if the string is a base type.
    """
    data_type = data_type.strip()
    # If the data type is an array, remove the bound value
    if is_type_string_array(data_type):
        data_type = f"{get_type_string_of_array(data_type)}[]"
    return data_type in SCXML_DATA_STR_TO_TYPE


def get_data_type_from_string(data_type: str) -> Type:
    """
    Convert a data type string description to the matching python type.

    :param data_type: The data type to check.
    :return: the type matching the string, if that is valid. None otherwise.
    """
    data_type = data_type.strip()
    # If the data type is an array, remove the bound value
    if is_type_string_array(data_type):
        data_type = f"{get_type_string_of_array(data_type)}[]"
    return SCXML_DATA_STR_TO_TYPE[data_type]


def convert_string_to_type(value: str, data_type: str) -> Any:
    """
    Convert a value to the provided data type.
    """
    python_type = get_data_type_from_string(data_type)
    interpreted_value = interpret_ecma_script_expr(value)
    assert isinstance(interpreted_value, python_type), f"Failed interpreting {value}"
    return interpreted_value


def get_array_max_size(data_type: str) -> Optional[int]:
    """
    Get the maximum size of an array, if the data type is an array.
    """
    assert is_type_string_array(data_type), f"Error: SCXML data: '{data_type}' is not an array."
    match_obj = re.search(r"\[([0-9]+)\]", data_type)
    if match_obj is not None:
        return int(match_obj.group(1))
    return None
