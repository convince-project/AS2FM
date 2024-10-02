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

from array import array
from typing import MutableSequence, Type, Union, get_args, get_origin

"""
Set of basic types that are supported by the Jani language.

Basic types (from Jani docs):
Types
We cover only the most basic types at the moment.
In the remainder of the specification, all requirements like "y must be of type x" are to be
interpreted as "type x must be assignable from y's type".
var BasicType = schema([
"bool", // assignable from bool
"int", // numeric; assignable from int and bounded int
"real" // numeric; assignable from all numeric types
]);
src https://docs.google.com/document/d/\
    1BDQIzPBtscxJFFlDUEPIo8ivKHgXT8_X6hz5quq7jK0/edit

Additionally, we support the array types from the array extension.
"""
ValidTypes = Union[bool, int, float, MutableSequence[int], MutableSequence[float]]


def remove_namespace(tag: str) -> str:
    """
    If a tag has a namespace, remove it.

    e.g. {http://www.w3.org/2005/07/scxml}transition -> transition

    :param tag: The tag to remove the namespace from.
    :return: The tag without the namespace.
    """
    if '}' in tag:
        tag_wo_ns = tag.split('}')[-1]
    else:
        tag_wo_ns = tag
    return tag_wo_ns


def get_default_expression_for_type(field_type: Type[ValidTypes]) -> ValidTypes:
    """Generate a default expression for a field type."""
    assert field_type in get_args(ValidTypes), f"Error: Unsupported data type {field_type}."
    if field_type is MutableSequence[int]:
        return array('i')
    elif field_type is MutableSequence[float]:
        return array('d')
    else:
        return field_type()


def value_to_type(value: ValidTypes) -> Type[ValidTypes]:
    """Convert a value to a type."""
    if isinstance(value, array):
        if value.typecode == 'i':
            return MutableSequence[int]
        elif value.typecode == 'd':
            return MutableSequence[float]
        else:
            raise ValueError(f"Type of array '{value.typecode}' not supported.")
    elif isinstance(value, (int, float, bool)):
        return type(value)
    else:
        raise ValueError(f"Unsupported value type {type(value)}.")


def value_to_string(value: ValidTypes) -> str:
    """Convert a value to a string."""
    if isinstance(value, MutableSequence):
        # Expect value to be an array
        return f'[{",".join(str(v) for v in value)}]'
    elif isinstance(value, bool):
        return str(value).lower()
    elif isinstance(value, (int, float)):
        return str(value)
    else:
        raise ValueError(f"Unsupported value type {type(value)}.")


def string_to_value(value_str: str, value_type: Type[ValidTypes]) -> ValidTypes:
    """Convert a string to a value of the desired type."""
    value_str = value_str.strip()
    assert isinstance(value_str, str), \
        f"Error: provided value is of type {type(value_str)}, expected a string."
    assert len(value_str) > 0, "Error: provided value is an empty string, cannot convert."
    is_array_value = value_str.startswith('[') and value_str.endswith(']')
    if not is_array_value:
        assert value_type in (bool, int, float), \
            f"Error: the value {value_str} shall be converted to a base type."
        return value_type(value_str)
    else:
        str_entries = value_str.strip('[]').split(',')
        if str_entries == ['']:
            str_entries = []
        if value_type is MutableSequence[int]:
            return array('i', [int(v) for v in str_entries])
        elif value_type is MutableSequence[float]:
            return array('d', [float(v) for v in str_entries])
        else:
            raise ValueError(f"Unsupported value type {value_type}.")


def check_value_type_compatible(value: ValidTypes, field_type: Type[ValidTypes]) -> bool:
    """Check if the value is compatible with the field type."""
    if field_type is float:
        return isinstance(value, (int, float))
    return isinstance(value, field_type)


def is_array_type(field_type: Type[ValidTypes]) -> bool:
    """Check if the field type is an array type."""
    return get_origin(field_type) == get_origin(MutableSequence)
