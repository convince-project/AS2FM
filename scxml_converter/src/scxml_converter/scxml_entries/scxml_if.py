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
Container for conditional execution in a SCXML model. In XML, it has the tag `if`.
"""

from typing import List, Optional, Tuple
from scxml_converter.scxml_entries import ScxmlExecutionBody

from xml.etree import ElementTree as ET


ConditionExecutionBody = Tuple[str, ScxmlExecutionBody]


class ScxmlIf:
    """This class represents SCXML conditionals."""
    def __init__(self,
                 conditional_executions: List[ConditionExecutionBody],
                 else_execution: Optional[ScxmlExecutionBody] = None):
        """
        Class representing a conditional execution in SCXML.

        :param conditional_executions: List of pairs of condition and related execution. At least one pair is required.
        :param else_execution: Execution to be done if no condition is met.
        """
        self._conditional_executions = conditional_executions
        self._else_execution = else_execution

    def check_validity(self) -> bool:
        valid_conditional_executions = len(self._conditional_executions) > 0
        if not valid_conditional_executions:
            print("Error: SCXML if: no conditional executions found.")
        for condition_execution in self._conditional_executions:
            valid_tuple = isinstance(condition_execution, tuple) and len(condition_execution) == 2
            if not valid_tuple:
                print("Error: SCXML if: invalid conditional execution found.")
            condition, execution = condition_execution
            valid_condition = isinstance(condition, str) and len(condition) > 0
            valid_execution = isinstance(execution, ScxmlExecutionBody) and execution.check_validity()
            if not valid_condition:
                print("Error: SCXML if: invalid condition found.")
            if not valid_execution:
                print("Error: SCXML if: invalid execution body found.")
            valid_conditional_executions = valid_tuple and valid_condition and valid_execution
            if not valid_conditional_executions:
                break
        valid_else_execution = \
            self._else_execution is None or \
            (isinstance(self._else_execution, ScxmlExecutionBody) and self._else_execution.check_validity())
        if not valid_else_execution:
            print("Error: SCXML if: invalid else execution body found.")
        return valid_conditional_executions and valid_else_execution

    def as_xml(self) -> ET.Element:
        # Based on example in https://www.w3.org/TR/scxml/#if
        assert self.check_validity(), "SCXML: found invalid if object."
        first_conditional_execution = self._conditional_executions[0]
        xml_if = ET.Element('if', {"cond": first_conditional_execution[0]})
        xml_if.append(first_conditional_execution[1].as_xml())
        for condition, execution in self._conditional_executions[1:]:
            xml_if.append = ET.Element('elseif', {"cond": condition})
            xml_if.append(execution.as_xml())
        if self._else_execution is not None:
            xml_if.append(ET.Element('else'))
            xml_if.append(self._else_execution.as_xml())
        return xml_if
