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

from typing import Optional
from scxml_converter.scxml_entries import (ScxmlSend, ScxmlParam, ScxmlTransition,
                                           ScxmlExecutionBody, valid_execution_body)
from xml.etree import ElementTree as ET


class RosTimeRate:
    """Declarative object used to define a new timer with its related tick rate."""

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
        pass


class RosTopicCallback(ScxmlTransition):
    # TODO
    pass


class ScxmlRosTopicPublish(ScxmlSend):
    # TODO
    pass


class ScxmlRosField(ScxmlParam):
    # TODO
    pass
