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

from typing import List, Optional, Union
from scxml_converter.scxml_entries import (RosField, ScxmlBase, ScxmlSend, ScxmlParam, 
                                           ScxmlTransition, ScxmlExecutionBody, 
                                           ScxmlRosDeclarationsContainer,
                                           valid_execution_body, execution_body_from_xml,
                                           as_plain_execution_body)
from xml.etree import ElementTree as ET
from scxml_converter.scxml_entries.utils import is_msg_type_known


class RosTopicPublisher(ScxmlBase):
    """Object used in SCXML root to declare a new topic publisher."""

    def __init__(self, topic_name: str, topic_type: str) -> None:
        self._topic_name = topic_name
        self._topic_type = topic_type

    def get_tag_name() -> str:
        return "ros_topic_publisher"

    def from_xml_tree(xml_tree: ET.Element) -> "RosTopicPublisher":
        """Create a RosTopicPublisher object from an XML tree."""
        assert xml_tree.tag == RosTopicPublisher.get_tag_name(), \
            f"Error: SCXML topic publisher: XML tag name is not {RosTopicPublisher.get_tag_name()}"
        topic_name = xml_tree.attrib.get("topic")
        topic_type = xml_tree.attrib.get("type")
        assert topic_name is not None and topic_type is not None, \
            "Error: SCXML topic publisher: 'topic' or 'type' attribute not found in input xml."
        return RosTopicPublisher(topic_name, topic_type)

    def check_validity(self) -> bool:
        valid_name = isinstance(self._topic_name, str) and len(self._topic_name) > 0
        valid_type = is_msg_type_known(self._topic_type)
        if not valid_name:
            print("Error: SCXML topic subscriber: topic name is not valid.")
        if not valid_type:
            print("Error: SCXML topic subscriber: topic type is not valid.")
        return valid_name and valid_type

    def get_topic_name(self) -> str:
        return self._topic_name

    def get_topic_type(self) -> str:
        return self._topic_type

    def as_plain_scxml(self, _) -> ScxmlBase:
        # This is discarded in the as_plain_scxml method from ScxmlRoot
        raise RuntimeError("Error: SCXML ROS declarations cannot be converted to plain SCXML.")

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic subscriber: invalid parameters."
        xml_topic_publisher = ET.Element(
            RosTopicPublisher.get_tag_name(), {"topic": self._topic_name, "type": self._topic_type})
        return xml_topic_publisher


class RosTopicSubscriber(ScxmlBase):
    """Object used in SCXML root to declare a new topic subscriber."""

    def __init__(self, topic_name: str, topic_type: str) -> None:
        self._topic_name = topic_name
        self._topic_type = topic_type

    def get_tag_name() -> str:
        return "ros_topic_subscriber"

    def from_xml_tree(xml_tree: ET.Element) -> "RosTopicSubscriber":
        """Create a RosTopicSubscriber object from an XML tree."""
        assert xml_tree.tag == RosTopicSubscriber.get_tag_name(), \
            f"Error: SCXML topic subscribe: XML tag name is not {RosTopicSubscriber.get_tag_name()}"
        topic_name = xml_tree.attrib.get("topic")
        topic_type = xml_tree.attrib.get("type")
        assert topic_name is not None and topic_type is not None, \
            "Error: SCXML topic subscriber: 'topic' or 'type' attribute not found in input xml."
        return RosTopicSubscriber(topic_name, topic_type)

    def check_validity(self) -> bool:
        valid_name = isinstance(self._topic_name, str) and len(self._topic_name) > 0
        valid_type = is_msg_type_known(self._topic_type)
        if not valid_name:
            print("Error: SCXML topic subscriber: topic name is not valid.")
        if not valid_type:
            print("Error: SCXML topic subscriber: topic type is not valid.")
        return valid_name and valid_type

    def get_topic_name(self) -> str:
        return self._topic_name

    def get_topic_type(self) -> str:
        return self._topic_type

    def as_plain_scxml(self, _) -> ScxmlBase:
        # This is discarded in the as_plain_scxml method from ScxmlRoot
        raise RuntimeError("Error: SCXML ROS declarations cannot be converted to plain SCXML.")

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic subscriber: invalid parameters."
        xml_topic_subscriber = ET.Element(
            RosTopicSubscriber.get_tag_name(),
            {"topic": self._topic_name, "type": self._topic_type})
        return xml_topic_subscriber


class RosTopicCallback(ScxmlTransition):
    """Object representing a transition to perform when a new ROS msg is received."""

    def __init__(
            self, topic: Union[RosTopicSubscriber, str], target: str,
            condition: Optional[str] = None, body: Optional[ScxmlExecutionBody] = None):
        """
        Create a new ros_topic_callback object  instance.

        :param topic: The RosTopicSubscriber instance triggering the callback, or its name
        :param target: The target state of the transition
        :param body: Execution body executed at the time the received message gets processed
        """
        if isinstance(topic, RosTopicSubscriber):
            self._topic = topic.get_topic_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(topic, str), "Error: SCXML topic callback: invalid topic type."
            self._topic = topic
        self._target = target
        self._condition = condition
        self._body = body
        assert self.check_validity(), "Error: SCXML topic callback: invalid parameters."

    def get_tag_name() -> str:
        return "ros_topic_callback"

    def from_xml_tree(xml_tree: ET.Element) -> "RosTopicCallback":
        """Create a RosTopicCallback object from an XML tree."""
        assert xml_tree.tag == RosTopicCallback.get_tag_name(), \
            f"Error: SCXML topic callback: XML tag name is not {RosTopicCallback.get_tag_name()}"
        topic_name = xml_tree.attrib.get("topic")
        target = xml_tree.attrib.get("target")
        assert topic_name is not None and target is not None, \
            "Error: SCXML topic callback: 'topic' or 'target' attribute not found in input xml."
        condition = xml_tree.get("cond")
        condition = condition if condition is not None and len(condition) > 0 else None
        exec_body = execution_body_from_xml(xml_tree)
        exec_body = exec_body if exec_body is not None else None
        return RosTopicCallback(topic_name, target, condition, exec_body)

    def check_validity(self) -> bool:
        valid_topic = isinstance(self._topic, str) and len(self._topic) > 0
        valid_target = isinstance(self._target, str) and len(self._target) > 0
        valid_cond = self._condition is None or (
            isinstance(self._condition, str) and len(self._condition) > 0)
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_topic:
            print("Error: SCXML topic callback: topic name is not valid.")
        if not valid_target:
            print("Error: SCXML topic callback: target is not valid.")
        if not valid_cond:
            print("Error: SCXML topic callback: condition is not valid.")
        if not valid_body:
            print("Error: SCXML topic callback: body is not valid.")
        return valid_topic and valid_target and valid_cond and valid_body

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ros instantiations have been declared."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML topic callback: invalid ROS declarations container."
        topic_cb_declared = ros_declarations.is_subscriber_defined(self._topic)
        if not topic_cb_declared:
            print(f"Error: SCXML topic callback: topic subscriber {self._topic} not declared.")
            return False
        valid_body = self._check_valid_ros_instantiations_exec_body(ros_declarations)
        if not valid_body:
            print("Error: SCXML topic callback: body has invalid ROS instantiations.")
        return valid_body

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        event_name = "ros_topic." + self._topic
        target = self._target
        cond = self._condition
        body = as_plain_execution_body(self._body, ros_declarations)
        return ScxmlTransition(target, [event_name], cond, body)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic callback: invalid parameters."
        xml_topic_callback = ET.Element(
            "ros_topic_callback", {"topic": self._topic, "target": self._target})
        if self._condition is not None:
            xml_topic_callback.set("cond", self._condition)
        if self._body is not None:
            for entry in self._body:
                xml_topic_callback.append(entry.as_xml())
        return xml_topic_callback


class RosTopicPublish(ScxmlSend):
    """Object representing the shipping of a ROS msg through a topic."""

    def __init__(self, topic: Union[RosTopicPublisher, str],
                 fields: Optional[List[RosField]] = None):
        if isinstance(topic, RosTopicPublisher):
            self._topic = topic.get_topic_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(topic, str), "Error: SCXML topic publish: invalid topic type."
            self._topic = topic
        self._fields = fields
        assert self.check_validity(), "Error: SCXML topic publish: invalid parameters."

    def get_tag_name() -> str:
        return "ros_topic_publish"

    def from_xml_tree(xml_tree: ET.Element) -> ScxmlSend:
        """Create a RosTopicPublish object from an XML tree."""
        assert xml_tree.tag == RosTopicPublish.get_tag_name(), \
            f"Error: SCXML topic publish: XML tag name is not {RosTopicPublish.get_tag_name()}"
        topic_name = xml_tree.attrib.get("topic")
        assert topic_name is not None, \
            "Error: SCXML topic publish: 'topic' attribute not found in input xml."
        fields = []
        for field_xml in xml_tree:
            fields.append(RosField.from_xml_tree(field_xml))
        if len(fields) == 0:
            fields = None
        return RosTopicPublish(topic_name, fields)

    def check_validity(self) -> bool:
        valid_topic = isinstance(self._topic, str) and len(self._topic) > 0
        valid_fields = self._fields is None or \
            all([isinstance(field, RosField) for field in self._fields])
        if not valid_topic:
            print("Error: SCXML topic publish: topic name is not valid.")
        if not valid_fields:
            print("Error: SCXML topic publish: fields are not valid.")
        return valid_topic and valid_fields

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ros instantiations have been declared."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML topic publish: invalid ROS declarations container."
        topic_pub_declared = ros_declarations.is_publisher_defined(self._topic)
        if not topic_pub_declared:
            print(f"Error: SCXML topic publish: topic {self._topic} not declared.")
        # TODO: Check for valid fields can be done here
        return topic_pub_declared

    def append_param(self, param: ScxmlParam) -> None:
        raise RuntimeError(
            "Error: SCXML topic publish: cannot append scxml params, use append_field instead.")

    def append_field(self, field: RosField) -> None:
        assert isinstance(field, RosField), "Error: SCXML topic publish: invalid field."
        if self._fields is None:
            self._fields = []
        self._fields.append(field)

    def as_plain_scxml(self, _) -> ScxmlSend:
        event_name = "ros_topic." + self._topic
        params = None if self._fields is None else \
            [field.as_plain_scxml() for field in self._fields]
        return ScxmlSend(event_name, params)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic publish: invalid parameters."
        xml_topic_publish = ET.Element(RosTopicPublish.get_tag_name(), {"topic": self._topic})
        if self._fields is not None:
            for field in self._fields:
                xml_topic_publish.append(field.as_xml())
        return xml_topic_publish
