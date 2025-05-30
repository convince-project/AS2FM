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
Values in Jani
"""

from math import e, pi
from typing import Type, Union


class JaniValue:
    """Class containing Jani Constant Values"""

    def __init__(self, value: Union[int, float, bool, dict]):
        self._value = value

    def is_valid(self) -> bool:
        if isinstance(self._value, dict):
            if "constant" in self._value:
                assert self._value["constant"] in (
                    "e",
                    "π",
                ), f"Unknown constant value {self._value['constant']}. Only 'e' and 'π' supported."
                return True
        return isinstance(self._value, (int, float, bool))

    def value(self) -> Union[int, float, bool]:
        assert self.is_valid(), "The expression cannot be evaluated to a constant value"
        if isinstance(self._value, dict):
            constant_id = self._value["constant"]
            if constant_id == "e":
                return e
            if constant_id == "π":
                return pi
        return self._value

    def _get_py_type(self) -> Type[Union[int, float, bool]]:
        """
        Get the python type of the entry stored in the JaniValue.

        Constants are mapped to floats.
        """
        assert self.is_valid(), "Invalid JaniValue instance"
        if isinstance(self._value, dict):
            return float
        return type(self._value)

    def as_dict(self) -> Union[dict, int, float, bool]:
        # Note: this might be a value or a dictionary
        assert self.is_valid(), "Invalid JaniValue instance"
        return self._value
