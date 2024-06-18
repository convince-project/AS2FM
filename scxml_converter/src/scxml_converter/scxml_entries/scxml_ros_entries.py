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

from typing import Optional, Union
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
        self._rate_hz = rate_hz
        assert self.check_validity(), "Error: SCXML rate timer: invalid parameters."

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
            "ros_time_rate", {"rate_hz": str(self._rate_hz), "name": self._name})
        return xml_time_rate


class RosTopicPublisher:
    """Object used in SCXML root to declare a new topic publisher."""
    def __init__(self, topic_name: str, topic_type: str) -> None:
        pass


class RosTopicSubscriber:
    """Object used in SCXML root to declare a new topic subscriber."""
    def __init__(self, topic_name: str, topic_type: str) -> None:
        self._topic_name = topic_name
        self._topic_type = topic_type
        assert self.check_validity(), "Error: SCXML topic subscriber: invalid parameters."

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
            "ros_topic_subscriber", {"topic": self._topic_name, "type": self._topic_type})
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


class RosTopicPublish(ScxmlSend):
    # TODO
    pass


class RosField(ScxmlParam):
    # TODO
    pass


ScxmlRosDeclarations = Union[RosTimeRate, RosTopicPublisher, RosTopicSubscriber]
