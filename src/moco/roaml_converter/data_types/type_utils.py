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
from typing import Any, Dict, List, MutableSequence, Optional, Tuple, Type

from lxml.etree import _Element as XmlElement

from moco.moco_common.array_type import ArrayInfo
from moco.moco_common.ecmascript_interpretation import parse_ecmascript_expr_to_type

# TODO: add lower and upper bounds depending on the n. of bits used.
# TODO: add support to uint
# TODO: Maybe rename, after this bloodbath is over...
SCXML_DATA_STR_TO_TYPE: Dict[str, Type] = {
    "bool": bool,
    "float32": float,
    "float64": float,
    "int8": int,
    "int16": int,
    "int32": int,
    "int64": int,
    "uint8": int,
    "uint16": int,
    "uint32": int,
    "uint64": int,
    "string": str,
}

# The keyword used to determine the length of an array and its type
ARRAY_LENGTH_SUFFIX = "length"
ARRAY_LENGTH_TYPE = "uint64"

# What to use for representing member access in plain SCXML (instead of '.' in HL-SCXML)
MEMBER_ACCESS_SUBSTITUTION = "__"


def is_type_string_array(data_type: str) -> bool:
    """Check if the data type defined in the string is related to an array."""
    return re.match(r"^.+\[[0-9]*\]$", data_type) is not None


def get_type_string_of_array(data_type: str) -> str:
    """Remove the array bit from the type string (works only with 1D array declarations)."""
    assert is_type_string_array(data_type)
    brackets = "".join(re.findall(r"(\[[0-9]*\])", data_type))
    # Make sure this is the end of the string
    assert data_type.endswith(brackets), f"Expected '{brackets}' at the end of '{data_type}'"
    return data_type.removesuffix(brackets)


def is_type_string_base_type(data_type: str) -> bool:
    """
    Check if the string is a base type.
    """
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
        return MutableSequence
    return SCXML_DATA_STR_TO_TYPE[data_type]


def convert_string_to_type(value: str, data_type: str, elem: XmlElement) -> Any:
    """
    Convert a value to the provided data type.
    """
    expected_type = get_data_type_from_string(data_type)
    interpreted_type = parse_ecmascript_expr_to_type(value, {}, elem)
    assert isinstance(
        interpreted_type, expected_type
    ), f"Mismatched type: {value} evaluates to {interpreted_type}, but {expected_type} is expected."
    return interpreted_type(value)


def get_type_string_from_type_and_dimensions(base_type: str, dimensions: List[Optional[int]]):
    """
    Generate the type string from the base type and array dimensions.

    E.g. uint32, [None, 1, 2, None] => uint32[][1][2][]
    """
    str_dims: List[str] = ["" if dim is None else str(dim) for dim in dimensions]
    return base_type + "".join(f"[{v_dim}]" for v_dim in str_dims)


def get_array_type_and_dimensions_from_string(data_type: str) -> Tuple[str, List[Optional[int]]]:
    """
    Given an array type string, return its base type and each dimension's max size.

    E.g. CustomType[][5][10] will return "CustomType" and [None, 5, 10].
    """
    assert is_type_string_array(data_type), f"Error: SCXML data: '{data_type}' is not an array."
    array_type_str = get_type_string_of_array(data_type)
    dim_matches = re.findall(r"(\[([0-9]*)\])", data_type)
    array_max_sizes = [None if dim_str == "" else int(dim_str) for _, dim_str in dim_matches]
    return array_type_str, array_max_sizes


def get_array_info(data_type: str, expect_base_type: bool = True) -> ArrayInfo:
    """
    Given an array type string, return the related ArrayInfo.

    E.g. float[][5][10] will return n_dims=3 and array_max_sizes=(None, 5, 10).

    :param data_type: A string representing the array type. Must be a valid array type string.
    :param expect_base_type: A flag indicating whether to expect a base type in the type string.
    :return: An ArrayInfo object containing all required info.
    """
    assert is_type_string_array(data_type), f"Error: SCXML data: '{data_type}' is not an array."
    array_type_str, array_max_sizes = get_array_type_and_dimensions_from_string(data_type)
    n_dims = len(array_max_sizes)
    if expect_base_type:
        array_py_type = SCXML_DATA_STR_TO_TYPE[array_type_str]
        return ArrayInfo(array_py_type, n_dims, array_max_sizes, expect_base_type)
    return ArrayInfo(array_type_str, n_dims, array_max_sizes, expect_base_type)
