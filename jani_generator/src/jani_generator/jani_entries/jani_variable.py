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

from typing import MutableSequence, Optional, Union, Type, get_args

from as2fm_common.common import ValidTypes
from jani_generator.jani_entries import JaniExpression, JaniValue


class JaniVariable:
    @staticmethod
    def from_dict(variable_dict: dict) -> "JaniVariable":
        variable_name = variable_dict["name"]
        initial_value = variable_dict.get("initial-value", None)
        variable_type: type = JaniVariable.python_type_from_json(variable_dict["type"])
        if initial_value is None:
            return JaniVariable(variable_name,
                                variable_type,
                                None,
                                variable_dict.get("transient", False))
        if isinstance(initial_value, str):
            # Check if conversion from string to variable_type is possible
            try:
                init_value_cast = variable_type(initial_value)
                return JaniVariable(variable_name,
                                    variable_type,
                                    JaniExpression(init_value_cast),
                                    variable_dict.get("transient", False))
            except ValueError:
                # If no conversion possible, raise an error (variable names are not supported)
                raise ValueError(
                    f"Initial value {initial_value} for variable {variable_name} "
                    f"is not a valid value for type {variable_type}.")
        return JaniVariable(variable_name,
                            variable_type,
                            JaniExpression(initial_value),
                            variable_dict.get("transient", False))

    def __init__(self, v_name: str, v_type: Type[ValidTypes],
                 init_value: Optional[Union[JaniExpression, JaniValue]] = None,
                 v_transient: bool = False):
        assert init_value is None or isinstance(init_value, (JaniExpression, JaniValue)), \
            "Init value should be a JaniExpression or a JaniValue"
        self._name = v_name
        self._type = v_type
        self._transient = v_transient
        self._init_expr: Optional[JaniExpression] = None
        if init_value is not None:
            self._init_expr = JaniExpression(init_value)
        else:
            # Some Model Checkers need a explicit initial value.
            if self._type == int:
                self._init_expr = JaniExpression(0)
            elif self._type == bool:
                self._init_expr = JaniExpression(False)
            elif self._type == float:
                self._init_expr = JaniExpression(0.0)
            else:
                raise ValueError(f"Type {self._type} needs an initial value")
        assert v_type in get_args(ValidTypes), f"Type {v_type} not supported by Jani"
        if not self._transient and self._type in (float, MutableSequence[float]):
            print(f"Warning: Variable {self._name} is not transient and has type float."
                  "This is not supported by STORM.")

    def name(self):
        """Get name."""
        return self._name

    def get_type(self):
        """Get type."""
        return self._type

    def as_dict(self):
        """Return the variable as a dictionary."""
        d = {
            "name": self._name,
            "type": JaniVariable.python_type_to_json(self._type),
            "transient": self._transient
        }
        if self._init_expr is not None:
            d["initial-value"] = self._init_expr.as_dict()
        return d

    @staticmethod
    def python_type_from_json(json_type: Union[str, dict]) -> ValidTypes:
        """
        Translate a (Jani) type string or dict to a Python type.
        """
        if isinstance(json_type, str):
            if json_type == "bool":
                return bool
            elif json_type == "int":
                return int
            elif json_type == "real":
                return float
            else:
                raise ValueError(f"Type {json_type} not supported by Jani")
        elif isinstance(json_type, dict):
            assert "kind" in json_type, "Type dict should contain a 'kind' key"
            if json_type["kind"] == "array":
                assert "base" in json_type, "Array type should contain a 'base' key"
                if json_type["base"] == "int":
                    return MutableSequence[int]
                if json_type["base"] == "real":
                    return MutableSequence[float]
        raise ValueError(f"Type {json_type} not supported by Jani")

    @staticmethod
    def python_type_to_json(v_type: Type[ValidTypes]) -> Union[str, dict]:
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
        elif v_type == MutableSequence[int]:
            return {"kind": "array", "base": "int"}
        elif v_type == MutableSequence[float]:
            return {"kind": "array", "base": "real"}
        else:
            raise ValueError(f"Type {v_type} not supported by Jani")
