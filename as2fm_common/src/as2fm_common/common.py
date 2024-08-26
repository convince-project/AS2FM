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

from typing import get_args, MutableSequence, Union, Type

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
    if field_type not in get_args(ValidTypes):
        raise ValueError(f"Error: Unsupported data type {field_type}.")
    elif field_type is MutableSequence[int]:
        return "[]"
    elif field_type is MutableSequence[float]:
        return "[]"
    else:
        return str(field_type())
