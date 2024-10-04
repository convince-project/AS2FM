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

from typing import Dict, List, Optional, Tuple, Union, get_args

from lxml import etree as ET

from as2fm.as2fm_common.common import is_comment
from as2fm.scxml_converter.scxml_entries import (
    BtGetValueInputPort,
    ScxmlBase,
    ScxmlParam,
    ScxmlRosDeclarationsContainer,
)
from as2fm.scxml_converter.scxml_entries.bt_utils import (
    BtPortsHandler,
    is_bt_event,
    replace_bt_event,
)
from as2fm.scxml_converter.scxml_entries.utils import (
    CallbackType,
    get_plain_expression,
    is_non_empty_string,
)
from as2fm.scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok,
    get_xml_argument,
    read_value_from_xml_child,
)

# Use delayed type evaluation: https://peps.python.org/pep-0484/#forward-references
ScxmlExecutableEntry = Union["ScxmlAssign", "ScxmlIf", "ScxmlSend"]
ScxmlExecutionBody = List[ScxmlExecutableEntry]
ConditionalExecutionBody = Tuple[str, ScxmlExecutionBody]


def instantiate_exec_body_bt_events(
    exec_body: Optional[ScxmlExecutionBody], instance_id: str
) -> None:
    """
    Instantiate the behavior tree events in the execution body.

    :param exec_body: The execution body to instantiate the BT events in
    :param instance_id: The instance ID of the BT node
    """
    if exec_body is not None:
        for entry in exec_body:
            entry.instantiate_bt_events(instance_id)


def update_exec_body_bt_ports_values(
    exec_body: Optional[ScxmlExecutionBody], bt_ports_handler: BtPortsHandler
) -> None:
    """
    Update the BT ports values in the execution body.
    """
    if exec_body is not None:
        for entry in exec_body:
            entry.update_bt_ports_values(bt_ports_handler)


class ScxmlIf(ScxmlBase):
    """This class represents SCXML conditionals."""

    @staticmethod
    def get_tag_name() -> str:
        return "if"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlIf":
        """
        Create a ScxmlIf object from an XML tree.

        :param xml_tree: The XML tree to create the object from.
        :param cb_type: The kind of callback executing this SCXML entry.
        """
        assert_xml_tag_ok(ScxmlIf, xml_tree)
        conditions: List[str] = []
        exec_bodies: List[ScxmlExecutionBody] = []
        conditions.append(xml_tree.attrib["cond"])
        current_body: ScxmlExecutionBody = []
        else_tag_found = False
        for child in xml_tree:
            if is_comment(child):
                continue
            if child.tag == "elseif":
                assert not else_tag_found, "Error: SCXML if: 'elseif' tag found after 'else' tag."
                conditions.append(child.attrib["cond"])
                exec_bodies.append(current_body)
                current_body = []
            elif child.tag == "else":
                assert not else_tag_found, "Error: SCXML if: multiple 'else' tags found."
                else_tag_found = True
                exec_bodies.append(current_body)
                current_body = []
            else:
                current_body.append(execution_entry_from_xml(child))
        else_body: Optional[ScxmlExecutionBody] = None
        if else_tag_found:
            else_body = current_body
        else:
            exec_bodies.append(current_body)
        assert len(conditions) == len(exec_bodies), (
            "Error: SCXML if: number of conditions and bodies do not match "
            f"({len(conditions)} != {len(exec_bodies)}). Conditions: {conditions}."
        )
        return ScxmlIf(list(zip(conditions, exec_bodies)), else_body)

    def __init__(
        self,
        conditional_executions: List[ConditionalExecutionBody],
        else_execution: Optional[ScxmlExecutionBody] = None,
    ):
        """
        Class representing a conditional execution in SCXML.

        :param conditional_executions: List of (condition - exec. body) pairs. Min n. pairs is one.
        :param else_execution: Execution to be done if no condition is met.
        :param cb_type: The kind of callback executing this SCXML entry.
        """
        self._conditional_executions: List[ConditionalExecutionBody] = conditional_executions
        self._else_execution: ScxmlExecutionBody = []
        if else_execution is not None:
            self._else_execution = else_execution
        self._cb_type: Optional[CallbackType] = None
        assert self.check_validity(), "Error: SCXML if: invalid if object."

    def set_callback_type(self, cb_type: CallbackType) -> None:
        """Set the cb type for this entry and its children."""
        self._cb_type = cb_type

    def get_conditional_executions(self) -> List[ConditionalExecutionBody]:
        """Get the conditional executions."""
        return self._conditional_executions

    def get_else_execution(self) -> ScxmlExecutionBody:
        """Get the else execution."""
        return self._else_execution

    def instantiate_bt_events(self, instance_id: str) -> None:
        """Instantiate the behavior tree events in the If action, if available."""
        for _, exec_body in self._conditional_executions:
            instantiate_exec_body_bt_events(exec_body, instance_id)
        instantiate_exec_body_bt_events(self._else_execution, instance_id)

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        for _, exec_body in self._conditional_executions:
            update_exec_body_bt_ports_values(exec_body, bt_ports_handler)
        update_exec_body_bt_ports_values(self._else_execution, bt_ports_handler)

    def check_validity(self) -> bool:
        valid_conditional_executions = len(self._conditional_executions) > 0 and all(
            isinstance(condition, str) and len(body) > 0 and valid_execution_body(body)
            for condition, body in self._conditional_executions
        )
        if not valid_conditional_executions:
            print("Error: SCXML if: Found invalid entries in conditional executions.")
        valid_else_execution = valid_execution_body(self._else_execution)
        if not valid_else_execution:
            print("Error: SCXML if: invalid else execution body found.")
        return valid_conditional_executions and valid_else_execution

    def check_valid_ros_instantiations(
        self, ros_declarations: ScxmlRosDeclarationsContainer
    ) -> bool:
        """Check if the ros instantiations have been declared."""
        # Check the executable content
        assert isinstance(
            ros_declarations, ScxmlRosDeclarationsContainer
        ), "Error: SCXML if: invalid ROS declarations type provided."
        for _, exec_body in self._conditional_executions:
            for exec_entry in exec_body:
                if not exec_entry.check_valid_ros_instantiations(ros_declarations):
                    return False
        for exec_entry in self._else_execution:
            if not exec_entry.check_valid_ros_instantiations(ros_declarations):
                return False
        return True

    def set_thread_id(self, thread_id: int) -> None:
        """Set the thread ID for the executable entries contained in the if object."""
        for _, exec_body in self._conditional_executions:
            for entry in exec_body:
                if hasattr(entry, "set_thread_id"):
                    entry.set_thread_id(thread_id)
        for entry in self._else_execution:
            if hasattr(entry, "set_thread_id"):
                entry.set_thread_id(thread_id)

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> "ScxmlIf":
        assert self._cb_type is not None, "Error: SCXML if: callback type not set."
        conditional_executions = []
        for condition, execution in self._conditional_executions:
            set_execution_body_callback_type(execution, self._cb_type)
            execution_body = as_plain_execution_body(execution, ros_declarations)
            assert execution_body is not None, "Error: SCXML if: invalid execution body."
            conditional_executions.append(
                (get_plain_expression(condition, self._cb_type), execution_body)
            )
        set_execution_body_callback_type(self._else_execution, self._cb_type)
        else_execution = as_plain_execution_body(self._else_execution, ros_declarations)
        return ScxmlIf(conditional_executions, else_execution)

    def as_xml(self) -> ET.Element:
        # Based on example in https://www.w3.org/TR/scxml/#if
        assert self.check_validity(), "SCXML: found invalid if object."
        first_conditional_execution = self._conditional_executions[0]
        xml_if = ET.Element(ScxmlIf.get_tag_name(), {"cond": first_conditional_execution[0]})
        append_execution_body_to_xml(xml_if, first_conditional_execution[1])
        for condition, execution in self._conditional_executions[1:]:
            xml_if.append(ET.Element("elseif", {"cond": condition}))
            append_execution_body_to_xml(xml_if, execution)
        if len(self._else_execution) > 0:
            xml_if.append(ET.Element("else"))
            append_execution_body_to_xml(xml_if, self._else_execution)
        return xml_if


class ScxmlSend(ScxmlBase):
    """This class represents a send action."""

    @staticmethod
    def get_tag_name() -> str:
        return "send"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlSend":
        """
        Create a ScxmlSend object from an XML tree.

        :param xml_tree: The XML tree to create the object from.
        :param cb_type: The kind of callback executing this SCXML entry.
        """
        assert (
            xml_tree.tag == ScxmlSend.get_tag_name()
        ), f"Error: SCXML send: XML tag name is not {ScxmlSend.get_tag_name()}."
        event = xml_tree.attrib["event"]
        params: List[ScxmlParam] = []
        assert params is not None, "Error: SCXML send: params is not valid."
        for param_xml in xml_tree:
            if is_comment(param_xml):
                continue
            params.append(ScxmlParam.from_xml_tree(param_xml))
        return ScxmlSend(event, params)

    def __init__(self, event: str, params: Optional[List[ScxmlParam]] = None):
        """
        Construct a new ScxmlSend object.

        :param event: The name of the event sent when executing this entry.
        :param params: The parameters to send as part of the event.
        :param cb_type: The kind of callback executing this SCXML entry.
        """
        if params is None:
            params = []
        self._event = event
        self._params = params
        self._cb_type: Optional[CallbackType] = None

    def set_callback_type(self, cb_type: CallbackType) -> None:
        """Set the cb type for this entry and its children."""
        self._cb_type = cb_type

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

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        """Update the values of potential entries making use of BT ports."""
        for param in self._params:
            param.update_bt_ports_values(bt_ports_handler)

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
        assert (
            self.__class__ is ScxmlSend
        ), f"Error: SCXML send: cannot append param to derived class {self.__class__.__name__}."
        assert isinstance(param, ScxmlParam), "Error: SCXML send: invalid param."
        self._params.append(param)

    def as_plain_scxml(self, _) -> "ScxmlSend":
        # For now we don't need to do anything here. Change this to handle ros expr in scxml params.
        assert self._cb_type is not None, "Error: SCXML send: callback type not set."
        for param in self._params:
            param.set_callback_type(self._cb_type)
        # For now, no conversion to plain scxml is expected for params
        # param.as_plain_scxml()
        return ScxmlSend(self._event, self._params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid send object."
        xml_send = ET.Element(ScxmlSend.get_tag_name(), {"event": self._event})
        for param in self._params:
            xml_send.append(param.as_xml())
        return xml_send


class ScxmlAssign(ScxmlBase):
    """This class represents a variable assignment."""

    @staticmethod
    def get_tag_name() -> str:
        return "assign"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlAssign":
        """
        Create a ScxmlAssign object from an XML tree.

        :param xml_tree: The XML tree to create the object from.
        :param cb_type: The kind of callback executing this SCXML entry.
        """
        assert_xml_tag_ok(ScxmlAssign, xml_tree)
        location = get_xml_argument(ScxmlAssign, xml_tree, "location")
        expr = get_xml_argument(ScxmlAssign, xml_tree, "expr", none_allowed=True)
        if expr is None:
            expr = read_value_from_xml_child(xml_tree, "expr", (BtGetValueInputPort, str))
            assert expr is not None, "Error: SCXML assign: expr is not valid."
        return ScxmlAssign(location, expr)

    def __init__(self, location: str, expr: Union[str, BtGetValueInputPort]):
        self._location = location
        self._expr = expr
        self._cb_type: Optional[CallbackType] = None

    def set_callback_type(self, cb_type: CallbackType) -> None:
        """Set the cb type for this assignment."""
        self._cb_type = cb_type

    def get_location(self) -> str:
        """Get the location to assign."""
        return self._location

    def get_expr(self) -> Union[str, BtGetValueInputPort]:
        """Get the expression to assign."""
        return self._expr

    def instantiate_bt_events(self, _) -> None:
        """This functionality is not needed in this class."""
        return

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        """Update the values of potential entries making use of BT ports."""
        if isinstance(self._expr, BtGetValueInputPort):
            self._expr = bt_ports_handler.get_in_port_value(self._expr.get_key_name())

    def check_validity(self) -> bool:
        # TODO: Check that the location to assign exists in the data-model
        valid_location = is_non_empty_string(ScxmlAssign, "location", self._location)
        valid_expr = is_non_empty_string(ScxmlAssign, "expr", self._expr)
        return valid_location and valid_expr

    def check_valid_ros_instantiations(self, _) -> bool:
        """Check if the ros instantiations have been declared."""
        # This has nothing to do with ROS. Return always True
        return True

    def as_plain_scxml(self, _) -> "ScxmlAssign":
        # TODO: Might make sense to check if the assignment happens in a topic callback
        assert self._cb_type is not None, "Error: SCXML assign: callback type not set."
        expr = get_plain_expression(self._expr, self._cb_type)
        return ScxmlAssign(self._location, expr)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid assign object."
        return ET.Element(
            ScxmlAssign.get_tag_name(), {"location": self._location, "expr": self._expr}
        )


# Get the resolved types from the forward references in ScxmlExecutableEntry
_ResolvedScxmlExecutableEntry = tuple(
    entry._evaluate(globals(), locals(), frozenset()) for entry in get_args(ScxmlExecutableEntry)
)


def valid_execution_body_entry_types(exec_body: ScxmlExecutionBody) -> bool:
    """
    Check if the type of the entries in an execution body are valid.

    :param exec_body: The execution body to check
    :return: True if all types of the body entries are the expected ones, False otherwise
    """
    if not isinstance(exec_body, list):
        print("Error: SCXML execution body: invalid type found: expected a list.")
        return False
    for entry in exec_body:
        if not isinstance(entry, _ResolvedScxmlExecutableEntry):
            print(
                f"Error: SCXML execution body: entry type {type(entry)} not in valid set."
                f" {_ResolvedScxmlExecutableEntry}."
            )
            return False
    return True


def valid_execution_body(execution_body: ScxmlExecutionBody) -> bool:
    """
    Check if an execution body is valid.

    :param execution_body: The execution body to check
    :return: True if the execution body is valid, False otherwise
    """
    if valid_execution_body_entry_types(execution_body):
        for entry in execution_body:
            if not entry.check_validity():
                print(f"Error: SCXML execution body: content of {entry.get_tag_name()} is invalid.")
                return False
        return True
    return False


def execution_entry_from_xml(xml_tree: ET.Element) -> ScxmlExecutableEntry:
    """
    Create an execution entry from an XML tree.

    :param xml_tree: The XML tree to create the execution entry from.
    :return: The execution entry
    """
    from as2fm.scxml_converter.scxml_entries.scxml_ros_base import RosTrigger

    # TODO: This should be generated only once, since it stays as it is
    tag_to_cls: Dict[str, ScxmlExecutableEntry] = {
        cls.get_tag_name(): cls for cls in _ResolvedScxmlExecutableEntry
    }
    tag_to_cls.update({cls.get_tag_name(): cls for cls in RosTrigger.__subclasses__()})
    exec_tag = xml_tree.tag
    assert (
        exec_tag in tag_to_cls
    ), f"Error: SCXML conversion: tag {exec_tag} isn't an executable entry."
    return tag_to_cls[exec_tag].from_xml_tree(xml_tree)


def execution_body_from_xml(xml_tree: ET.Element) -> ScxmlExecutionBody:
    """
    Create an execution body from an XML tree.

    :param xml_tree: The XML tree to create the execution body from.
    :return: The execution body
    """
    exec_body: ScxmlExecutionBody = []
    for exec_elem_xml in xml_tree:
        if not is_comment(exec_elem_xml):
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


def set_execution_body_callback_type(exec_body: ScxmlExecutionBody, cb_type: CallbackType) -> None:
    """
    Set the callback type for the provided execution body.

    :param exec_body: The execution body that required the callback type to be set.
    :param cb_type: The callback type to set.
    """
    for entry in exec_body:
        entry.set_callback_type(cb_type)


def as_plain_execution_body(
    exec_body: Optional[ScxmlExecutionBody],
    ros_declarations: ScxmlRosDeclarationsContainer,
) -> Optional[ScxmlExecutionBody]:
    """
    Convert the execution body to plain SCXML.

    :param exec_body: The execution body to convert
    :param ros_declarations: The ROS declarations
    :return: The converted execution body
    """
    if exec_body is None:
        return None
    return [entry.as_plain_scxml(ros_declarations) for entry in exec_body if not is_comment(entry)]
