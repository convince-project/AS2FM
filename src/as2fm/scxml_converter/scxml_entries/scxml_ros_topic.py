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
Declaration of SCXML tags related to ROS Topics.

Additional information:
https://docs.ros.org/en/iron/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.html
"""

from typing import Type

from as2fm.scxml_converter.scxml_entries import ScxmlRosDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.ros_utils import generate_topic_event, is_msg_type_known
from as2fm.scxml_converter.scxml_entries.scxml_ros_base import (
    RosCallback,
    RosDeclaration,
    RosTrigger,
)
from as2fm.scxml_converter.scxml_entries.utils import CallbackType


class RosTopicPublisher(RosDeclaration):
    """Object used in SCXML root to declare a new topic publisher."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_topic_publisher"

    @staticmethod
    def get_xml_arg_interface_name() -> str:
        return "topic"

    def check_valid_interface_type(self) -> bool:
        if not is_msg_type_known(self._interface_type):
            print(f"Error: SCXML RosTopicPublisher: invalid msg type {self._interface_type}.")
            return False
        return True


class RosTopicSubscriber(RosDeclaration):
    """Object used in SCXML root to declare a new topic subscriber."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_topic_subscriber"

    @staticmethod
    def get_xml_arg_interface_name() -> str:
        return "topic"

    def check_valid_interface_type(self) -> bool:
        if not is_msg_type_known(self._interface_type):
            print(f"Error: SCXML RosTopicSubscriber: invalid msg type {self._interface_type}.")
            return False
        return True


class RosTopicCallback(RosCallback):
    """Object representing a transition to perform when a new ROS msg is received."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_topic_callback"

    @staticmethod
    def get_declaration_type() -> Type[RosTopicSubscriber]:
        return RosTopicSubscriber

    @staticmethod
    def get_callback_type() -> CallbackType:
        return CallbackType.ROS_TOPIC

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_subscriber_defined(self._interface_name)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_topic_event(ros_declarations.get_subscriber_info(self._interface_name)[0])


class RosTopicPublish(RosTrigger):
    """Object representing the shipping of a ROS msg through a topic."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_topic_publish"

    @staticmethod
    def get_declaration_type() -> Type[RosTopicPublisher]:
        return RosTopicPublisher

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_publisher_defined(self._interface_name)

    def check_fields_validity(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        # TODO: CHeck fields for topics, too
        return True

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_topic_event(ros_declarations.get_publisher_info(self._interface_name)[0])
