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

from typing import Dict, List, Type, Union

from action_msgs.msg import GoalStatus
from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import ScxmlRosDeclarationsContainer, ScxmlTransition
from as2fm.scxml_converter.scxml_entries.ros_utils import (
    generate_action_feedback_handle_event,
    generate_action_goal_handle_accepted_event,
    generate_action_goal_handle_rejected_event,
    generate_action_goal_req_event,
    generate_action_result_handle_event,
    is_action_type_known,
)
from as2fm.scxml_converter.scxml_entries.scxml_ros_base import (
    RosCallback,
    RosDeclaration,
    RosTrigger,
)
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import CallbackType, is_non_empty_string
from as2fm.scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok, get_xml_attribute


class RosActionClient(RosDeclaration):
    """Object used in SCXML root to declare a new action client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_client"

    @staticmethod
    def get_communication_interface() -> str:
        return "action"

    def check_valid_interface_type(self) -> bool:
        if not is_action_type_known(self._interface_type):
            print(f"Error: SCXML RosActionClient: invalid action type {self._interface_type}.")
            return False
        return True


class RosActionSendGoal(RosTrigger):
    """Object representing a ROS Action Goal (request, from the client side) in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_send_goal"

    @staticmethod
    def get_declaration_type() -> Type[RosActionClient]:
        return RosActionClient

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_action_client_defined(self._interface_name)

    def check_fields_validity(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.check_valid_action_goal_fields(self._interface_name, self._fields)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_goal_req_event(
            ros_declarations.get_action_client_info(self._interface_name)[0],
            ros_declarations.get_automaton_name(),
        )


class RosActionHandleGoalResponse(ScxmlTransition):
    """
    SCXML object representing the handler of an action response upon a goal request.

    A server might accept or refuse a goal request, based on its internal state.
    This handler is meant to handle both acceptance or refusal of a request.
    Translating this to plain-SCXML, it results to two conditional transitions.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_goal_response"

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, _: Dict[str, StructDefinition]
    ) -> "RosActionHandleGoalResponse":
        """Create a RosServiceServer object from an XML tree."""
        assert_xml_tag_ok(RosActionHandleGoalResponse, xml_tree)
        action_name = get_xml_attribute(RosActionHandleGoalResponse, xml_tree, "name")
        accept_target = get_xml_attribute(RosActionHandleGoalResponse, xml_tree, "accept")
        reject_target = get_xml_attribute(RosActionHandleGoalResponse, xml_tree, "reject")
        assert len(xml_tree) == 0, (
            "Error: SCXML RosActionHandleGoalResponse can not have any children. "
            "(Neither executable content nor probabilistic targets)"
        )
        return RosActionHandleGoalResponse(action_name, accept_target, reject_target)

    def __init__(
        self, action_client: Union[str, RosActionClient], accept_target: str, reject_target: str
    ) -> None:
        """
        Initialize a new RosActionHandleGoalResponse object.

        :param action_client: Action client used by this handler, or its name.
        :param accept_target: State to transition to, in case of goal acceptance.
        :param reject_target: State to transition to, in case of goal refusal.
        """
        if isinstance(action_client, RosActionClient):
            self._client_name = action_client.get_name()
        else:
            assert is_non_empty_string(RosActionHandleGoalResponse, "name", action_client)
            self._client_name = action_client
        self._accept_target = accept_target
        self._reject_target = reject_target
        assert self.check_validity(), "Error: SCXML RosActionHandleGoalResponse: invalid params."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosActionHandleGoalResponse, "name", self._client_name)
        valid_accept = is_non_empty_string(
            RosActionHandleGoalResponse, "accept", self._accept_target
        )
        valid_reject = is_non_empty_string(
            RosActionHandleGoalResponse, "reject", self._reject_target
        )
        return valid_name and valid_accept and valid_reject

    def instantiate_bt_events(self, _, __) -> List["RosActionHandleGoalResponse"]:
        # We do not expect a body with BT events requiring substitutions
        return [self]

    def update_bt_ports_values(self, _) -> None:
        """Update the values of potential entries making use of BT ports."""
        # We do not expect a body with BT ports to be substituted
        pass

    def has_bt_blackboard_input(self, _) -> bool:
        """This can not have a body, so it can not have BT blackboard input."""
        return False

    def check_valid_ros_instantiations(
        self, ros_declarations: ScxmlRosDeclarationsContainer
    ) -> bool:
        assert isinstance(
            ros_declarations, ScxmlRosDeclarationsContainer
        ), "Error: SCXML Service Handle Response: invalid ROS declarations container."
        assert isinstance(
            ros_declarations, ScxmlRosDeclarationsContainer
        ), "Error: SCXML action goal request: invalid ROS declarations container."
        if not ros_declarations.is_action_client_defined(self._client_name):
            print(
                "Error: SCXML action goal request: "
                f"action client {self._client_name} not declared."
            )
            return False
        return True

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ros_declarations: List[AscxmlDeclaration],
    ) -> List[ScxmlTransition]:
        assert self.check_valid_ros_instantiations(
            ros_declarations
        ), "Error: SCXML service response handler: invalid ROS instantiations."
        automaton_name = ros_declarations.get_automaton_name()
        interface_name, _ = ros_declarations.get_action_client_info(self._client_name)
        accept_event = generate_action_goal_handle_accepted_event(interface_name, automaton_name)
        reject_event = generate_action_goal_handle_rejected_event(interface_name, automaton_name)
        accept_transition = ScxmlTransition.make_single_target_transition(
            self._accept_target, [accept_event]
        )
        reject_transition = ScxmlTransition.make_single_target_transition(
            self._reject_target, [reject_event]
        )
        return [accept_transition, reject_transition]

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "Error: SCXML Service Handle Response: invalid parameters."
        return ET.Element(
            RosActionHandleGoalResponse.get_tag_name(),
            {
                "name": self._client_name,
                "accept": self._accept_target,
                "reject": self._reject_target,
            },
        )


class RosActionHandleFeedback(RosCallback):
    """SCXML object representing the handler of an action feedback."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_feedback"

    @staticmethod
    def get_declaration_type() -> Type[RosActionClient]:
        return RosActionClient

    @staticmethod
    def get_callback_type() -> CallbackType:
        return CallbackType.ROS_ACTION_FEEDBACK

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_action_client_defined(self._interface_name)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_feedback_handle_event(
            ros_declarations.get_action_client_info(self._interface_name)[0],
            ros_declarations.get_automaton_name(),
        )


class RosActionHandleSuccessResult(RosCallback):
    """SCXML object representing the handler of am action result for a service client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_success_result"

    @staticmethod
    def get_declaration_type() -> Type[RosActionClient]:
        return RosActionClient

    @staticmethod
    def get_callback_type() -> CallbackType:
        return CallbackType.ROS_ACTION_RESULT

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_action_client_defined(self._interface_name)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_result_handle_event(
            ros_declarations.get_action_client_info(self._interface_name)[0],
            ros_declarations.get_automaton_name(),
        )

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ros_declarations: ScxmlRosDeclarationsContainer,
    ) -> List[ScxmlTransition]:
        assert (
            self._condition is None
        ), "Error: SCXML RosActionHandleSuccessResult: condition not supported."
        self._condition = f"_wrapped_result.code == {GoalStatus.STATUS_SUCCEEDED}"
        return super().as_plain_scxml(struct_declarations, ros_declarations)


class RosActionHandleCanceledResult(RosCallback):
    """SCXML object representing the handler of am action result for a service client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_canceled_result"

    @staticmethod
    def get_declaration_type() -> Type[RosActionClient]:
        return RosActionClient

    @staticmethod
    def get_callback_type() -> CallbackType:
        return CallbackType.ROS_ACTION_RESULT

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_action_client_defined(self._interface_name)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_result_handle_event(
            ros_declarations.get_action_client_info(self._interface_name)[0],
            ros_declarations.get_automaton_name(),
        )

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ros_declarations: ScxmlRosDeclarationsContainer,
    ) -> List[ScxmlTransition]:
        assert (
            self._condition is None
        ), "Error: SCXML RosActionHandleSuccessResult: condition not supported."
        self._condition = f"_wrapped_result.code == {GoalStatus.STATUS_CANCELED}"
        return super().as_plain_scxml(struct_declarations, ros_declarations)


class RosActionHandleAbortedResult(RosCallback):
    """SCXML object representing the handler of am action result for a service client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_aborted_result"

    @staticmethod
    def get_declaration_type() -> Type[RosActionClient]:
        return RosActionClient

    @staticmethod
    def get_callback_type() -> CallbackType:
        return CallbackType.ROS_ACTION_RESULT

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_action_client_defined(self._interface_name)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_result_handle_event(
            ros_declarations.get_action_client_info(self._interface_name)[0],
            ros_declarations.get_automaton_name(),
        )

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ros_declarations: ScxmlRosDeclarationsContainer,
    ) -> List[ScxmlTransition]:
        assert (
            self._condition is None
        ), "Error: SCXML RosActionHandleSuccessResult: condition not supported."
        self._condition = f"_wrapped_result.code == {GoalStatus.STATUS_ABORTED}"
        return super().as_plain_scxml(struct_declarations, ros_declarations)
