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

"""Collection of various utilities for scxml entries."""

from typing import Type

from scxml_converter.scxml_entries import ScxmlBase

# TODO: add lower and upper bounds depending on the n. of bits used.
# TODO: add support to uint
SCXML_DATA_STR_TO_TYPE = {
    "bool": bool,
    "float32": float,
    "float64": float,
    "int8": int,
    "int16": int,
    "int32": int,
    "int64": int
}


def is_non_empty_string(scxml_type: Type[ScxmlBase], arg_name: str, arg_value: str) -> bool:
    """Check if a string is non-empty."""
    valid_str = isinstance(arg_value, str) and len(arg_value) > 0
    if not valid_str:
        print(f"Error: SCXML conversion of {scxml_type.get_tag_name()}: "
              f"Expected non-empty argument {arg_name}.")


def get_default_expression_for_type(field_type: str) -> str:
    """Generate a default expression for a field type."""
    return str(SCXML_DATA_STR_TO_TYPE[field_type]())
