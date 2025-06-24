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

"""
Common functionalities used throughout the toolchain.
"""

import re
from typing import List, MutableSequence, Optional, Tuple, Type, Union, get_args

from lxml.etree import _Comment as XmlComment
from lxml.etree import _Element as XmlElement

# Set of basic types that are supported by the Jani language.
# Basic types (from Jani docs):
# Types
# We cover only the most basic types at the moment.
# In the remainder of the specification, all requirements like "y must be of type x" are to be
# interpreted as "type x must be assignable from y's type".
# var BasicType = schema([
# "bool", // assignable from bool
# "int", // numeric; assignable from int and bounded int
# "real" // numeric; assignable from all numeric types
# ]);
# src https://docs.google.com/document/d/\
#     1BDQIzPBtscxJFFlDUEPIo8ivKHgXT8_X6hz5quq7jK0/edit
# Additionally, we support the array types from the array extension.
ValidJaniTypes = Union[bool, int, float, MutableSequence]

# When interpreting ECMAScript, we support either MutableSequence that are arrays in ECMAScript or
# Strings.
SupportedECMAScriptSequences = (MutableSequence, str)
ValidPlainScxmlTypes = Union[bool, int, float, MutableSequence, str]

# Small number used for float comparison.
EPSILON = 1e-3


def remove_namespace(tag: str) -> str:
    """
    If a tag has a namespace, remove it.

    e.g. {http://www.w3.org/2005/07/scxml}transition -> transition

    :param tag: The tag to remove the namespace from.
    :return: The tag without the namespace.
    """
    if "}" in tag:
        tag_wo_ns = tag.split("}")[-1]
    else:
        tag_wo_ns = tag
    return tag_wo_ns


def is_comment(element: XmlElement) -> bool:
    """
    Check if an element is a comment.

    :param element: The element to check.
    :return: True if the element is a comment, False otherwise.
    """
    return isinstance(element, XmlComment) or "function Comment" in str(element)


def get_default_expression_for_type(field_type: Type[ValidPlainScxmlTypes]) -> ValidPlainScxmlTypes:
    """Generate a default expression for a field type."""
    assert field_type in get_args(
        ValidPlainScxmlTypes
    ), f"Error: Unsupported SCXML data type {field_type}."
    if field_type is MutableSequence:
        return []
    if field_type is str:
        return "''"
    else:
        return field_type()


def value_to_type(value: ValidPlainScxmlTypes) -> Type[ValidJaniTypes]:
    """Return the type of a python object (to be a jani value)."""
    if isinstance(value, MutableSequence):
        return MutableSequence
    elif isinstance(value, (int, float, bool)):
        return type(value)
    elif isinstance(value, str):  # Strings are interpreted as arrays of integers
        return MutableSequence
    else:
        raise ValueError(f"Unsupported value type {type(value)}.")


def value_to_string_expr(value: ValidPlainScxmlTypes) -> str:
    """Return a python object (to be a jani value) as a string."""
    if isinstance(value, MutableSequence):
        assert is_valid_array(value), f"Found invalid input array {value}."
        # Expect value to be a list, so casting to string is enough.
        return str(value)
    elif isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        return value
    else:
        raise ValueError(f"Unsupported value type {type(value)}.")


def is_valid_array(in_sequence: Union[MutableSequence, str]) -> bool:
    """
    Check that the array is composed by a list of (int, float, list).

    This does *not* check that all sub-lists have the same depth (e.g. [[1], [[1,2,3]]]).
    """
    assert isinstance(
        in_sequence, (list, str)
    ), f"Input values are expected to be lists, found '{in_sequence}' of type {type(in_sequence)}."
    if len(in_sequence) == 0:
        return True
    if isinstance(in_sequence, str):
        return True
    if isinstance(in_sequence[0], MutableSequence):
        return all(
            isinstance(seq_value, MutableSequence) and is_valid_array(seq_value)
            for seq_value in in_sequence
        )
    # base case: simple array of base types
    return all(isinstance(seq_value, (int, float)) for seq_value in in_sequence)


def get_array_type_and_sizes(
    in_sequence: Union[MutableSequence, str],
) -> Tuple[Optional[Type[Union[int, float]]], MutableSequence]:
    """
    Extract the type and size(s) of the provided multi-dimensional array.

    Exemplary output for 3-dimensional array `[ [], [ [1], [1, 2], [] ] ]` is:
    `tuple(int, [2, [0, 3], [[], [1, 2, 0]]]])`.
    The sizes contain one entry per dimension (here 3).
    """
    if not is_valid_array(in_sequence):
        raise ValueError(f"Invalid sub-array found: {in_sequence}")
    if isinstance(in_sequence, str):
        return get_array_type_and_sizes(convert_string_to_int_array(in_sequence))
    if len(in_sequence) == 0:
        return None, [0]
    if not isinstance(in_sequence[0], MutableSequence):
        # 1-D array -> type is int or float
        ret_type: Optional[Type[Union[int, float]]] = float
        if all(isinstance(seq_entry, int) for seq_entry in in_sequence):
            # if at least one entry is float, all will be float
            ret_type = int
        return ret_type, [len(in_sequence)]
    # Recursive part
    curr_type: Optional[Type[Union[int, float]]] = None
    base_size = len(in_sequence)  # first dimension
    child_sizes = []  # on this first dimension
    children_max_depth = 0  # keep track of how deep we go
    for seq_entry in in_sequence:
        single_type, single_sizes = get_array_type_and_sizes(seq_entry)
        child_depth = len(single_sizes)
        if curr_type is None:
            if single_type is not None and child_depth < children_max_depth:
                raise ValueError("Unbalanced list found.")
            # We do not know *yet* the max depth of the children.
            children_max_depth = max(children_max_depth, child_depth)
            curr_type = single_type
        else:
            # We have to make sure the max depth doesn't grow
            if single_type is None:
                if child_depth > children_max_depth:
                    raise ValueError("Unbalanced list found.")
            else:
                if child_depth != children_max_depth:
                    raise ValueError("Unbalanced list found.")
                if curr_type == int:
                    curr_type = single_type
        child_sizes.append(single_sizes)
    # At this point, we need to merge the sizes from the child_sizes to create the desired
    # output format. (List with one entry per dimension)
    max_depth = children_max_depth + 1
    processed_sizes: List[Union[int, List]] = []
    for level in range(max_depth):
        if level == 0:
            processed_sizes.append(base_size)
            continue
        processed_sizes.append([])
        for curr_size_entry in child_sizes:
            if len(curr_size_entry) < level:
                # there was an empty list at the previous depth level
                processed_sizes[level].append([])
            else:
                assert isinstance(
                    processed_sizes[level], list
                ), f"Unexpected a list of sizes at {level=}."
                processed_sizes[level].append(curr_size_entry[level - 1])
    return curr_type, processed_sizes


def get_padded_array(
    array_to_pad: List[Union[int, float, List]],
    size_per_level: List[int],
    array_type: Type[Union[int, float]],
) -> List[Union[int, float, List]]:
    """Given a N-Dimensional list, add padding for each level, depending on the provided sizes."""
    padding_size = size_per_level[0] - len(array_to_pad)
    if padding_size < 0:
        raise ValueError(
            f"Expected level's size '{size_per_level[0]}' is smaller than ",
            f"the current instance length '{len(array_to_pad)}'.",
        )
    if len(size_per_level) == 1:
        # We are at the lowest level -> only floats and integers allowed
        if any(isinstance(entry, list) for entry in array_to_pad):
            raise ValueError("The array to pad is deeper than expected.")
        array_to_pad.extend([array_type(0)] * padding_size)
    else:
        # There are lower levels -> Here we expect only empty lists
        if not all(isinstance(entry, list) for entry in array_to_pad):
            raise ValueError("Found non-array entries at intermediate depth.")
        array_to_pad.extend([[]] * padding_size)
        for idx in range(size_per_level[0]):
            array_to_pad[idx] = get_padded_array(array_to_pad[idx], size_per_level[1:], array_type)
    return array_to_pad


def string_as_bool(value_str: str) -> bool:
    """
    Special case for boolean conversion for configuration parameters.
    """
    assert value_str in ("true", "false"), f"Invalid bool string: {value_str} != 'true'/'false'"
    return value_str == "true"


def is_array_type(field_type: Type[ValidPlainScxmlTypes]) -> bool:
    """Check if the field type is an array type."""
    return field_type is MutableSequence


def is_valid_variable_name(var_name: str) -> bool:
    """
    Check if a string can represent a variable name in JANI and SCXML.

    This differs from the string.isidentifier() python function, since we allow more possibilities:
    * A variable name must start with a character or an underscore;
    * Can continue with any number of alphanumerical values plus (. - _);
    * Must finish with an alphanumerical value.
    Alternatively, a variable name can be a single character.
    """
    return re.match(r"^[a-zA-Z_][a-zA-Z0-9._-]*[a-zA-Z0-9]$|^[a-zA-Z]$", var_name) is not None


def convert_string_to_int_array(value: str) -> List[int]:
    """
    Convert a string to a list of integers.
    """
    return [int(x) for x in value.encode()]
