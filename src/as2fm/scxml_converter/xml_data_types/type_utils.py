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

from as2fm.as2fm_common.common import ValidScxmlTypes
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
    "string": str,
}


@dataclass()
class ArrayInfo:
    """
    A class to represent metadata about an array, including its type, dimensions,
    and maximum sizes for each dimension.
    Attributes:
        array_type (str): The data type string of the array elements.
        array_dimensions (int): The number of dimensions of the array.
        array_max_sizes (List[int]): A list specifying the maximum size for each
            dimension of the array.
        is_base_type (bool): Whether we expect the type string to relate to a float/int or not.
    """

    array_type: Union[str]
    array_dimensions: int
    array_max_sizes: List[Optional[int]]
    is_base_type: bool = True

    def __post_init__(self):
        if self.is_base_type:
            evaluated_type = SCXML_DATA_STR_TO_TYPE[self.array_type]
            assert evaluated_type in (int, float), f"array_type '{self.array_type}' != (int, float)"
        assert (
            isinstance(self.array_dimensions, int) and self.array_dimensions > 0
        ), f"array_dimension is {self.array_dimensions}, but should be at least 1"
        assert all(
            d_size is None or (isinstance(d_size, int) and d_size > 0)
            for d_size in self.array_max_sizes
        ), f"Invalid 'array_max_sizes': {self.array_max_sizes}"

    def substitute_unbounded_dims(self, max_size: int):
        """
        Substitute the 'None' entries in the array_max_sizes with the provided max_size.
        """
        self.array_max_sizes = [
            max_size if curr_size is None else curr_size for curr_size in self.array_max_sizes
        ]


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


def get_array_info(data_type: str, expect_base_type: bool = True) -> ArrayInfo:
    """
    Given an array type string, return the related ArrayInfo.

    E.g. float[][5][10] will return n_dims=3 and dim_bounds=(None, 5, 10).

    :param data_type: A string representing the array type. Must be a valid array type string.
    :param expect_base_type: A flag indicating whether to expect a base type in the type string.
    :return: An ArrayInfo object containing all required info.
    """
    assert is_type_string_array(data_type), f"Error: SCXML data: '{data_type}' is not an array."
    array_type_str = get_type_string_of_array(data_type)
    dim_matches = re.findall(r"(\[([0-9]*)\])", data_type)
    n_dims = len(dim_matches)
    dim_bounds = [None if dim_str == "" else int(dim_str) for _, dim_str in dim_matches]
    return ArrayInfo(array_type_str, n_dims, dim_bounds, expect_base_type)


def check_variable_base_type_ok(
    data_value: ValidScxmlTypes,
    expected_data_type: Type[ValidScxmlTypes],
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
    valid_types = get_args(ValidScxmlTypes)
    assert (
        expected_data_type in valid_types
    ), f"Invalid expected data type '{expected_data_type}' not in {valid_types}"
    expected_types: Tuple[Type, ...] = (expected_data_type,)
    if isinstance(data_value, valid_types):
        if isinstance(data_value, MutableSequence):
            assert array_info is not None
            # Small hack to accept integer values in case type is float
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
            # Small hack to accept integer values in case type is float
            if expected_data_type is float:
                expected_types = (int, float)
            return isinstance(data_value, expected_types)
    return False
