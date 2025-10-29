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

from as2fm.as2fm_common.logging import get_error_msg
from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration
from as2fm.scxml_converter.ascxml_extensions.ros_entries.ros_utils import (
    check_all_fields_known,
    generate_action_feedback_handle_event,
    generate_action_goal_handle_accepted_event,
    generate_action_goal_handle_rejected_event,
    generate_action_goal_req_event,
    generate_action_result_handle_event,
    get_action_type_params,
    is_action_type_known,
)
from as2fm.scxml_converter.ascxml_extensions.ros_entries.scxml_ros_base import (
    RosCallback,
    RosDeclaration,
    RosTrigger,
)
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import ScxmlBase, ScxmlTransition
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

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionClient)
        return generate_action_goal_req_event(
            ascxml_declaration.get_interface_name(),
            ascxml_declaration.get_node_name(),
        )

    def check_fields_validity(self, ascxml_declaration: AscxmlDeclaration) -> bool:
        assert isinstance(ascxml_declaration, RosActionClient)
        goal_fields = get_action_type_params(ascxml_declaration.get_interface_type())[0]
        return check_all_fields_known(self._params, goal_fields)


class RosActionHandleGoalResponse(RosCallback):
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
    def get_declaration_type(cls) -> Type[RosDeclaration]:
        """
        Get the type of ROS declaration related to the callback.

        Examples: RosSubscriber, RosPublisher, ...
        """
        return RosActionClient

    @classmethod
    def get_callback_type(cls):
        # This class has no children to process: this function is not expected to be used anywhere.
        RuntimeError("This method shouldn't be called for this class.")

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration):
        # This class generates two events: this is implemented in as_plain_scxml
        RuntimeError("This method shouldn't be called for this class.")

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, _: Dict[str, StructDefinition]
    ) -> "RosActionHandleGoalResponse":
        """Create a RosServiceServer object from an XML tree."""
        assert_xml_tag_ok(RosActionHandleGoalResponse, xml_tree)
        action_name = get_xml_attribute(RosActionHandleGoalResponse, xml_tree, "name")
        assert action_name is not None  # MyPy check
        accept_target = get_xml_attribute(RosActionHandleGoalResponse, xml_tree, "accept")
        assert accept_target is not None  # MyPy check
        reject_target = get_xml_attribute(RosActionHandleGoalResponse, xml_tree, "reject")
        assert reject_target is not None  # MyPy check
        assert len(xml_tree) == 0, get_error_msg(
            xml_tree,
            f"The tag {cls.get_tag_name()} cannot have any content "
            "(neither executable content nor probabilistic targets)",
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
        self._targets = []  # This is unused, but needs to be defined for the parent class
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

    def update_exec_body_configurable_values(self, ascxml_declarations: List[AscxmlDeclaration]):
        # No executable value expected
        pass

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        related_declaration = self.get_related_interface(ascxml_declarations)
        assert related_declaration is not None, get_error_msg(
            self.get_xml_origin(), "Cannot find related ROS declaration."
        )
        automaton_name = related_declaration.get_node_name()
        interface_name = related_declaration.get_interface_name()
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

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionClient)
        return generate_action_feedback_handle_event(
            ascxml_declaration.get_interface_name(),
            ascxml_declaration.get_node_name(),
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

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionClient)
        return generate_action_result_handle_event(
            ascxml_declaration.get_interface_name(),
            ascxml_declaration.get_node_name(),
        )

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        assert (
            self._condition is None
        ), "Error: SCXML RosActionHandleSuccessResult: condition not supported."
        self._condition = f"_wrapped_result.code == {GoalStatus.STATUS_SUCCEEDED}"
        return super().as_plain_scxml(struct_declarations, ascxml_declarations, **kwargs)


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

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionClient)
        return generate_action_result_handle_event(
            ascxml_declaration.get_interface_name(),
            ascxml_declaration.get_node_name(),
        )

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        assert (
            self._condition is None
        ), "Error: SCXML RosActionHandleSuccessResult: condition not supported."
        self._condition = f"_wrapped_result.code == {GoalStatus.STATUS_CANCELED}"
        return super().as_plain_scxml(struct_declarations, ascxml_declarations, **kwargs)


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

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionClient)
        return generate_action_result_handle_event(
            ascxml_declaration.get_interface_name(),
            ascxml_declaration.get_node_name(),
        )

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        assert (
            self._condition is None
        ), "Error: SCXML RosActionHandleSuccessResult: condition not supported."
        self._condition = f"_wrapped_result.code == {GoalStatus.STATUS_ABORTED}"
        return super().as_plain_scxml(struct_declarations, ascxml_declarations, **kwargs)
