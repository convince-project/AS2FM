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

from typing import List, Optional, Tuple, Union, get_args
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (ScxmlBase, ScxmlParam,
                                           ScxmlRosDeclarationsContainer)
from scxml_converter.scxml_entries.ros_utils import replace_ros_interface_expression
from scxml_converter.scxml_entries.bt_utils import is_bt_event, replace_bt_event

# Use delayed type evaluation: https://peps.python.org/pep-0484/#forward-references
ScxmlExecutableEntry = Union['ScxmlAssign', 'ScxmlIf', 'ScxmlSend']
ScxmlExecutionBody = List[ScxmlExecutableEntry]
ConditionalExecutionBody = Tuple[str, ScxmlExecutionBody]


def instantiate_exec_body_bt_events(
        exec_body: Optional[ScxmlExecutionBody], instance_id: str) -> None:
    """
    Instantiate the behavior tree events in the execution body.

    :param exec_body: The execution body to instantiate the BT events in
    :param instance_id: The instance ID of the BT node
    """
    if exec_body is not None:
        for entry in exec_body:
            entry.instantiate_bt_events(instance_id)


class ScxmlIf(ScxmlBase):
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

    @staticmethod
    def get_tag_name() -> str:
        return "if"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlIf":
        """Create a ScxmlIf object from an XML tree."""
        assert xml_tree.tag == ScxmlIf.get_tag_name(), \
            f"Error: SCXML if: XML tag name is not {ScxmlIf.get_tag_name()}."
        conditions: List[str] = []
        exec_bodies: List[ScxmlExecutionBody] = []
        conditions.append(xml_tree.attrib["cond"])
        current_body: Optional[ScxmlExecutionBody] = []
        assert current_body is not None, "Error: SCXML if: current body is not valid."
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

    def get_conditional_executions(self) -> List[ConditionalExecutionBody]:
        """Get the conditional executions."""
        return self._conditional_executions

    def get_else_execution(self) -> Optional[ScxmlExecutionBody]:
        """Get the else execution."""
        return self._else_execution

    def instantiate_bt_events(self, instance_id: str) -> None:
        """Instantiate the behavior tree events in the If action, if available."""
        for _, exec_body in self._conditional_executions:
            instantiate_exec_body_bt_events(exec_body, instance_id)
        instantiate_exec_body_bt_events(self._else_execution, instance_id)

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
            valid_execution = valid_execution_body(execution)
            if not valid_condition:
                print("Error: SCXML if: invalid condition found.")
            if not valid_execution:
                print("Error: SCXML if: invalid execution body found.")
            valid_conditional_executions = valid_tuple and valid_condition and valid_execution
            if not valid_conditional_executions:
                break
        valid_else_execution = \
            self._else_execution is None or valid_execution_body(self._else_execution)
        if not valid_else_execution:
            print("Error: SCXML if: invalid else execution body found.")
        return valid_conditional_executions and valid_else_execution

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ros instantiations have been declared."""
        # Check the executable content
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML if: invalid ROS declarations type provided."
        for _, exec_body in self._conditional_executions:
            for exec_entry in exec_body:
                if not exec_entry.check_valid_ros_instantiations(ros_declarations):
                    return False
        if self._else_execution is not None:
            for exec_entry in self._else_execution:
                if not exec_entry.check_valid_ros_instantiations(ros_declarations):
                    return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> "ScxmlIf":
        condional_executions = []
        for condition, execution in self._conditional_executions:
            execution_body = as_plain_execution_body(execution, ros_declarations)
            assert execution_body is not None, "Error: SCXML if: invalid execution body."
            condional_executions.append((replace_ros_interface_expression(condition),
                                         execution_body))
        else_execution = as_plain_execution_body(self._else_execution, ros_declarations)
        return ScxmlIf(condional_executions, else_execution)

    def as_xml(self) -> ET.Element:
        # Based on example in https://www.w3.org/TR/scxml/#if
        assert self.check_validity(), "SCXML: found invalid if object."
        first_conditional_execution = self._conditional_executions[0]
        xml_if = ET.Element(ScxmlIf.get_tag_name(), {"cond": first_conditional_execution[0]})
        append_execution_body_to_xml(xml_if, first_conditional_execution[1])
        for condition, execution in self._conditional_executions[1:]:
            xml_if.append(ET.Element('elseif', {"cond": condition}))
            append_execution_body_to_xml(xml_if, execution)
        if self._else_execution is not None:
            xml_if.append(ET.Element('else'))
            append_execution_body_to_xml(xml_if, self._else_execution)
        return xml_if


class ScxmlSend(ScxmlBase):
    """This class represents a send action."""

    def __init__(self, event: str, params: Optional[List[ScxmlParam]] = None):
        if params is None:
            params = []
        self._event = event
        self._params = params

    @staticmethod
    def get_tag_name() -> str:
        return "send"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlSend":
        """Create a ScxmlSend object from an XML tree."""
        assert xml_tree.tag == ScxmlSend.get_tag_name(), \
            f"Error: SCXML send: XML tag name is not {ScxmlSend.get_tag_name()}."
        event = xml_tree.attrib["event"]
        params: List[ScxmlParam] = []
        assert params is not None, "Error: SCXML send: params is not valid."
        for param_xml in xml_tree:
            params.append(ScxmlParam.from_xml_tree(param_xml))
        return ScxmlSend(event, params)

    def get_event(self) -> str:
        """Get the event to send."""
        return self._event

    def get_params(self) -> List[ScxmlParam]:
        """Get the parameters to send."""
        return self._params

    def instantiate_bt_events(self, instance_id: str) -> None:
        """Instantiate the behavior tree events in the send action, if available."""
        # Make sure this method is executed only on ScxmlSend objects, and not on derived classes
        if type(self) is ScxmlSend and is_bt_event(self._event):
            # Those are expected to be only bt_success, bt_failure and bt_running
            self._event = replace_bt_event(self._event, instance_id)

    def check_validity(self) -> bool:
        valid_event = isinstance(self._event, str) and len(self._event) > 0
        valid_params = True
        for param in self._params:
            valid_param = isinstance(param, ScxmlParam) and param.check_validity()
            valid_params = valid_params and valid_param
        if not valid_event:
            print("Error: SCXML send: event is not valid.")
        if not valid_params:
            print("Error: SCXML send: one or more param entries are not valid.")
        return valid_event and valid_params

    def check_valid_ros_instantiations(self, _) -> bool:
        """Check if the ros instantiations have been declared."""
        # This has nothing to do with ROS. Return always True
        return True

    def append_param(self, param: ScxmlParam) -> None:
        assert isinstance(param, ScxmlParam), "Error: SCXML send: invalid param."
        self._params.append(param)

    def as_plain_scxml(self, _) -> "ScxmlSend":
        return self

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid send object."
        xml_send = ET.Element(ScxmlSend.get_tag_name(), {"event": self._event})
        for param in self._params:
            xml_send.append(param.as_xml())
        return xml_send


class ScxmlAssign(ScxmlBase):
    """This class represents a variable assignment."""

    def __init__(self, location: str, expr: str):
        self._location = location
        self._expr = expr

    @staticmethod
    def get_tag_name() -> str:
        return "assign"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlAssign":
        """Create a ScxmlAssign object from an XML tree."""
        assert xml_tree.tag == ScxmlAssign.get_tag_name(), \
            f"Error: SCXML assign: XML tag name is {xml_tree.tag} != {ScxmlAssign.get_tag_name()}."
        location = xml_tree.attrib.get("location")
        assert location is not None and len(location) > 0, \
            "Error: SCXML assign: location is not valid."
        expr = xml_tree.attrib.get("expr")
        assert expr is not None and len(expr) > 0, \
            "Error: SCXML assign: expr is not valid."
        return ScxmlAssign(location, expr)

    def get_location(self) -> str:
        """Get the location to assign."""
        return self._location

    def get_expr(self) -> str:
        """Get the expression to assign."""
        return self._expr

    def instantiate_bt_events(self, _) -> None:
        """This functionality is not needed in this class."""
        return

    def check_validity(self) -> bool:
        # TODO: Check that the location to assign exists in the data-model
        valid_location = isinstance(self._location, str) and len(self._location) > 0
        valid_expr = isinstance(self._expr, str) and len(self._expr) > 0
        if not valid_location:
            print("Error: SCXML assign: location is not valid.")
        if not valid_expr:
            print("Error: SCXML assign: expr is not valid.")
        return valid_location and valid_expr

    def check_valid_ros_instantiations(self, _) -> bool:
        """Check if the ros instantiations have been declared."""
        # This has nothing to do with ROS. Return always True
        return True

    def as_plain_scxml(self, _) -> "ScxmlAssign":
        # TODO: Might make sense to check if the assignment happens in a topic callback
        expr = replace_ros_interface_expression(self._expr)
        return ScxmlAssign(self._location, expr)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid assign object."
        return ET.Element(ScxmlAssign.get_tag_name(), {
            "location": self._location, "expr": self._expr})


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
    from .scxml_ros_entries import ScxmlRosSends

    # TODO: This should be generated only once, since it stays as it is
    tag_to_cls = {cls.get_tag_name(): cls for cls in _ResolvedScxmlExecutableEntry + ScxmlRosSends}
    exec_tag = xml_tree.tag
    assert exec_tag in tag_to_cls, \
        f"Error: SCXML conversion: tag {exec_tag} isn't an executable entry."
    return tag_to_cls[exec_tag].from_xml_tree(xml_tree)


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


def append_execution_body_to_xml(xml_parent: ET.Element, exec_body: ScxmlExecutionBody) -> None:
    """
    Append an execution body to an existing XML element.

    :param xml_parent: The parent XML element to append the executable entries to
    :param exec_body: The execution body to append
    """
    for exec_entry in exec_body:
        xml_parent.append(exec_entry.as_xml())


def as_plain_execution_body(
        exec_body: Optional[ScxmlExecutionBody],
        ros_declarations: ScxmlRosDeclarationsContainer) -> Optional[ScxmlExecutionBody]:
    """
    Convert the execution body to plain SCXML.

    :param exec_body: The execution body to convert
    :param ros_declarations: The ROS declarations
    :return: The converted execution body
    """
    if exec_body is None:
        return None
    return [entry.as_plain_scxml(ros_declarations) for entry in exec_body]
