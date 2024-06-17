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
Definition of SCXML Tags that can be part of executable content
"""

from typing import List, Optional, Union, Tuple, get_args
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import ScxmlParam

# Use delayed type evaluation: https://peps.python.org/pep-0484/#forward-references
ScxmlExecutableEntries = Union['ScxmlAssign', 'ScxmlIf', 'ScxmlSend']
ScxmlExecutionBody = List[ScxmlExecutableEntries]
ConditionalExecutionBody = Tuple[str, ScxmlExecutionBody]


class ScxmlIf:
    """This class represents SCXML conditionals."""
    def __init__(self,
                 conditional_executions: List[ConditionalExecutionBody],
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


class ScxmlSend:
    """This class represents a send action."""
    def __init__(self, event: str, target: str, params: Optional[List[ScxmlParam]] = None):
        # TODO: Right now, it seems only a single target is allowed in the SCXML standard. Needs clarification
        self._event = event
        self._target = target
        self._params = params

    def check_validity(self) -> bool:
        valid_event = isinstance(self._event, str) and len(self._event) > 0
        valid_target = isinstance(self._target, str) and len(self._target) > 0
        valid_params = True
        if self._params is not None:
            for param in self._params:
                valid_param = isinstance(param, ScxmlParam) and param.check_validity()
                valid_params = valid_params and valid_param
        if not valid_event:
            print("Error: SCXML send: event is not valid.")
        if not valid_target:
            print("Error: SCXML send: target is not valid.")
        if not valid_params:
            print("Error: SCXML send: one or more param entries are not valid.")
        return valid_event and valid_target and valid_params

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid send object."
        xml_send = ET.Element('send', {"event": self._event, "target": self._target})
        if self._params is not None:
            for param in self._params:
                xml_send.append(param.as_xml())
        return xml_send


class ScxmlAssign:
    """This class represents a variable assignment."""
    def __init__(self, name: str, expr: str):
        self.name = name
        self.expr = expr

    def check_validity(self) -> bool:
        # TODO: Check that the location to assign exists in the data-model
        valid_name = isinstance(self.name, str) and len(self.name) > 0
        valid_expr = isinstance(self.expr, str) and len(self.expr) > 0
        if not valid_name:
            print("Error: SCXML assign: name is not valid.")
        if not valid_expr:
            print("Error: SCXML assign: expr is not valid.")
        return valid_name and valid_expr

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid assign object."
        return ET.Element('assign', {"location": self.name, "expr": self.expr})


# Get the resolved types from the forward references in ScxmlExecutableEntries
_ResolvedScxmlExecutableEntries = \
    tuple(entry._evaluate(globals(), locals(), frozenset()) for entry in get_args(ScxmlExecutableEntries))


print(_ResolvedScxmlExecutableEntries)


def valid_execution_body(execution_body: ScxmlExecutionBody) -> bool:
    """
    Check if an execution body is valid.

    :param execution_body: The execution body to check
    :return: True if the execution body is valid, False otherwise
    """
    valid = isinstance(execution_body, list)
    if not valid:
        print("Error: SCXML execution body: invalid type found: expected a list.")
    for entry in execution_body:
        if not isinstance(entry, _ResolvedScxmlExecutableEntries):
            valid = False
            print(f"Error: SCXML execution body: entry type {type(entry)} not in valid set "
                  f" {_ResolvedScxmlExecutableEntries}.")
            break
        if not entry.check_validity():
            valid = False
            print("Error: SCXML execution body: invalid entry content found.")
            break
    return valid
