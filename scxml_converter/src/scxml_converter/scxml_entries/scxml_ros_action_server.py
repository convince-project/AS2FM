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
    RosField, ScxmlBase, ScxmlExecutionBody, ScxmlSend, ScxmlTransition, BtGetValueInputPort,
    as_plain_execution_body, execution_body_from_xml, valid_execution_body,
    ScxmlRosDeclarationsContainer)

from scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from scxml_converter.scxml_entries.ros_utils import (
    RosDeclaration, is_action_type_known)
from scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok, get_xml_argument, read_value_from_xml_arg_or_child)
from scxml_converter.scxml_entries.utils import is_non_empty_string


class RosActionServer(RosDeclaration):
    """Object used in SCXML root to declare a new action client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_client"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionServer":
        """Create a RosActionServer object from an XML tree."""
        assert_xml_tag_ok(RosActionServer, xml_tree)
        action_alias = get_xml_argument(RosActionServer, xml_tree, "name", none_allowed=True)
        action_name = read_value_from_xml_arg_or_child(RosActionServer, xml_tree, "action_name",
                                                       (BtGetValueInputPort, str))
        action_type = get_xml_argument(RosActionServer, xml_tree, "type")
        return RosActionServer(action_name, action_type, action_alias)

    def check_valid_interface_type(self) -> bool:
        if not is_action_type_known(self._interface_type):
            print(f"Error: SCXML RosActionServer: invalid action type {self._interface_type}.")
            return False
        return True

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML RosActionServer: invalid parameters."
        xml_action_server = ET.Element(
            RosActionServer.get_tag_name(),
            {"name": self._interface_alias,
             "action_name": self._interface_name,
             "type": self._interface_type})
        return xml_action_server


class RosActionThread(ScxmlBase):
    """Object used in SCXML root to declare a new action client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_client"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionClient":
        """Create a RosActionClient object from an XML tree."""
        assert_xml_tag_ok(RosActionClient, xml_tree)
        action_alias = get_xml_argument(
            RosActionClient, xml_tree, "name", none_allowed=True)
        action_name = read_value_from_xml_arg_or_child(RosActionClient, xml_tree, "action_name",
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

    def as_plain_scxml(self, _) -> ScxmlBase:
        # This is discarded in the to_plain_scxml_and_declarations method from ScxmlRoot
        raise RuntimeError("Error: SCXML ROS declarations cannot be converted to plain SCXML.")

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Action Client: invalid parameters."
        xml_action_server = ET.Element(
            RosActionClient.get_tag_name(),
            {"name": self._action_alias,
             "action_name": self._action_name,
             "type": self._action_type})
        return xml_action_server


class RosActionHandleGoalRequest(ScxmlTransition):
    """
    SCXML object representing the handler of an action response upon a goal request.

    A server might accept or refuse a goal request, based on its internal state.
    This handler is meant to handle both acceptance or refusal of a request.
    Translating this to plain-SCXML, it results to two conditional transitions.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_goal_response"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionHandleGoalResponse":
        """Create a RosServiceServer object from an XML tree."""
        assert_xml_tag_ok(RosActionHandleGoalResponse, xml_tree)
        action_name = get_xml_argument(RosActionHandleGoalResponse, xml_tree, "name")
        accept_target = get_xml_argument(RosActionHandleGoalResponse, xml_tree, "accept")
        decline_target = get_xml_argument(RosActionHandleGoalResponse, xml_tree, "decline")
        return RosActionHandleGoalResponse(action_name, accept_target, decline_target)

    def __init__(self, action_client: Union[str, RosActionClient],
                 accept_target: str, decline_target: str) -> None:
        """
        Initialize a new RosActionHandleGoalResponse object.

        :param action_client: Action client used by this handler, or its name.
        :param accept_target: State to transition to, in case of goal acceptance.
        :param decline_target: State to transition to, in case of goal refusal.
        """
        if isinstance(action_client, RosActionClient):
            self._client_name = action_client.get_name()
        else:
            assert is_non_empty_string(RosActionHandleGoalResponse, "name", action_client)
            self._client_name = action_client
        self._accept_target = accept_target
        self._decline_target = decline_target
        assert self.check_validity(), "Error: SCXML RosActionHandleGoalResponse: invalid params."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosActionHandleGoalResponse, "name", self._client_name)
        valid_accept = is_non_empty_string(RosActionHandleGoalResponse, "accept",
                                           self._accept_target)
        valid_decline = is_non_empty_string(RosActionHandleGoalResponse, "decline",
                                            self._decline_target)
        return valid_name and valid_accept and valid_decline

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML Service Handle Response: invalid ROS declarations container."
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML action goal request: invalid ROS declarations container."
        if not ros_declarations.is_action_client_defined(self._client_name):
            print("Error: SCXML action goal request: "
                  f"action client {self._client_name} not declared.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML service response handler: invalid ROS instantiations."
        automaton_name = ros_declarations.get_automaton_name()
        interface_name, _ = ros_declarations.get_action_client_info(self._client_name)
        accept_event = generate_action_goal_accepted_event(interface_name, automaton_name)
        decline_event = generate_action_goal_declined_event(interface_name, automaton_name)
        accept_transition = ScxmlTransition(self._accept_target, [accept_event])
        decline_transition = ScxmlTransition(self._decline_target, [decline_event])
        return [accept_transition, decline_transition]

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML Service Handle Response: invalid parameters."
        return ET.Element(RosActionHandleGoalResponse.get_tag_name(),
                          {"name": self._client_name,
                           "accept": self._accept_target, "decline": self._decline_target})


class RosActionAcceptGoal(ScxmlSend):
    """Object representing a ROS Action Goal (request, from the client side) in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_send_goal"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionSendGoal":
        """Create a RosActionSendGoal object from an XML tree."""
        assert_xml_tag_ok(RosActionSendGoal, xml_tree)
        action_name = get_xml_argument(RosActionSendGoal, xml_tree, "name")
        fields: List[RosField] = []
        for field_xml in xml_tree:
            fields.append(RosField.from_xml_tree(field_xml))
        return RosActionSendGoal(action_name, fields)

    def __init__(self, action_client: Union[str, RosActionClient],
                 fields: List[RosField] = None) -> None:
        """
        Initialize a new RosActionSendGoal object.

        :param action_client: The ActionClient object used by the sender, or its name.
        :param fields: List of fields to be sent in the goal request.
        """
        if isinstance(action_client, RosActionClient):
            self._client_name = action_client.get_name()
        else:
            assert is_non_empty_string(RosActionSendGoal, "name", action_client)
            self._client_name = action_client
        if fields is None:
            fields = []
        self._fields = fields
        assert self.check_validity(), "Error: SCXML Action Goal Request: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosActionSendGoal, "name", self._client_name)
        valid_fields = all([isinstance(field, RosField) and field.check_validity()
                            for field in self._fields])
        if not valid_fields:
            print("Error: SCXML service request: fields are not valid.")
        return valid_name and valid_fields

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ros instantiations have been declared."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML action goal request: invalid ROS declarations container."
        if not ros_declarations.is_action_client_defined(self._client_name):
            print("Error: SCXML action goal request: "
                  f"action client {self._client_name} not declared.")
            return False
        if not ros_declarations.check_valid_action_goal_fields(self._client_name, self._fields):
            print("Error: SCXML action goal request: invalid fields in request.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML action goal request: invalid ROS instantiations."
        automaton_name = ros_declarations.get_automaton_name()
        action_interface, _ = ros_declarations.get_action_client_info(self._client_name)
        event_name = generate_action_goal_req_event(action_interface, automaton_name)
        event_params = [field.as_plain_scxml(ros_declarations) for field in self._fields]
        return ScxmlSend(event_name, event_params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML action goal Request: invalid parameters."
        xml_goal_request = ET.Element(RosActionSendGoal.get_tag_name(), {
            "name": self._client_name})
        if self._fields is not None:
            for field in self._fields:
                xml_goal_request.append(field.as_xml())
        return xml_goal_request


class RosActionRejectGoal(ScxmlSend):
    """Object representing a ROS Action Goal (request, from the client side) in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_send_goal"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionSendGoal":
        """Create a RosActionSendGoal object from an XML tree."""
        assert_xml_tag_ok(RosActionSendGoal, xml_tree)
        action_name = get_xml_argument(RosActionSendGoal, xml_tree, "name")
        fields: List[RosField] = []
        for field_xml in xml_tree:
            fields.append(RosField.from_xml_tree(field_xml))
        return RosActionSendGoal(action_name, fields)

    def __init__(self, action_client: Union[str, RosActionClient],
                 fields: List[RosField] = None) -> None:
        """
        Initialize a new RosActionSendGoal object.

        :param action_client: The ActionClient object used by the sender, or its name.
        :param fields: List of fields to be sent in the goal request.
        """
        if isinstance(action_client, RosActionClient):
            self._client_name = action_client.get_name()
        else:
            assert is_non_empty_string(RosActionSendGoal, "name", action_client)
            self._client_name = action_client
        if fields is None:
            fields = []
        self._fields = fields
        assert self.check_validity(), "Error: SCXML Action Goal Request: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosActionSendGoal, "name", self._client_name)
        valid_fields = all([isinstance(field, RosField) and field.check_validity()
                            for field in self._fields])
        if not valid_fields:
            print("Error: SCXML service request: fields are not valid.")
        return valid_name and valid_fields

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ros instantiations have been declared."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML action goal request: invalid ROS declarations container."
        if not ros_declarations.is_action_client_defined(self._client_name):
            print("Error: SCXML action goal request: "
                  f"action client {self._client_name} not declared.")
            return False
        if not ros_declarations.check_valid_action_goal_fields(self._client_name, self._fields):
            print("Error: SCXML action goal request: invalid fields in request.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML action goal request: invalid ROS instantiations."
        automaton_name = ros_declarations.get_automaton_name()
        action_interface, _ = ros_declarations.get_action_client_info(self._client_name)
        event_name = generate_action_goal_req_event(action_interface, automaton_name)
        event_params = [field.as_plain_scxml(ros_declarations) for field in self._fields]
        return ScxmlSend(event_name, event_params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML action goal Request: invalid parameters."
        xml_goal_request = ET.Element(RosActionSendGoal.get_tag_name(), {
            "name": self._client_name})
        if self._fields is not None:
            for field in self._fields:
                xml_goal_request.append(field.as_xml())
        return xml_goal_request


class RosActionStartThread(ScxmlSend):
    """Object representing a ROS Action Goal (request, from the client side) in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_send_goal"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionSendGoal":
        """Create a RosActionSendGoal object from an XML tree."""
        assert_xml_tag_ok(RosActionSendGoal, xml_tree)
        action_name = get_xml_argument(RosActionSendGoal, xml_tree, "name")
        fields: List[RosField] = []
        for field_xml in xml_tree:
            fields.append(RosField.from_xml_tree(field_xml))
        return RosActionSendGoal(action_name, fields)

    def __init__(self, action_client: Union[str, RosActionClient],
                 fields: List[RosField] = None) -> None:
        """
        Initialize a new RosActionSendGoal object.

        :param action_client: The ActionClient object used by the sender, or its name.
        :param fields: List of fields to be sent in the goal request.
        """
        if isinstance(action_client, RosActionClient):
            self._client_name = action_client.get_name()
        else:
            assert is_non_empty_string(RosActionSendGoal, "name", action_client)
            self._client_name = action_client
        if fields is None:
            fields = []
        self._fields = fields
        assert self.check_validity(), "Error: SCXML Action Goal Request: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosActionSendGoal, "name", self._client_name)
        valid_fields = all([isinstance(field, RosField) and field.check_validity()
                            for field in self._fields])
        if not valid_fields:
            print("Error: SCXML service request: fields are not valid.")
        return valid_name and valid_fields

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ros instantiations have been declared."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML action goal request: invalid ROS declarations container."
        if not ros_declarations.is_action_client_defined(self._client_name):
            print("Error: SCXML action goal request: "
                  f"action client {self._client_name} not declared.")
            return False
        if not ros_declarations.check_valid_action_goal_fields(self._client_name, self._fields):
            print("Error: SCXML action goal request: invalid fields in request.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML action goal request: invalid ROS instantiations."
        automaton_name = ros_declarations.get_automaton_name()
        action_interface, _ = ros_declarations.get_action_client_info(self._client_name)
        event_name = generate_action_goal_req_event(action_interface, automaton_name)
        event_params = [field.as_plain_scxml(ros_declarations) for field in self._fields]
        return ScxmlSend(event_name, event_params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML action goal Request: invalid parameters."
        xml_goal_request = ET.Element(RosActionSendGoal.get_tag_name(), {
            "name": self._client_name})
        if self._fields is not None:
            for field in self._fields:
                xml_goal_request.append(field.as_xml())
        return xml_goal_request


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


class RosActionSendFeedback(ScxmlSend):
    """Object representing a ROS Action Goal (request, from the client side) in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_send_goal"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionSendGoal":
        """Create a RosActionSendGoal object from an XML tree."""
        assert_xml_tag_ok(RosActionSendGoal, xml_tree)
        action_name = get_xml_argument(RosActionSendGoal, xml_tree, "name")
        fields: List[RosField] = []
        for field_xml in xml_tree:
            fields.append(RosField.from_xml_tree(field_xml))
        return RosActionSendGoal(action_name, fields)

    def __init__(self, action_client: Union[str, RosActionClient],
                 fields: List[RosField] = None) -> None:
        """
        Initialize a new RosActionSendGoal object.

        :param action_client: The ActionClient object used by the sender, or its name.
        :param fields: List of fields to be sent in the goal request.
        """
        if isinstance(action_client, RosActionClient):
            self._client_name = action_client.get_name()
        else:
            assert is_non_empty_string(RosActionSendGoal, "name", action_client)
            self._client_name = action_client
        if fields is None:
            fields = []
        self._fields = fields
        assert self.check_validity(), "Error: SCXML Action Goal Request: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosActionSendGoal, "name", self._client_name)
        valid_fields = all([isinstance(field, RosField) and field.check_validity()
                            for field in self._fields])
        if not valid_fields:
            print("Error: SCXML service request: fields are not valid.")
        return valid_name and valid_fields

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ros instantiations have been declared."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML action goal request: invalid ROS declarations container."
        if not ros_declarations.is_action_client_defined(self._client_name):
            print("Error: SCXML action goal request: "
                  f"action client {self._client_name} not declared.")
            return False
        if not ros_declarations.check_valid_action_goal_fields(self._client_name, self._fields):
            print("Error: SCXML action goal request: invalid fields in request.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML action goal request: invalid ROS instantiations."
        automaton_name = ros_declarations.get_automaton_name()
        action_interface, _ = ros_declarations.get_action_client_info(self._client_name)
        event_name = generate_action_goal_req_event(action_interface, automaton_name)
        event_params = [field.as_plain_scxml(ros_declarations) for field in self._fields]
        return ScxmlSend(event_name, event_params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML action goal Request: invalid parameters."
        xml_goal_request = ET.Element(RosActionSendGoal.get_tag_name(), {
            "name": self._client_name})
        if self._fields is not None:
            for field in self._fields:
                xml_goal_request.append(field.as_xml())
        return xml_goal_request


class RosActionSendResult(ScxmlSend):
    """Object representing a ROS Action Goal (request, from the client side) in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_send_goal"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosActionSendGoal":
        """Create a RosActionSendGoal object from an XML tree."""
        assert_xml_tag_ok(RosActionSendGoal, xml_tree)
        action_name = get_xml_argument(RosActionSendGoal, xml_tree, "name")
        fields: List[RosField] = []
        for field_xml in xml_tree:
            fields.append(RosField.from_xml_tree(field_xml))
        return RosActionSendGoal(action_name, fields)

    def __init__(self, action_client: Union[str, RosActionClient],
                 fields: List[RosField] = None) -> None:
        """
        Initialize a new RosActionSendGoal object.

        :param action_client: The ActionClient object used by the sender, or its name.
        :param fields: List of fields to be sent in the goal request.
        """
        if isinstance(action_client, RosActionClient):
            self._client_name = action_client.get_name()
        else:
            assert is_non_empty_string(RosActionSendGoal, "name", action_client)
            self._client_name = action_client
        if fields is None:
            fields = []
        self._fields = fields
        assert self.check_validity(), "Error: SCXML Action Goal Request: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosActionSendGoal, "name", self._client_name)
        valid_fields = all([isinstance(field, RosField) and field.check_validity()
                            for field in self._fields])
        if not valid_fields:
            print("Error: SCXML service request: fields are not valid.")
        return valid_name and valid_fields

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ros instantiations have been declared."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML action goal request: invalid ROS declarations container."
        if not ros_declarations.is_action_client_defined(self._client_name):
            print("Error: SCXML action goal request: "
                  f"action client {self._client_name} not declared.")
            return False
        if not ros_declarations.check_valid_action_goal_fields(self._client_name, self._fields):
            print("Error: SCXML action goal request: invalid fields in request.")
            return False
        return True

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        assert self.check_valid_ros_instantiations(ros_declarations), \
            "Error: SCXML action goal request: invalid ROS instantiations."
        automaton_name = ros_declarations.get_automaton_name()
        action_interface, _ = ros_declarations.get_action_client_info(self._client_name)
        event_name = generate_action_goal_req_event(action_interface, automaton_name)
        event_params = [field.as_plain_scxml(ros_declarations) for field in self._fields]
        return ScxmlSend(event_name, event_params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML action goal Request: invalid parameters."
        xml_goal_request = ET.Element(RosActionSendGoal.get_tag_name(), {
            "name": self._client_name})
        if self._fields is not None:
            for field in self._fields:
                xml_goal_request.append(field.as_xml())
        return xml_goal_request
