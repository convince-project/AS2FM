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
# limitations under the License.from typing import List

"""A constant value expression."""

from typing import Optional, Type, Union, get_args

from moco.roaml_generator.jani_entries import JaniExpression

ValidTypes = Union[bool, int, float]


class JaniConstant:
    @staticmethod
    def from_dict(constant_dict: dict) -> "JaniConstant":
        constant_name = constant_dict["name"]
        constant_type = JaniConstant.jani_type_from_string(constant_dict["type"])
        constant_value = constant_dict.get("value", None)
        if constant_value is None:
            return JaniConstant(constant_name, constant_type, None)
        if isinstance(constant_value, str):
            # Check if conversion from string to constant_type is possible
            try:
                const_value_cast = constant_type(constant_value)
                return JaniConstant(constant_name, constant_type, JaniExpression(const_value_cast))
            except ValueError:
                # If no conversion possible, raise an error (constant names are not supported)
                raise ValueError(
                    f"Value {constant_value} for constant {constant_name} "
                    f"is not a valid value for type {constant_type}."
                )
        return JaniConstant(constant_name, constant_type, JaniExpression(constant_value))

    def __init__(self, c_name: str, c_type: Type, c_value: Optional[JaniExpression]):
        assert isinstance(c_value, JaniExpression), "Value should be a JaniExpression"
        assert c_type in get_args(ValidTypes), f"Type {c_type} not supported by Jani"
        self._name = c_name
        self._type = c_type
        self._value = c_value

    def name(self) -> str:
        return self._name

    def value(self) -> Optional[ValidTypes]:
        if self._value is None:
            return None
        jani_value = self._value.value
        assert jani_value.is_valid(), "The expression can't be evaluated to a constant value"
        return jani_value.value()

    @staticmethod
    def jani_type_from_string(str_type: str) -> Type[ValidTypes]:
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

    # TODO: Move this to a util function file
    @staticmethod
    def jani_type_to_string(c_type: Type[ValidTypes]) -> str:
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
        assert isinstance(c_type, type), f"Type {c_type} is not a type"
        if c_type == bool:
            return "bool"
        if c_type == int:
            return "int"
        if c_type == float:
            return "real"
        raise ValueError(f"Type {c_type} not supported by Jani")

    def as_dict(self):
        const_dict = {"name": self._name, "type": JaniConstant.jani_type_to_string(self._type)}
        if self._value is not None:
            const_dict["value"] = self._value.as_dict()
        return const_dict
