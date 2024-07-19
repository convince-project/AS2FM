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
Variables in Jani
"""

from typing import Optional, Union, get_args
from jani_generator.jani_entries import JaniExpression, JaniValue

from as2fm_common.common import ValidTypes


class JaniVariable:
    def __init__(self, v_name: str, v_type: ValidTypes,
                 v_init_value: Optional[Union[JaniExpression, JaniValue]] = None,
                 v_transient: bool = False):
        assert v_init_value is None or isinstance(v_init_value, (JaniExpression, JaniValue)), \
            "Init value should be a JaniExpression or a JaniValue"
        if v_init_value is not None:
            if isinstance(v_init_value, JaniExpression):
                self._init_value = v_init_value
            else:  # In this case it can only be a JaniValue
                self._init_value = JaniExpression(v_init_value)
        assert v_type in get_args(ValidTypes), f"Type {v_type} not supported by Jani"
        self._name = v_name
        self._init_value = v_init_value
        self._type = v_type
        self._transient = v_transient
        # Some Model Checkers really need them to be defined to have a unique initial state
        if self._init_value is None:
            if self._type == int:
                self._init_value = JaniExpression(0)
            elif self._type == bool:
                self._init_value = JaniExpression(False)
            elif self._type == float:
                self._init_value = JaniExpression(0.0)
        if not self._transient and self._type == float:
            print(f"Warning: Variable {self._name} is not transient and has type float."
                  "This is not supported by STORM yet.")

    def name(self):
        return self._name

    def get_type(self):
        return self._type

    def as_dict(self):
        d = {
            "name": self._name,
            "type": JaniVariable.jani_type_to_string(self._type),
            "transient": self._transient
        }
        if self._init_value is not None:
            d["initial-value"] = self._init_value.as_dict()
        return d

    def jani_type_from_string(str_type: str) -> ValidTypes:
        """
        Translate a (Jani) type string to a Python type.
        """
        if str_type == "bool":
            return bool
        elif str_type == "int":
            return int
        elif str_type == "real":
            return float
        else:
            raise ValueError(f"Type {str_type} not supported by Jani")

    def jani_type_to_string(v_type: ValidTypes) -> str:
        """
        Translate a Python type to the name of the type in Jani.

        // Types
        // We cover only the most basic types at the moment.
        // In the remainder of the specification, all requirements like "y must be of type x" are
        // to be interpreted as "type x must be assignable from y's type".
        var BasicType = schema([
        "bool", // assignable from bool
        "int", // numeric; assignable from int and bounded int
        "real" // numeric; assignable from all numeric types
        ]);
        src https://docs.google.com/document/d/\
            1BDQIzPBtscxJFFlDUEPIo8ivKHgXT8_X6hz5quq7jK0/edit
        """
        if v_type == bool:
            return "bool"
        elif v_type == int:
            return "int"
        elif v_type == float:
            return "real"
        else:
            raise ValueError(f"Type {v_type} not supported by Jani")
