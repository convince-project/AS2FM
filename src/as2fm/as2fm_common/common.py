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
from typing import MutableSequence, Type, get_args

from lxml.etree import _Comment as XmlComment
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.array_type import is_valid_array
from as2fm.as2fm_common.types import ValidJaniTypes, ValidPlainScxmlTypes

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


def value_to_type(value: ValidPlainScxmlTypes) -> Type[ValidJaniTypes]:
    """Return the type of a python object (to be a jani value)."""
    if isinstance(value, MutableSequence):
        return MutableSequence
    elif isinstance(value, (int, float, bool)):
        return type(value)
    else:
        raise ValueError(f"Unsupported value type {type(value)} for {value}.")


def string_as_bool(value_str: str) -> bool:
    """
    Special case for boolean conversion for configuration parameters.
    """
    assert value_str in ("true", "false"), f"Invalid bool string: {value_str} != 'true'/'false'"
    return value_str == "true"


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


def get_default_expression_for_type(field_type: Type[ValidPlainScxmlTypes]) -> ValidPlainScxmlTypes:
    """Generate a default expression for a field type."""
    assert field_type in get_args(
        ValidPlainScxmlTypes
    ), f"Error: Unsupported SCXML data type {field_type}."
    if field_type is MutableSequence:
        return []
    if field_type is str:
        return ""
    else:
        return field_type()


def value_to_string_expr(value: ValidPlainScxmlTypes) -> str:
    """Takes a python object and returns it as a (SCXML compatible) string."""
    if isinstance(value, MutableSequence):
        assert is_valid_array(value), f"Found invalid input array {value}."
        # Expect value to be a list, so casting to string is enough.
        return str(value)
    elif isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, (int, float)):
        return str(value)
    elif isinstance(value, str):
        return f"'{value}'"
    else:
        raise ValueError(f"Unsupported value type {type(value)}.")
