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
Assignment in Jani
"""

from typing import Dict

from as2fm.jani_generator.jani_entries import JaniConstant, JaniExpression, generate_jani_expression
from as2fm.jani_generator.jani_entries.jani_convince_expression_expansion import expand_expression


class JaniAssignment:
    """
    Assignment in Jani.
    """

    def __init__(self, assignment_dict: dict):
        """Initialize the assignment from a dictionary"""
        self._var_name = generate_jani_expression(assignment_dict["ref"])
        self._value: JaniExpression = generate_jani_expression(assignment_dict["value"])
        self._index = 0
        if "index" in assignment_dict:
            self._index = assignment_dict["index"]

    def get_target(self):
        """Return the variable storing the expression result."""
        return self._var_name

    def get_expression(self):
        """Return the expression assigned to the target variable (or array entry)"""
        return self._value

    def get_index(self) -> int:
        """Returns the index, i.e. the number that defines the order of execution in Jani."""
        return self._index

    def as_dict(self, constants: Dict[str, JaniConstant]):
        """Transform the assignment to a dictionary"""
        expanded_value = expand_expression(self._value, constants)
        return {
            "ref": self._var_name.as_dict(),
            "value": expanded_value.as_dict(),
            "index": self._index,
        }
