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

from typing import List, Union, Type
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (
    RosField, ScxmlSend, ScxmlParam, ScxmlRosDeclarationsContainer)

from scxml_converter.scxml_entries.scxml_ros_base import RosDeclaration, RosCallback, RosTrigger

from scxml_converter.scxml_entries.ros_utils import (
    is_action_type_known, generate_action_goal_handle_event,
    generate_action_goal_handle_accepted_event, generate_action_goal_handle_rejected_event,
    generate_action_thread_execution_start_event, generate_action_feedback_event,
    generate_action_result_event, generate_action_thread_free_event)
from scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok, get_xml_argument, get_children_as_scxml)


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

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_action_server_defined(self._interface_name)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_goal_handle_event(
            ros_declarations.get_action_server_info(self._interface_name)[0])


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

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_action_server_defined(self._interface_name)

    def check_fields_validity(self, _) -> bool:
        # When accepting the goal, we send only the goal_id of the accepted goal
        return len(self._fields) == 1 and self._fields[0].get_name() == "goal_id"

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_goal_handle_accepted_event(
            ros_declarations.get_action_server_info(self._interface_name)[0])

    def as_xml(self) -> ET.Element:
        assert self.check_fields_validity(None), "Error: SCXML RosActionAcceptGoal: invalid fields."
        return super().as_xml()


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

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_action_server_defined(self._interface_name)

    def check_fields_validity(self, _) -> bool:
        # When accepting the goal, we send only the goal_id of the accepted goal
        return len(self._fields) == 1 and self._fields[0].get_name() == "goal_id"

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_goal_handle_rejected_event(
            ros_declarations.get_action_server_info(self._interface_name)[0])

    def as_xml(self) -> ET.Element:
        assert self.check_fields_validity(None), "Error: SCXML RosActionRejectGoal: invalid fields."
        return super().as_xml()


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

    @classmethod
    def from_xml_tree(cls: Type[RosTrigger], xml_tree: ET.Element) -> "RosActionStartThread":
        """Create a RosActionStartThread object from an XML tree."""
        assert_xml_tag_ok(cls, xml_tree)
        action_name = get_xml_argument(cls, xml_tree, "name")
        thread_id = get_xml_argument(cls, xml_tree, "thread_id")
        fields: List[RosField] = get_children_as_scxml(xml_tree, (RosField,))
        return cls(action_name, thread_id, fields)

    def __init__(self, action_name: Union[str, RosActionServer], thread_id: str,
                 fields: List[RosField] = None) -> None:
        """
        Initialize a new RosActionStartThread object.

        :param action_name: The ActionServer object used by the sender, or its name.
        :param thread_id: The ID of the new thread instance.
        :param fields: List of fields to be sent in the goal request.
        """
        self._thread_id = thread_id
        super().__init__(action_name, fields)

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the action server has been declared."""
        return ros_declarations.is_action_server_defined(self._interface_name)

    def check_fields_validity(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the goal_id and the request fields have been defined."""
        if not ros_declarations.check_valid_action_goal_fields(self._interface_name, self._fields,
                                                               has_goal_id=True):
            print(f"Error: SCXML {self.__class__.__name__}: "
                  f"invalid fields in goal request {self._interface_name}.")
            return False
        return True

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_thread_execution_start_event(
            ros_declarations.get_action_server_info(self._interface_name)[0])

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlSend:
        plain_send = super().as_plain_scxml(ros_declarations)
        # Append the thread ID to the param list
        plain_send.append_param(ScxmlParam("thread_id", expr=self._thread_id))
        return plain_send

    def as_xml(self) -> ET.Element:
        xml_thread_start_req = super().as_xml()
        xml_thread_start_req.set("thread_id", self._thread_id)
        return xml_thread_start_req


class RosActionSendFeedback(RosTrigger):
    """Object representing a ROS Action Goal (request, from the client side) in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_feedback"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_action_server_defined(self._interface_name)

    def check_fields_validity(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the goal_id and the request fields have been defined."""
        if not ros_declarations.check_valid_action_feedback_fields(self._interface_name,
                                                                   self._fields, has_goal_id=True):
            print(f"Error: SCXML {self.__class__.__name__}: "
                  f"invalid fields in feedback request {self._interface_name}.")
            return False
        return True

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_feedback_event(
            ros_declarations.get_action_server_info(self._interface_name)[0])


class RosActionSendResult(RosTrigger):
    """Object representing a ROS Action Goal (request, from the client side) in SCXML."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_succeed"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_action_server_defined(self._interface_name)

    def check_fields_validity(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the goal_id and the request fields have been defined."""
        if not ros_declarations.check_valid_action_result_fields(self._interface_name,
                                                                 self._fields, has_goal_id=True):
            print(f"Error: SCXML {self.__class__.__name__}: "
                  f"invalid fields in result request {self._interface_name}.")
            return False
        return True

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_result_event(
            ros_declarations.get_action_server_info(self._interface_name)[0])


class RosActionHandleThreadFree(RosCallback):
    """
    Object representing the callback executed when an action thread report it is free.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "ros_action_handle_thread_free"

    @staticmethod
    def get_declaration_type() -> Type[RosActionServer]:
        return RosActionServer

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_action_server_defined(self._interface_name)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_action_thread_free_event(
            ros_declarations.get_action_server_info(self._interface_name)[0])
