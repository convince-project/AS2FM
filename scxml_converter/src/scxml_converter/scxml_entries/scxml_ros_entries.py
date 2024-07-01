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
                                           ScxmlExecutionBody, valid_execution_body,
                                           execution_body_from_xml)
from xml.etree import ElementTree as ET


def _check_topic_type_known(topic_definition: str) -> bool:
    """Check if python can import the provided topic definition."""
    # Check the input type has the expected structure
    if not (isinstance(topic_definition, str) and topic_definition.count("/") == 1):
        return False
    topic_ns, topic_type = topic_definition.split("/")
    if len(topic_ns) == 0 or len(topic_type) == 0:
        return False
    try:
        _ = __import__(topic_ns + '.msg', fromlist=[topic_type])
    except ImportError:
        return False
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

    def __init__(self, timer: Union[RosTimeRate, str], target: str,
                 body: Optional[ScxmlExecutionBody] = None):
        """
        Generate a new rate timer and callback.

        Multiple rate callbacks can share the same timer name, but the rate must match.

        :param timer: The RosTimeRate instance triggering the callback, or its name
        :param body: The body of the callback
        """
        if isinstance(timer, RosTimeRate):
            self._timer_name = timer.get_name()
        else:
            # Used for generating ROS entries from xml file
            assert isinstance(timer, str), "Error: SCXML rate callback: invalid timer type."
            self._timer_name = timer
        self._target = target
        self._body = body
        assert self.check_validity(), "Error: SCXML rate callback: invalid parameters."

    def get_tag_name() -> str:
        return "ros_rate_callback"

    def from_xml_tree(xml_tree: ET.Element) -> ScxmlTransition:
        """Create a RosRateCallback object from an XML tree."""
        assert xml_tree.tag == RosRateCallback.get_tag_name(), \
            f"Error: SCXML rate callback: XML tag name is not {RosRateCallback.get_tag_name()}"
        timer_name = xml_tree.attrib.get("name")
        target = xml_tree.attrib.get("target")
        assert timer_name is not None and target is not None, \
            "Error: SCXML rate callback: 'name' or 'target' attribute not found in input xml."
        exec_body = execution_body_from_xml(xml_tree)
        exec_body = exec_body if exec_body is not None else None
        return RosRateCallback(timer_name, target, exec_body)

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
            self, topic: Union[RosTopicSubscriber, str], target: str,
            body: Optional[ScxmlExecutionBody] = None):
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
        self._body = body
        assert self.check_validity(), "Error: SCXML topic callback: invalid parameters."

    def get_tag_name() -> str:
        return "ros_topic_callback"

    def from_xml_tree(xml_tree: ET.Element) -> ScxmlTransition:
        """Create a RosTopicCallback object from an XML tree."""
        assert xml_tree.tag == RosTopicCallback.get_tag_name(), \
            f"Error: SCXML topic callback: XML tag name is not {RosTopicCallback.get_tag_name()}"
        topic_name = xml_tree.attrib.get("topic")
        target = xml_tree.attrib.get("target")
        assert topic_name is not None and target is not None, \
            "Error: SCXML topic callback: 'topic' or 'target' attribute not found in input xml."
        exec_body = execution_body_from_xml(xml_tree)
        exec_body = exec_body if exec_body is not None else None
        return RosTopicCallback(topic_name, target, exec_body)

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

    def get_tag_name() -> str:
        return "field"

    def from_xml_tree(xml_tree: ET.Element) -> "RosField":
        """Create a RosField object from an XML tree."""
        assert xml_tree.tag == RosField.get_tag_name(), \
            f"Error: SCXML topic publish field: XML tag name is not {RosField.get_tag_name()}"
        name = xml_tree.attrib.get("name")
        expr = xml_tree.attrib.get("expr")
        assert name is not None and expr is not None, \
            "Error: SCXML topic publish field: 'name' or 'expr' attribute not found in input xml."
        return RosField(name, expr)

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
        xml_field = ET.Element(RosField.get_tag_name(), {"name": self._name, "expr": self._expr})
        return xml_field


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

    def append_param(self, param: ScxmlParam) -> None:
        raise RuntimeError(
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
