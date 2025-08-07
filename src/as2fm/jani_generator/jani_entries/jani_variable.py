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

from typing import MutableSequence, Optional, Tuple, Type, Union, get_args

from as2fm.as2fm_common.array_type import ArrayInfo
from as2fm.as2fm_common.common import ValidJaniTypes
from as2fm.jani_generator.jani_entries import JaniExpression, JaniValue
from as2fm.jani_generator.jani_entries.jani_expression import SupportedExp


class JaniVariable:
    @staticmethod
    def from_dict(variable_dict: dict) -> "JaniVariable":
        variable_name = variable_dict["name"]
        initial_value = variable_dict.get("initial-value", None)
        variable_type, array_info = JaniVariable.python_type_from_json(variable_dict["type"])
        if initial_value is None:
            return JaniVariable(
                variable_name,
                variable_type,
                None,
                variable_dict.get("transient", False),
                array_info,
            )
        if isinstance(initial_value, str):
            # Check if conversion from string to variable_type is possible
            try:
                init_value_cast = variable_type(initial_value)
                return JaniVariable(
                    variable_name,
                    variable_type,
                    JaniExpression(init_value_cast),
                    variable_dict.get("transient", False),
                    array_info,
                )
            except ValueError:
                # If no conversion possible, raise an error (variable names are not supported)
                raise ValueError(
                    f"Initial value {initial_value} for variable {variable_name} "
                    f"is not a valid value for type {variable_type}."
                )
        return JaniVariable(
            variable_name,
            variable_type,
            JaniExpression(initial_value),
            variable_dict.get("transient", False),
            array_info,
        )

    def __init__(
        self,
        v_name: str,
        v_type: Type[ValidJaniTypes],
        init_value: Optional[Union[JaniExpression, JaniValue, SupportedExp]] = None,
        v_transient: bool = False,
        array_info: Optional[ArrayInfo] = None,
    ):
        assert init_value is None or isinstance(
            init_value, (JaniExpression, JaniValue, int, float, bool)
        ), (
            f"Expected {v_name} init_value {init_value} to be of type "
            f"(JaniExpression, JaniValue), found {type(init_value)} instead."
        )
        self._name: str = v_name
        self._type: Type[ValidJaniTypes] = v_type
        self._array_info: Optional[ArrayInfo] = None
        self._transient: bool = v_transient
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
                raise ValueError(
                    f"JaniVariable {self._name} of type {self._type} needs an initial value"
                )
        assert v_type in get_args(ValidJaniTypes), f"Type {v_type} not supported by Jani"
        if v_type == MutableSequence:
            assert isinstance(
                array_info, ArrayInfo
            ), f"Variable {v_name} type is an array, but additional info are missing."
            self._array_info = array_info

    def name(self):
        """Get name."""
        return self._name

    def get_type(self) -> Type[ValidJaniTypes]:
        """Get type."""
        return self._type

    def get_array_info(self) -> Optional[ArrayInfo]:
        """Return the array info associated to this JANI variable."""
        return self._array_info

    def get_init_expr(self) -> Optional[JaniExpression]:
        """Get initial expression.  if available. None otherwise."""
        return self._init_expr

    def as_dict(self):
        """Return the variable as a dictionary."""
        d = {
            "name": self._name,
            "type": JaniVariable.python_type_to_json(self._type, self._array_info),
            "transient": self._transient,
        }
        if self._init_expr is not None:
            d["initial-value"] = self._init_expr.as_dict()
        return d

    @staticmethod
    def python_type_from_json(
        json_type: Union[str, dict],
    ) -> Tuple[Type[ValidJaniTypes], Optional[ArrayInfo]]:
        """
        Translate a (Jani) type string or dict to a Python type.
        """
        if isinstance(json_type, str):
            if json_type == "bool":
                return bool, None
            elif json_type == "int":
                return int, None
            elif json_type == "real":
                return float, None
            else:
                raise ValueError(f"Type {json_type} not supported by Jani")
        elif isinstance(json_type, dict):
            n_dimensions = 0
            curr_level = json_type
            while isinstance(curr_level, dict):
                assert "kind" in json_type, "Type dict should contain a 'kind' key"
                if json_type["kind"] == "array":
                    n_dimensions += 1
                    assert "base" in json_type, "Array type should contain a 'base' key"
                    curr_level = json_type["base"]
                else:
                    raise ValueError(f"Type {json_type} not supported by Jani")
            if curr_level == "int":
                return MutableSequence, ArrayInfo(int, n_dimensions, [None] * n_dimensions)
            if curr_level == "real":
                return MutableSequence, ArrayInfo(float, n_dimensions, [None] * n_dimensions)
        raise ValueError(f"Unsupported json type {json_type}")

    @staticmethod
    def python_type_to_json(
        v_type: Type[ValidJaniTypes], v_array_info: Optional[ArrayInfo]
    ) -> Union[str, dict]:
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
        elif v_type == MutableSequence:
            assert isinstance(v_array_info, ArrayInfo)
            target_type = v_array_info.array_type
            assert target_type in (int, float)
            jani_type_str = "int" if target_type is int else "real"
            n_dimensions = v_array_info.array_dimensions
            return JaniVariable.array_to_jany_type(jani_type_str, n_dimensions)
        else:
            raise ValueError(f"Type {v_type} not supported by Jani")

    @staticmethod
    def array_to_jany_type(array_type: str, n_dimensions: int) -> dict:
        """
        Generate the type of a n-dimensional array
        """
        base_content: Union[str, dict] = array_type
        if n_dimensions > 1:
            base_content = JaniVariable.array_to_jany_type(array_type, n_dimensions - 1)
        return {"kind": "array", "base": base_content}
