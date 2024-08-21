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
Declaration of SCXML tags related to ROS Action Clients.

Based loosely on https://design.ros2.org/articles/actions.html
"""

from typing import List, Optional, Union
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (
    ScxmlRoot, ScxmlDataModel, ScxmlExecutionBody, ScxmlSend, ScxmlTransition, BtGetValueInputPort,
    as_plain_execution_body, execution_body_from_xml, valid_execution_body,
    ScxmlRosDeclarationsContainer)

from scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from scxml_converter.scxml_entries.ros_utils import (
    is_action_type_known)
from scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok, get_xml_argument, read_value_from_xml_arg_or_child, get_children_as_scxml)
from scxml_converter.scxml_entries.utils import is_non_empty_string


class RosActionThread(ScxmlRoot):
    """
    SCXML declaration of a set of threads for executing the action server code.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_thread"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionThread":
        """Create a RosActionThread object from an XML tree."""
        assert_xml_tag_ok(RosActionThread, xml_tree)
        action_alias = get_xml_argument(RosActionThread, xml_tree, "name")
        n_threads = get_xml_argument(RosActionThread, xml_tree, "n_threads")
        initial_state = get_xml_argument(RosActionThread, xml_tree, "initial_state")
        datamodel = get_children_as_scxml(xml_tree, (ScxmlDataModel,))
        ros_declarations: List[ScxmlRosDeclarations] = get_children_as_scxml(
            xml_tree, get_args(ScxmlRosDeclarations))
        # TODO: Append the action server to the ROS declarations in the thread, somehow

        action_name = read_value_from_xml_arg_or_child(RosActionThread, xml_tree, "action_name",
                                                       (BtGetValueInputPort, str))
        action_type = get_xml_argument(RosActionClient, xml_tree, "type")
        return RosActionClient(action_name, action_type, action_alias)

    def __init__(self, action_name: Union[str, BtGetValueInputPort], action_type: str,
                 action_alias: Optional[str] = None) -> None:
        """
        Initialize a new RosActionClient object.

        :param action_name: Comm. interface used by the action.
        :param action_type: ROS type of the service.
        :param action_alias: Alias for the service client, for the handler to reference to it
        """
        self._action_name = action_name
        self._action_type = action_type
        self._action_alias = action_alias
        assert isinstance(action_name, (str, BtGetValueInputPort)), \
            "Error: SCXML Service Client: invalid service name."
        if self._action_alias is None:
            assert is_non_empty_string(RosActionClient, "action_name", self._action_name), \
                "Error: SCXML Action Client: an alias name is required for dynamic action names."
            self._action_alias = action_name

    def get_action_name(self) -> str:
        """Get the name of the action."""
        return self._action_name

    def get_action_type(self) -> str:
        """Get the type of the action."""
        return self._action_type

    def get_name(self) -> str:
        """Get the alias of the action client."""
        return self._action_alias

    def check_validity(self) -> bool:
        valid_alias = is_non_empty_string(RosActionClient, "name", self._action_alias)
        valid_action_name = isinstance(self._action_name, BtGetValueInputPort) or \
            is_non_empty_string(RosActionClient, "action_name", self._action_name)
        valid_action_type = is_action_type_known(self._action_type)
        if not valid_action_type:
            print(f"Error: SCXML Action Client: action type {self._action_type} is not valid.")
        return valid_alias and valid_action_name and valid_action_type

    def check_valid_instantiation(self) -> bool:
        """Check if the topic publisher has undefined entries (i.e. from BT ports)."""
        return is_non_empty_string(RosActionClient, "action_name", self._action_name)

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        """Update the values of potential entries making use of BT ports."""
        if isinstance(self._action_name, BtGetValueInputPort):
            self._action_name = bt_ports_handler.get_in_port_value(self._action_name.get_key_name())

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlRoot:
        raise NotImplementedError("Error: This should return a ScxmlRoot.")

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Action Client: invalid parameters."
        xml_action_server = ET.Element(
            RosActionClient.get_tag_name(),
            {"name": self._action_alias,
             "action_name": self._action_name,
             "type": self._action_type})
        return xml_action_server


class RosActionHandleThreadStart(ScxmlTransition):
    """SCXML object representing the handler of am action result for a service client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_result"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionHandleResult":
        """Create a RosActionHandleResult object from an XML tree."""
        assert_xml_tag_ok(RosActionHandleResult, xml_tree)
        client_name = get_xml_argument(RosActionHandleResult, xml_tree, "name")
        target_name = get_xml_argument(RosActionHandleResult, xml_tree, "target")
        exec_body = execution_body_from_xml(xml_tree)
        return RosActionHandleResult(client_name, target_name, exec_body)

    def __init__(self, action_client: Union[str, RosActionClient], target: str,
                 body: Optional[ScxmlExecutionBody] = None) -> None:
        """
        Initialize a new RosActionHandleResult object.

        :param action_client: Action client used by this handler, or its name.
        :param target: Target state to transition to after the feedback is received.
        :param body: Execution body to be executed upon feedback reception (before transition).
        """
        if isinstance(action_client, RosActionClient):
            self._client_name = action_client.get_name()
        else:
            assert is_non_empty_string(RosActionHandleResult, "name", action_client)
            self._client_name = action_client
        self._target = target
        self._body = body
        assert self.check_validity(), "Error: SCXML RosActionHandleResult: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosActionHandleResult, "name", self._client_name)
        valid_target = is_non_empty_string(RosActionHandleResult, "target", self._target)
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_body:
            print("Error: SCXML RosActionHandleResult: body is not valid.")
        return valid_name and valid_target and valid_body

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML RosActionHandleResult: invalid ROS declarations container."
        if not ros_declarations.is_action_client_defined(self._client_name):
            print("Error: SCXML RosActionHandleResult: "
                  f"action client {self._client_name} not declared.")
            return False
        if not super().check_valid_ros_instantiations(ros_declarations):
            print("Error: SCXML RosActionHandleResult: invalid ROS instantiations in exec body.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML service response handler: invalid ROS instantiations."
        automaton_name = ros_declarations.get_automaton_name()
        interface_name, _ = ros_declarations.get_action_client_info(self._client_name)
        event_name = generate_action_result_handle_event(interface_name, automaton_name)
        target = self._target
        body = as_plain_execution_body(self._body, ros_declarations)
        return ScxmlTransition(target, [event_name], None, body)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML RosActionHandleResult: invalid parameters."
        xml_handle_feedback = ET.Element(RosActionHandleResult.get_tag_name(),
                                         {"name": self._client_name, "target": self._target})
        if self._body is not None:
            for body_elem in self._body:
                xml_handle_feedback.append(body_elem.as_xml())
        return xml_handle_feedback
