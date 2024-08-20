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

from typing import List, Type
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (
    RosField, ScxmlRosDeclarationsContainer, ScxmlSend, BtGetValueInputPort,
    execution_body_from_xml)
from scxml_converter.scxml_entries.scxml_ros_base import RosCallback, RosTrigger, RosDeclaration

from scxml_converter.scxml_entries.ros_utils import (is_msg_type_known, generate_topic_event)
from scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok, get_xml_argument, get_children_as_scxml, read_value_from_xml_child)


class RosTopicPublisher(RosDeclaration):
    """Object used in SCXML root to declare a new topic publisher."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_topic_publisher"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosTopicPublisher":
        """Create a RosTopicPublisher object from an XML tree."""
        assert_xml_tag_ok(RosTopicPublisher, xml_tree)
        topic_name = get_xml_argument(RosTopicPublisher, xml_tree, "topic", none_allowed=True)
        topic_type = get_xml_argument(RosTopicPublisher, xml_tree, "type")
        pub_name = get_xml_argument(RosTopicPublisher, xml_tree, "name", none_allowed=True)
        if topic_name is None:
            topic_name = read_value_from_xml_child(xml_tree, "topic", (BtGetValueInputPort, str))
            assert topic_name is not None, "Error: SCXML topic publisher: topic name not found."
        return RosTopicPublisher(topic_name, topic_type, pub_name)

    def check_valid_interface_type(self) -> bool:
        if not is_msg_type_known(self._interface_type):
            print(f"Error: SCXML RosTopicPublisher: invalid msg type {self._interface_type}.")
            return False
        return True

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: RosTopicPublisher: invalid parameters."
        xml_topic_publisher = ET.Element(
            RosTopicPublisher.get_tag_name(),
            {"name": self._interface_alias,
             "topic": self._interface_name, "type": self._interface_type})
        return xml_topic_publisher


class RosTopicSubscriber(RosDeclaration):
    """Object used in SCXML root to declare a new topic subscriber."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_topic_subscriber"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosTopicSubscriber":
        """Create a RosTopicSubscriber object from an XML tree."""
        assert_xml_tag_ok(RosTopicSubscriber, xml_tree)
        topic_name = get_xml_argument(RosTopicSubscriber, xml_tree, "topic", none_allowed=True)
        topic_type = get_xml_argument(RosTopicSubscriber, xml_tree, "type")
        sub_name = get_xml_argument(RosTopicSubscriber, xml_tree, "name", none_allowed=True)
        if topic_name is None:
            topic_name = read_value_from_xml_child(xml_tree, "topic", (BtGetValueInputPort, str))
            assert topic_name is not None, "Error: SCXML topic subscriber: topic name not found."
        return RosTopicSubscriber(topic_name, topic_type, sub_name)

    def check_valid_interface_type(self) -> bool:
        if not is_msg_type_known(self._interface_type):
            print(f"Error: SCXML RosTopicSubscriber: invalid msg type {self._interface_type}.")
            return False
        return True

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML RosTopicSubscriber: invalid parameters."
        xml_topic_subscriber = ET.Element(
            RosTopicSubscriber.get_tag_name(),
            {"name": self._interface_alias,
             "topic": self._interface_name, "type": self._interface_type})
        return xml_topic_subscriber


class RosTopicCallback(RosCallback):
    """Object representing a transition to perform when a new ROS msg is received."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_topic_callback"

    @staticmethod
    def get_declaration_type() -> Type[RosTopicSubscriber]:
        return RosTopicSubscriber

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosTopicCallback":
        """Create a RosTopicCallback object from an XML tree."""
        assert_xml_tag_ok(RosTopicCallback, xml_tree)
        sub_name = get_xml_argument(RosTopicCallback, xml_tree, "name", none_allowed=True)
        if sub_name is None:
            sub_name = get_xml_argument(RosTopicCallback, xml_tree, "topic")
            print("Warning: SCXML topic callback: the 'topic' argument is deprecated. "
                  "Use 'name' instead.")
        target = get_xml_argument(RosTopicCallback, xml_tree, "target")
        exec_body = execution_body_from_xml(xml_tree)
        return RosTopicCallback(sub_name, target, exec_body)

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_subscriber_defined(self._interface_name)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_topic_event(ros_declarations.get_subscriber_info(self._interface_name)[0])

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic callback: invalid parameters."
        xml_topic_callback = ET.Element(RosTopicCallback.get_tag_name(),
                                        {"name": self._interface_name, "target": self._target})
        if self._body is not None:
            for entry in self._body:
                xml_topic_callback.append(entry.as_xml())
        return xml_topic_callback


class RosTopicPublish(RosTrigger):
    """Object representing the shipping of a ROS msg through a topic."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_topic_publish"

    @staticmethod
    def get_declaration_type() -> Type[RosTopicPublisher]:
        return RosTopicPublisher

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> ScxmlSend:
        """Create a RosTopicPublish object from an XML tree."""
        assert_xml_tag_ok(RosTopicPublish, xml_tree)
        pub_name = get_xml_argument(RosTopicPublish, xml_tree, "name", none_allowed=True)
        if pub_name is None:
            pub_name = get_xml_argument(RosTopicSubscriber, xml_tree, "topic")
            print("Warning: SCXML topic publisher: the 'topic' argument is deprecated. "
                  "Use 'name' instead.")
        fields: List[RosField] = get_children_as_scxml(xml_tree, (RosField,))
        return RosTopicPublish(pub_name, fields)

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_publisher_defined(self._interface_name)

    def check_fields_validity(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        # TODO: CHeck fields for topics, too
        return True

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_topic_event(ros_declarations.get_publisher_info(self._interface_name)[0])

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic publish: invalid parameters."
        xml_topic_publish = ET.Element(RosTopicPublish.get_tag_name(),
                                       {"name": self._interface_name})
        if self._fields is not None:
            for field in self._fields:
                xml_topic_publish.append(field.as_xml())
        return xml_topic_publish
