# Copyright (c) 2026 - for information on the respective copyright owner
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

from typing import MutableSequence, Union

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

ValidPlainScxmlTypes = Union[bool, int, float, MutableSequence, str]
