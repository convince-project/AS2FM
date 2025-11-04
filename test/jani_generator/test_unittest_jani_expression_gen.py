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

import pytest

from moco.moco_common.array_type import ArrayInfo
from moco.roaml_generator.jani_entries.jani_expression_generator import (
    array_create_operator,
    array_value_operator,
)


def __validate_array_create_operator(op_dict: dict, array_info: ArrayInfo):
    """Check that the 'ac' operator contains the expected info."""
    assert (
        array_info.array_dimensions > 0
        and len(array_info.array_max_sizes) == array_info.array_dimensions
    ), "Make sure the provided array_info instance is valid."
    assert op_dict["op"] == "ac", f"Unexpected operator identifier {op_dict['op']}."
    assert (
        isinstance(op_dict["var"], str) and len(op_dict["var"]) > 0
    ), f"Unexpected iterator variable name: {op_dict['var']}"
    assert op_dict["length"] == array_info.array_max_sizes[0], "Unexpected content of ac length."
    if len(array_info.array_max_sizes) > 1:
        # Multi-dimensional array, recurse
        __validate_array_create_operator(
            op_dict["exp"],
            ArrayInfo(
                array_info.array_type,
                array_info.array_dimensions - 1,
                array_info.array_max_sizes[1:],
            ),
        )


def __validate_array_value_operator(op_dict: dict, input_array: list):
    """Check that the content of an array_value operator matches the expectations."""
    assert isinstance(input_array, list)
    assert op_dict["op"] == "av", f"Unexpected operator type {op_dict['op']}"
    assert isinstance(op_dict["elements"], list), "Unexpected values in the 'av' elements."
    assert len(op_dict["elements"]) == len(input_array), "Unexpected elements length."
    if len(input_array) > 0 and isinstance(input_array[0], list):
        for op_entry, list_entry in zip(op_dict["elements"], input_array):
            __validate_array_value_operator(op_entry, list_entry)
    else:
        for op_entry, list_entry in zip(op_dict["elements"], input_array):
            assert op_entry == list_entry, (
                "The content of the input and generated array do not match: ",
                f"{op_dict['elements']} != {input_array}",
            )


def test_array_create_operator():
    # Test creating an array with valid inputs
    array_info = ArrayInfo(int, 1, [5])
    result = array_create_operator(array_info)
    __validate_array_create_operator(result.as_dict(), array_info)

    # Test creating an array with size 0 (no array_info can be defined)
    with pytest.raises(ValueError):
        array_info = ArrayInfo(int, 1, [0])
        # result = array_create_operator(array_info)

    # Test creating an array with negative size (no array_info can be defined)
    with pytest.raises(ValueError):
        array_info = ArrayInfo(int, 1, [-1])
        # result = array_create_operator(array_info)

    # Test creating an array with size None
    with pytest.raises(AssertionError):
        array_info = ArrayInfo(int, 1, [None])
        result = array_create_operator(array_info)

    # Test multi-dimensional array
    array_info = ArrayInfo(int, 3, [5, 4, 3])
    result = array_create_operator(array_info)
    __validate_array_create_operator(result.as_dict(), array_info)


def test_array_value_operator():
    array = [10, 20, 30]
    result = array_value_operator(array)
    __validate_array_value_operator(result.as_dict(), array)

    array = []
    result = array_value_operator(array)
    __validate_array_value_operator(result.as_dict(), array)

    array = [[1, 2, 3], [5], []]
    result = array_value_operator(array)
    __validate_array_value_operator(result.as_dict(), array)

    array = [[], [[1], [2, 3]], [[4, 5], []]]
    result = array_value_operator(array)
    __validate_array_value_operator(result.as_dict(), array)
