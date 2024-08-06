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

"""Declaration of SCXML tags related to ROS Timers."""

from typing import Optional, Union
from scxml_converter.scxml_entries import (ScxmlBase, ScxmlTransition,
                                           ScxmlExecutionBody, ScxmlRosDeclarationsContainer,
                                           valid_execution_body, execution_body_from_xml,
                                           as_plain_execution_body)
from xml.etree import ElementTree as ET


class RosTimeRate(ScxmlBase):
    """Object used in the SCXML root to declare a new timer with its related tick rate."""

    def __init__(self, name: str, rate_hz: float):
        self._name = name
        self._rate_hz = float(rate_hz)

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

    def as_plain_scxml(self, _) -> ScxmlBase:
        # This is discarded in the as_plain_scxml method from ScxmlRoot
        raise RuntimeError("Error: SCXML ROS declarations cannot be converted to plain SCXML.")

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML rate timer: invalid parameters."
        xml_time_rate = ET.Element(
            RosTimeRate.get_tag_name(), {"rate_hz": str(self._rate_hz), "name": self._name})
        return xml_time_rate


class RosRateCallback(ScxmlTransition):
    """Callback that triggers each time the associated timer ticks."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_rate_callback"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosRateCallback":
        """Create a RosRateCallback object from an XML tree."""
        assert xml_tree.tag == RosRateCallback.get_tag_name(), \
            f"Error: SCXML rate callback: XML tag name is not {RosRateCallback.get_tag_name()}"
        timer_name = xml_tree.attrib.get("name")
        target = xml_tree.attrib.get("target")
        assert timer_name is not None and target is not None, \
            "Error: SCXML rate callback: 'name' or 'target' attribute not found in input xml."
        condition = xml_tree.get("cond")
        condition = condition if condition is not None and len(condition) > 0 else None
        exec_body = execution_body_from_xml(xml_tree)
        exec_body = exec_body if exec_body is not None else None
        return RosRateCallback(timer_name, target, condition, exec_body)

    def __init__(self, timer: Union[RosTimeRate, str], target: str, condition: Optional[str] = None,
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
        self._condition = condition
        self._body = body
        assert self.check_validity(), "Error: SCXML rate callback: invalid parameters."

    def check_validity(self) -> bool:
        valid_timer = isinstance(self._timer_name, str) and len(self._timer_name) > 0
        valid_target = isinstance(self._target, str) and len(self._target) > 0
        valid_cond = self._condition is None or (
            isinstance(self._condition, str) and len(self._condition) > 0)
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_timer:
            print("Error: SCXML rate callback: timer name is not valid.")
        if not valid_target:
            print("Error: SCXML rate callback: target is not valid.")
        if not valid_cond:
            print("Error: SCXML rate callback: condition is not valid.")
        if not valid_body:
            print("Error: SCXML rate callback: body is not valid.")
        return valid_timer and valid_target and valid_cond and valid_body

    def check_valid_ros_instantiations(self,
                                       ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        """Check if the ros instantiations have been declared."""
        assert isinstance(ros_declarations, ScxmlRosDeclarationsContainer), \
            "Error: SCXML rate callback: invalid ROS declarations container."
        timer_cb_declared = ros_declarations.is_timer_defined(self._timer_name)
        if not timer_cb_declared:
            print(f"Error: SCXML rate callback: timer {self._timer_name} not declared.")
            return False
        valid_body = super().check_valid_ros_instantiations(ros_declarations)
        if not valid_body:
            print("Error: SCXML rate callback: body has invalid ROS instantiations.")
        return valid_body

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        event_name = "ros_time_rate." + self._timer_name
        target = self._target
        cond = self._condition
        body = as_plain_execution_body(self._body, ros_declarations)
        return ScxmlTransition(target, [event_name], cond, body)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML rate callback: invalid parameters."
        xml_rate_callback = ET.Element(
            "ros_rate_callback", {"name": self._timer_name, "target": self._target})
        if self._condition is not None:
            xml_rate_callback.set("cond", self._condition)
        if self._body is not None:
            for entry in self._body:
                xml_rate_callback.append(entry.as_xml())
        return xml_rate_callback
