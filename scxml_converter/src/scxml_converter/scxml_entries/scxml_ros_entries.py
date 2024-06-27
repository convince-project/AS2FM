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

"""Declaration of ROS-Specific SCXML tags extensions."""

from typing import List, Optional, Union
from scxml_converter.scxml_entries import (ScxmlSend, ScxmlParam, ScxmlTransition,
                                           ScxmlExecutionBody, valid_execution_body)
from xml.etree import ElementTree as ET


def _check_topic_type_known(topic_definition: str) -> bool:
    """Check if python can import the provided topic definition."""
    # Check the input type has the expected structure
    if not (isinstance(topic_definition, str) and topic_definition.count("/") == 1):
        return False
    topic_ns, topic_type = topic_definition.split("/")
    if len(topic_ns) == 0 or len(topic_type) == 0:
        return False
    # TODO: Check we can import the requested msg
    return True


class RosTimeRate:
    """Object used in the SCXML root to declare a new timer with its related tick rate."""

    def __init__(self, name: str, rate_hz: float):
        self._name = name
        self._rate_hz = float(rate_hz)
        assert self.check_validity(), "Error: SCXML rate timer: invalid parameters."

    def get_tag_name() -> str:
        return "ros_time_rate"

    def from_xml_tree(xml_tree: ET.Element) -> "RosTimeRate":
        """Create a RosTimeRate object from an XML tree."""
        assert xml_tree.tag == RosTimeRate.get_tag_name(), \
            f"Error: SCXML rate timer: XML tag name is not {RosTimeRate.get_tag_name()}"
        timer_name = xml_tree.attrib.get("name")
        timer_rate = xml_tree.attrib.get("rate_hz")
        assert timer_name is not None and timer_rate is not None, \
            "Error: SCXML rate timer: 'name' or 'rate_hz' attribute not found in input xml."
        try:
            timer_rate = float(timer_rate)
        except ValueError:
            raise ValueError("Error: SCXML rate timer: rate is not a number.")
        return RosTimeRate(timer_name, timer_rate)

    def check_validity(self) -> bool:
        valid_name = isinstance(self._name, str) and len(self._name) > 0
        valid_rate = isinstance(self._rate_hz, float) and self._rate_hz > 0
        if not valid_name:
            print("Error: SCXML rate timer: name is not valid.")
        if not valid_rate:
            print("Error: SCXML rate timer: rate is not valid.")
        return valid_name and valid_rate

    def get_name(self) -> str:
        return self._name

    def get_rate(self) -> float:
        return self._rate_hz

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML rate timer: invalid parameters."
        xml_time_rate = ET.Element(
            RosTimeRate.get_tag_name(), {"rate_hz": str(self._rate_hz), "name": self._name})
        return xml_time_rate


class RosTopicPublisher:
    """Object used in SCXML root to declare a new topic publisher."""

    def __init__(self, topic_name: str, topic_type: str) -> None:
        self._topic_name = topic_name
        self._topic_type = topic_type
        assert self.check_validity(), "Error: SCXML topic publisher: invalid parameters."

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
        valid_type = _check_topic_type_known(self._topic_type)
        if not valid_name:
            print("Error: SCXML topic subscriber: topic name is not valid.")
        if not valid_type:
            print("Error: SCXML topic subscriber: topic type is not valid.")
        return valid_name and valid_type

    def get_topic_name(self) -> str:
        return self._topic_name

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic subscriber: invalid parameters."
        xml_topic_publisher = ET.Element(
            RosTopicPublisher.get_tag_name(), {"topic": self._topic_name, "type": self._topic_type})
        return xml_topic_publisher


class RosTopicSubscriber:
    """Object used in SCXML root to declare a new topic subscriber."""

    def __init__(self, topic_name: str, topic_type: str) -> None:
        self._topic_name = topic_name
        self._topic_type = topic_type
        assert self.check_validity(), "Error: SCXML topic subscriber: invalid parameters."

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
        valid_type = _check_topic_type_known(self._topic_type)
        if not valid_name:
            print("Error: SCXML topic subscriber: topic name is not valid.")
        if not valid_type:
            print("Error: SCXML topic subscriber: topic type is not valid.")
        return valid_name and valid_type

    def get_topic_name(self) -> str:
        return self._topic_name

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic subscriber: invalid parameters."
        xml_topic_subscriber = ET.Element(
            RosTopicSubscriber.get_tag_name(),
            {"topic": self._topic_name, "type": self._topic_type})
        return xml_topic_subscriber


class RosRateCallback(ScxmlTransition):
    """Callback that triggers each time the associated timer ticks."""

    def __init__(self, timer: RosTimeRate, target: str, body: Optional[ScxmlExecutionBody] = None):
        """
        Generate a new rate timer and callback.

        Multiple rate callbacks can share the same timer name, but the rate must match.

        :param timer_name: The name of the timer to use
        :param rate_hz: The rate in Hz associated to the timer
        :param target: The target state of the callback
        :param body: The body of the callback
        """
        self._timer_name = timer.get_name()
        self._target = target
        self._body = body
        assert self.check_validity(), "Error: SCXML rate callback: invalid parameters."

    def check_validity(self) -> bool:
        valid_timer = isinstance(self._timer_name, str) and len(self._timer_name) > 0
        valid_target = isinstance(self._target, str) and len(self._target) > 0
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_timer:
            print("Error: SCXML rate callback: timer name is not valid.")
        if not valid_target:
            print("Error: SCXML rate callback: target is not valid.")
        if not valid_body:
            print("Error: SCXML rate callback: body is not valid.")
        return valid_timer and valid_target and valid_body

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML rate callback: invalid parameters."
        xml_rate_callback = ET.Element(
            "ros_rate_callback", {"name": self._timer_name, "target": self._target})
        if self._body is not None:
            for entry in self._body:
                xml_rate_callback.append(entry.as_xml())
        return xml_rate_callback


class RosTopicCallback(ScxmlTransition):
    """Object representing a transition to perform when a new ROS msg is received."""

    def __init__(
            self, topic: RosTopicSubscriber, target: str,
            body: Optional[ScxmlExecutionBody] = None):
        self._topic = topic.get_topic_name()
        self._target = target
        self._body = body
        assert self.check_validity(), "Error: SCXML topic callback: invalid parameters."

    def check_validity(self) -> bool:
        valid_topic = isinstance(self._topic, str) and len(self._topic) > 0
        valid_target = isinstance(self._target, str) and len(self._target) > 0
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_topic:
            print("Error: SCXML topic callback: topic name is not valid.")
        if not valid_target:
            print("Error: SCXML topic callback: target is not valid.")
        if not valid_body:
            print("Error: SCXML topic callback: body is not valid.")
        return valid_topic and valid_target and valid_body

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic callback: invalid parameters."
        xml_topic_callback = ET.Element(
            "ros_topic_callback", {"topic": self._topic, "target": self._target})
        if self._body is not None:
            for entry in self._body:
                xml_topic_callback.append(entry.as_xml())
        return xml_topic_callback


class RosField(ScxmlParam):
    """Field of a ROS msg published in a topic."""

    def __init__(self, name: str, expr: str):
        self._name = name
        self._expr = expr
        assert self.check_validity(), "Error: SCXML topic publish field: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = isinstance(self._name, str) and len(self._name) > 0
        valid_expr = isinstance(self._expr, str) and len(self._expr) > 0
        if not valid_name:
            print("Error: SCXML topic publish field: name is not valid.")
        if not valid_expr:
            print("Error: SCXML topic publish field: expr is not valid.")
        return valid_name and valid_expr

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic publish field: invalid parameters."
        xml_field = ET.Element("field", {"name": self._name, "expr": self._expr})
        return xml_field


class RosTopicPublish(ScxmlSend):
    """Object representing the shipping of a ROS msg through a topic."""

    def __init__(self, topic: RosTopicPublisher, fields: Optional[List[RosField]] = None):
        self._topic = topic.get_topic_name()
        self._fields = fields
        assert self.check_validity(), "Error: SCXML topic publish: invalid parameters."

    def get_tag_name() -> str:
        return "ros_topic_publish"

    def check_validity(self) -> bool:
        valid_topic = isinstance(self._topic, str) and len(self._topic) > 0
        valid_fields = self._fields is None or \
            all([isinstance(field, RosField) for field in self._fields])
        if not valid_topic:
            print("Error: SCXML topic publish: topic name is not valid.")
        if not valid_fields:
            print("Error: SCXML topic publish: fields are not valid.")
        return valid_topic and valid_fields

    def append_param(self, param: ScxmlParam) -> None:
        raise NotImplementedError(
            "Error: SCXML topic publish: cannot append scxml params, use append_field instead.")

    def append_field(self, field: RosField) -> None:
        assert isinstance(field, RosField), "Error: SCXML topic publish: invalid field."
        if self._fields is None:
            self._fields = []
        self._fields.append(field)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic publish: invalid parameters."
        xml_topic_publish = ET.Element(RosTopicPublish.get_tag_name(), {"topic": self._topic})
        if self._fields is not None:
            for field in self._fields:
                xml_topic_publish.append(field.as_xml())
        return xml_topic_publish


ScxmlRosDeclarations = Union[RosTimeRate, RosTopicPublisher, RosTopicSubscriber]
