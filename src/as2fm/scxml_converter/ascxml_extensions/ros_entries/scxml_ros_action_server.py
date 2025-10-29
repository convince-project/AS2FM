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

from typing import List, Type

from action_msgs.msg import GoalStatus

from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration
from as2fm.scxml_converter.ascxml_extensions.ros_entries import (
    RosCallback,
    RosDeclaration,
    RosTrigger,
)
from as2fm.scxml_converter.ascxml_extensions.ros_entries.ros_utils import (
    check_all_fields_known,
    generate_action_feedback_event,
    generate_action_goal_accepted_event,
    generate_action_goal_handle_event,
    generate_action_goal_rejected_event,
    generate_action_result_event,
    generate_action_thread_execution_start_event,
    generate_action_thread_free_event,
    get_action_type_params,
    is_action_type_known,
)
from as2fm.scxml_converter.scxml_entries import ScxmlBase, ScxmlParam, ScxmlSend
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import CallbackType


class RosActionServer(RosDeclaration):
    """Object used in SCXML root to declare a new action client."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_server"

    @staticmethod
    def get_communication_interface() -> str:
        return "action"

    def check_valid_interface_type(self) -> bool:
        if not is_action_type_known(self._interface_type):
            print(f"Error: SCXML RosActionServer: invalid action type {self._interface_type}.")
            return False
        return True


class RosActionHandleGoalRequest(RosCallback):
    """
    SCXML object representing the handler for a goal request.

    A server receives the request, containing the action goal fields and the goal_id.
    The goal_id is set from the action handler, based on the client.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_goal"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    @staticmethod
    def get_callback_type() -> CallbackType:
        return CallbackType.ROS_ACTION_GOAL

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionServer)
        return generate_action_goal_handle_event(ascxml_declaration.get_interface_name())


class RosActionAcceptGoal(RosTrigger):
    """
    Object representing the SCXML ROS Event sent from the server when an action Goal is accepted.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_accept_goal"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    @staticmethod
    def get_additional_arguments() -> List[str]:
        return ["goal_id"]

    def check_fields_validity(self, _) -> bool:
        return len(self._params) == 0

    def check_validity(self):
        return self.check_fields_validity(None) and super().check_validity()

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionServer)
        return generate_action_goal_accepted_event(ascxml_declaration.get_interface_name())


class RosActionRejectGoal(RosTrigger):
    """
    Object representing the SCXML ROS Event sent from the server when an action Goal is rejected.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_reject_goal"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    @staticmethod
    def get_additional_arguments() -> List[str]:
        return ["goal_id"]

    def check_fields_validity(self, _) -> bool:
        # When accepting the goal, we send only the goal_id of the accepted goal
        return len(self._params) == 0

    def check_validity(self):
        return self.check_fields_validity(None) and super().check_validity()

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionServer)
        return generate_action_goal_rejected_event(ascxml_declaration.get_interface_name())


class RosActionStartThread(RosTrigger):
    """
    Object representing the request, from an action server, to start a new execute thread instance.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_start_thread"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    @staticmethod
    def get_additional_arguments() -> List[str]:
        return ["goal_id", "thread_id"]

    def check_fields_validity(self, ascxml_declaration: AscxmlDeclaration) -> bool:
        """Check if the goal_id and the request fields have been defined."""
        assert isinstance(ascxml_declaration, RosActionServer)
        goal_fields = get_action_type_params(ascxml_declaration.get_interface_type())[0]
        return check_all_fields_known(self._params, goal_fields)

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionServer)
        return generate_action_thread_execution_start_event(ascxml_declaration.get_interface_name())


class RosActionSendFeedback(RosTrigger):
    """Object representing a ROS Action Goal (request, from the client side) in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_feedback"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    @staticmethod
    def get_additional_arguments() -> List[str]:
        return ["goal_id"]

    def check_fields_validity(self, ascxml_declaration: AscxmlDeclaration) -> bool:
        """Check if the goal_id and the request fields have been defined."""
        assert isinstance(ascxml_declaration, RosActionServer)
        feedback_fields = get_action_type_params(ascxml_declaration.get_interface_type())[1]
        return check_all_fields_known(self._params, feedback_fields)

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionServer)
        return generate_action_feedback_event(ascxml_declaration.get_interface_name())


class RosActionSendSuccessResult(RosTrigger):
    """Object representing a ROS Action Success Result in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_succeed"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    @staticmethod
    def get_additional_arguments() -> List[str]:
        return ["goal_id"]

    def check_fields_validity(self, ascxml_declaration: AscxmlDeclaration) -> bool:
        """Check if the goal_id and the request fields have been defined."""
        assert isinstance(ascxml_declaration, RosActionServer)
        result_fields = get_action_type_params(ascxml_declaration.get_interface_type())[2]
        return check_all_fields_known(self._params, result_fields)

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionServer)
        return generate_action_result_event(ascxml_declaration.get_interface_name())

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        plain_sends = super().as_plain_scxml(struct_declarations, ascxml_declarations, **kwargs)
        for p_send in plain_sends:
            assert isinstance(p_send, ScxmlSend)
            p_send.append_param(ScxmlParam("code", expr=f"{GoalStatus.STATUS_SUCCEEDED}"))
        return plain_sends


class RosActionSendCanceledResult(RosTrigger):
    """Object representing a ROS Action Canceled Result in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_canceled"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    @staticmethod
    def get_additional_arguments() -> List[str]:
        return ["goal_id"]

    def check_fields_validity(self, _) -> bool:
        """Check if the goal_id and the request fields have been defined."""
        return len(self._params) == 0

    def check_validity(self):
        return self.check_fields_validity(None) and super().check_validity()

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionServer)
        return generate_action_result_event(ascxml_declaration.get_interface_name())

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        plain_sends = super().as_plain_scxml(struct_declarations, ascxml_declarations, **kwargs)
        for p_send in plain_sends:
            assert isinstance(p_send, ScxmlSend)
            p_send.append_param(ScxmlParam("code", expr=f"{GoalStatus.STATUS_CANCELED}"))
        return plain_sends


class RosActionSendAbortedResult(RosTrigger):
    """Object representing a ROS Action Aborted Result in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_aborted"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    @staticmethod
    def get_additional_arguments() -> List[str]:
        return ["goal_id"]

    def check_fields_validity(self, _) -> bool:
        """Check if the goal_id and the request fields have been defined."""
        return len(self._params) == 0

    def check_validity(self):
        return self.check_fields_validity(None) and super().check_validity()

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionServer)
        return generate_action_result_event(ascxml_declaration.get_interface_name())

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        plain_sends = super().as_plain_scxml(struct_declarations, ascxml_declarations, **kwargs)
        for p_send in plain_sends:
            assert isinstance(p_send, ScxmlSend)
            p_send.append_param(ScxmlParam("code", expr=f"{GoalStatus.STATUS_ABORTED}"))
        return plain_sends


class RosActionHandleThreadFree(RosCallback):
    """
    Object representing the callback executed when an action thread report it is free.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_thread_free"

    @staticmethod
    def get_callback_type() -> CallbackType:
        # No ROS-specific fields are expected within this callback
        return CallbackType.TRANSITION

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    def get_plain_scxml_event(self, ascxml_declaration: AscxmlDeclaration) -> str:
        assert isinstance(ascxml_declaration, RosActionServer)
        return generate_action_thread_free_event(ascxml_declaration.get_interface_name())
