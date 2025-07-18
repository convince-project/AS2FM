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
from dataclasses import dataclass
from typing import Any, Dict, List, MutableSequence, Optional, Tuple, Type, Union, get_args

from as2fm.as2fm_common.common import ValidPlainScxmlTypes, get_array_type_and_sizes
from as2fm.as2fm_common.ecmascript_interpretation import interpret_ecma_script_expr

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

ARRAY_BASE_TYPES = (int, float, None)


# TODO: Move this class to as2fm common and use a python type instead of an scxml string for the
# base type
@dataclass()
class ArrayInfo:
    """
    A class to represent metadata about an array, including its type, dimensions,
    and maximum sizes for each dimension.
    Attributes:
        array_type (type, str): The data type of the array elements.
        array_dimensions (int): The number of dimensions of the array.
        array_max_sizes (List[int]): A list specifying the maximum size for each
            dimension of the array.
        is_base_type (bool): Whether the array_type is assumed to be a float or int, i.e. not a
            custom object.
    """

    array_type: Union[Type[Union[int, float]], str, None]
    array_dimensions: int
    array_max_sizes: List[Optional[int]]
    is_base_type: bool = True

    def __post_init__(self):
        if self.is_base_type and self.array_type not in ARRAY_BASE_TYPES:
            raise ValueError(f"array_type {self.array_type} != (int, float, None)")
        if not (isinstance(self.array_dimensions, int) and self.array_dimensions > 0):
            raise ValueError(f"array_dimension is {self.array_dimensions}: it should be at least 1")
        if not all(
            d_size is None or (isinstance(d_size, int) and d_size > 0)
            for d_size in self.array_max_sizes
        ):
            raise ValueError(f"Invalid 'array_max_sizes': {self.array_max_sizes}")

    def substitute_unbounded_dims(self, max_size: int):
        """
        Substitute the 'None' entries in the array_max_sizes with the provided max_size.
        """
        self.array_max_sizes = [
            max_size if curr_size is None else curr_size for curr_size in self.array_max_sizes
        ]


def array_value_to_type_info(data_value: MutableSequence) -> ArrayInfo:
    """Small helper function to generate the array info from a given value instance."""
    array_type, array_sizes = get_array_type_and_sizes(data_value)
    n_dims = len(array_sizes)
    return ArrayInfo(array_type, n_dims, [None] * n_dims)


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


def convert_string_to_type(value: str, data_type: str) -> Any:
    """
    Convert a value to the provided data type.
    """
    python_type = get_data_type_from_string(data_type)
    interpreted_value = interpret_ecma_script_expr(value)
    assert isinstance(interpreted_value, python_type), f"Failed interpreting {value}"
    return interpreted_value


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


def check_variable_base_type_ok(
    data_value: ValidPlainScxmlTypes,
    expected_data_type: Type[ValidPlainScxmlTypes],
    array_info: Optional[ArrayInfo] = None,
) -> bool:
    """
    Checks if the given data value matches the expected data type (and the opt. array information).

    This function is to be used only on base types and arrays of those.
    :param data_value: The value to be checked, expected to be of a valid SCXML type.
    :param expected_data_type: The expected type of the data value.
    :param array_info: Information about the array, if the data value is expected to one.
    :return: True if the data value matches the expected type, otherwise False.
    """
    valid_types = get_args(ValidPlainScxmlTypes)
    assert (
        expected_data_type in valid_types
    ), f"Invalid expected data type '{expected_data_type}' not in {valid_types}"
    expected_types: Tuple[Type, ...] = (expected_data_type,)
    if isinstance(data_value, valid_types):
        if isinstance(data_value, MutableSequence):
            assert array_info is not None
            # TODO: Small hack to accept integer values in case array type is float
            expected_types = (int,) if array_info.array_type is int else (int, float)

            # We are dealing with a list, use array_info data
            def recurse_on_array(
                data_value: MutableSequence, dims_left: int, base_types: Tuple[Type, ...]
            ) -> bool:
                assert dims_left > 0
                if dims_left == 1:
                    return all(isinstance(entry, base_types) for entry in data_value)
                return all(
                    recurse_on_array(entry, dims_left - 1, base_types) for entry in data_value
                )

            return recurse_on_array(data_value, array_info.array_dimensions, expected_types)
        else:
            return isinstance(data_value, expected_types)
    return False
