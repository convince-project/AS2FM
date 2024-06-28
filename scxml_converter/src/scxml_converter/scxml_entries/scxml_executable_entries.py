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
ScxmlExecutableEntry = Union['ScxmlAssign', 'ScxmlIf', 'ScxmlSend']
ScxmlExecutionBody = List[ScxmlExecutableEntry]
ConditionalExecutionBody = Tuple[str, ScxmlExecutionBody]


class ScxmlIf:
    """This class represents SCXML conditionals."""

    def __init__(self,
                 conditional_executions: List[ConditionalExecutionBody],
                 else_execution: Optional[ScxmlExecutionBody] = None):
        """
        Class representing a conditional execution in SCXML.

        :param conditional_executions: List of (condition - exec. body) pairs. Min n. pairs is one.
        :param else_execution: Execution to be done if no condition is met.
        """
        self._conditional_executions = conditional_executions
        self._else_execution = else_execution

    def get_tag_name() -> str:
        return "if"

    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlIf":
        """Create a ScxmlIf object from an XML tree."""
        assert xml_tree.tag == ScxmlIf.get_tag_name(), \
            f"Error: SCXML if: XML tag name is not {ScxmlIf.get_tag_name()}."
        conditions: List[str] = []
        exec_bodies: List[ScxmlExecutionBody] = []
        conditions.append(xml_tree.attrib["cond"])
        current_body: ScxmlExecutionBody = []
        for child in xml_tree:
            if child.tag == "elseif":
                conditions.append(child.attrib["cond"])
                exec_bodies.append(current_body)
                current_body = []
            elif child.tag == "else":
                exec_bodies.append(current_body)
                current_body = []
            else:
                current_body.append(execution_entry_from_xml(child))
        assert len(conditions) == len(exec_bodies), \
            "Error: SCXML if: number of conditions and bodies do not match."
        if len(current_body) == 0:
            current_body = None
        return ScxmlIf(list(zip(conditions, exec_bodies)), current_body)

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
            valid_execution = isinstance(
                execution, ScxmlExecutionBody) and execution.check_validity()
            if not valid_condition:
                print("Error: SCXML if: invalid condition found.")
            if not valid_execution:
                print("Error: SCXML if: invalid execution body found.")
            valid_conditional_executions = valid_tuple and valid_condition and valid_execution
            if not valid_conditional_executions:
                break
        valid_else_execution = \
            self._else_execution is None or \
            (isinstance(self._else_execution, ScxmlExecutionBody)
             and self._else_execution.check_validity())
        if not valid_else_execution:
            print("Error: SCXML if: invalid else execution body found.")
        return valid_conditional_executions and valid_else_execution

    def as_xml(self) -> ET.Element:
        # Based on example in https://www.w3.org/TR/scxml/#if
        assert self.check_validity(), "SCXML: found invalid if object."
        first_conditional_execution = self._conditional_executions[0]
        xml_if = ET.Element(ScxmlIf.get_tag_name(), {"cond": first_conditional_execution[0]})
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

    def __init__(self, event: str, params: Optional[List[ScxmlParam]] = None):
        self._event = event
        self._params = params

    def get_tag_name() -> str:
        return "send"

    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlSend":
        """Create a ScxmlSend object from an XML tree."""
        assert xml_tree.tag == ScxmlSend.get_tag_name(), \
            f"Error: SCXML send: XML tag name is not {ScxmlSend.get_tag_name()}."
        event = xml_tree.attrib["event"]
        params = []
        for param_xml in xml_tree:
            params.append(ScxmlParam.from_xml_tree(param_xml))
        if len(params) == 0:
            params = None
        return ScxmlSend(event, params)

    def check_validity(self) -> bool:
        valid_event = isinstance(self._event, str) and len(self._event) > 0
        valid_params = True
        if self._params is not None:
            for param in self._params:
                valid_param = isinstance(param, ScxmlParam) and param.check_validity()
                valid_params = valid_params and valid_param
        if not valid_event:
            print("Error: SCXML send: event is not valid.")
        if not valid_params:
            print("Error: SCXML send: one or more param entries are not valid.")
        return valid_event and valid_params

    def append_param(self, param: ScxmlParam) -> None:
        assert isinstance(param, ScxmlParam), "Error: SCXML send: invalid param."
        if self._params is None:
            self._params = []
        self._params.append(param)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid send object."
        xml_send = ET.Element(ScxmlSend.get_tag_name(), {"event": self._event})
        if self._params is not None:
            for param in self._params:
                xml_send.append(param.as_xml())
        return xml_send


class ScxmlAssign:
    """This class represents a variable assignment."""

    def __init__(self, name: str, expr: str):
        self.name = name
        self.expr = expr

    def get_tag_name() -> str:
        return "assign"

    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlAssign":
        """Create a ScxmlAssign object from an XML tree."""
        assert xml_tree.tag == ScxmlAssign.get_tag_name(), \
            f"Error: SCXML assign: XML tag name is not {ScxmlAssign.get_tag_name()}."
        name = xml_tree.attrib.get("location")
        assert name is not None and len(name) > 0, "Error: SCXML assign: name is not valid."
        expr = xml_tree.attrib.get("expr")
        assert expr is not None and len(expr) > 0, "Error: SCXML assign: expr is not valid."
        return ScxmlAssign(name, expr)

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
        return ET.Element(ScxmlAssign.get_tag_name(), {"location": self.name, "expr": self.expr})


# Get the resolved types from the forward references in ScxmlExecutableEntry
_ResolvedScxmlExecutableEntry = \
    tuple(entry._evaluate(globals(), locals(), frozenset())
          for entry in get_args(ScxmlExecutableEntry))


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
        if not isinstance(entry, _ResolvedScxmlExecutableEntry):
            valid = False
            print(f"Error: SCXML execution body: entry type {type(entry)} not in valid set "
                  f" {_ResolvedScxmlExecutableEntry}.")
            break
        if not entry.check_validity():
            valid = False
            print("Error: SCXML execution body: invalid entry content found.")
            break
    return valid


def execution_entry_from_xml(xml_tree: ET.Element) -> ScxmlExecutableEntry:
    """
    Create an execution entry from an XML tree.

    :param xml_tree: The XML tree to create the execution entry from
    :return: The execution entry
    """
    # TODO: This is pretty bad, need to re-check how to break the circle
    from .scxml_ros_entries import RosTopicPublish
    # Switch based on the tag name
    exec_tag = xml_tree.tag
    if exec_tag == ScxmlIf.get_tag_name():
        return ScxmlIf.from_xml_tree(xml_tree)
    elif exec_tag == ScxmlAssign.get_tag_name():
        return ScxmlAssign.from_xml_tree(xml_tree)
    elif exec_tag == ScxmlSend.get_tag_name():
        return ScxmlSend.from_xml_tree(xml_tree)
    elif exec_tag == RosTopicPublish.get_tag_name():
        return RosTopicPublish.from_xml_tree(xml_tree)
    else:
        raise ValueError(f"Error: SCXML conversion: tag {exec_tag} isn't an executable entry.")


def execution_body_from_xml(xml_tree: ET.Element) -> ScxmlExecutionBody:
    """
    Create an execution body from an XML tree.

    :param xml_tree: The XML tree to create the execution body from
    :return: The execution body
    """
    exec_body: ScxmlExecutionBody = []
    for exec_elem_xml in xml_tree:
        exec_body.append(execution_entry_from_xml(exec_elem_xml))
    return exec_body
