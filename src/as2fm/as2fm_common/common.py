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
from typing import List, MutableSequence, Tuple, Type, Union, get_args

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
ValidScxmlTypes = Union[bool, int, float, MutableSequence, str]

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


def get_default_expression_for_type(field_type: Type[ValidJaniTypes]) -> ValidJaniTypes:
    """Generate a default expression for a field type."""
    assert field_type in get_args(ValidJaniTypes), f"Error: Unsupported data type {field_type}."
    if field_type is MutableSequence:
        return []
    else:
        return field_type()


def value_to_type(value: ValidJaniTypes | str) -> Type[ValidJaniTypes]:
    """Convert a value to a type."""
    if isinstance(value, MutableSequence):
        return MutableSequence
    elif isinstance(value, (int, float, bool)):
        return type(value)
    elif isinstance(value, str):  # Strings are interpreted as arrays of integers
        return MutableSequence
    else:
        raise ValueError(f"Unsupported value type {type(value)}.")


def value_to_string_expr(value: ValidJaniTypes) -> str:
    """Convert a value to a string."""
    if isinstance(value, MutableSequence):
        assert is_valid_array(value), f"Found invalid input array {value}."
        # Expect value to be a list, so casting to string is enough.
        return str(value)
    elif isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, (int, float)):
        return str(value)
    else:
        raise ValueError(f"Unsupported value type {type(value)}.")


def is_valid_array(in_sequence: MutableSequence) -> bool:
    """Check that the array is composed by a list of (int, float, list)."""
    assert isinstance(
        in_sequence, list
    ), f"Input values are expected to be lists, found '{in_sequence}' of type {type(in_sequence)}."
    if len(in_sequence) == 0:
        return True
    if isinstance(in_sequence[0], MutableSequence):
        return all(
            isinstance(seq_value, MutableSequence) and is_valid_array(seq_value)
            for seq_value in in_sequence
        )
    return all(isinstance(seq_value, (int, float)) for seq_value in in_sequence)


def get_array_dimensionality_and_type(
    in_sequence: MutableSequence,
) -> Tuple[int, Type[Union[int, float]]]:
    """
    For a given array, return the deepest level it gets.

    E.g.: [[], [[1], []]] has depth 3
    """
    assert is_valid_array(in_sequence)
    if len(in_sequence) == 0:
        # By default, assume an array of integers
        return 1, int
    if not isinstance(in_sequence[0], MutableSequence):
        array_type = int if all(isinstance(seq_value, int) for seq_value in in_sequence) else float
        return 1, array_type
    sub_level_dim: int = 0
    sub_level_type: Type[Union[int, float]] = int
    for seq_value in in_sequence:
        next_dim, next_type = get_array_dimensionality_and_type(seq_value)
        sub_level_dim = max(next_dim, sub_level_dim)
        if next_type is float:
            sub_level_type = float
    return 1 + sub_level_dim, sub_level_type


def string_as_bool(value_str: str) -> bool:
    """
    Special case for boolean conversion for configuration parameters.
    """
    assert value_str in ("true", "false"), f"Invalid bool string: {value_str} != 'true'/'false'"
    return value_str == "true"


def is_array_type(field_type: Type[ValidScxmlTypes]) -> bool:
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
