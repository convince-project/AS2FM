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

from typing import Optional, Type, Union
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (
    ScxmlExecutionBody, ScxmlRosDeclarationsContainer, ScxmlTransition,
    as_plain_execution_body, execution_body_from_xml)
from scxml_converter.scxml_entries.scxml_ros_base import RosDeclaration, RosCallback

from scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from scxml_converter.scxml_entries.ros_utils import generate_rate_timer_event
from scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok, get_xml_argument
from scxml_converter.scxml_entries.utils import is_non_empty_string


class RosTimeRate(RosDeclaration):
    """Object used in the SCXML root to declare a new timer with its related tick rate."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_time_rate"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosTimeRate":
        """Create a RosTimeRate object from an XML tree."""
        assert_xml_tag_ok(RosTimeRate, xml_tree)
        timer_name = get_xml_argument(RosTimeRate, xml_tree, "name")
        timer_rate_str = get_xml_argument(RosTimeRate, xml_tree, "rate_hz")
        try:
            timer_rate = float(timer_rate_str)
        except ValueError as e:
            raise ValueError("Error: SCXML rate timer: rate is not a number.") from e
        return RosTimeRate(timer_name, timer_rate)

    def __init__(self, name: str, rate_hz: float):
        self._name = name
        self._rate_hz = float(rate_hz)

    def get_interface_name(self) -> str:
        raise RuntimeError("Error: SCXML rate timer: deleted method 'get_interface_name'.")

    def get_interface_type(self) -> str:
        raise RuntimeError("Error: SCXML rate timer: deleted method 'get_interface_type'.")

    def get_name(self) -> str:
        return self._name

    def get_rate(self) -> float:
        return self._rate_hz

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        """Update the values of potential entries making use of BT ports."""
        pass

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosTimeRate, "name", self._name)
        valid_rate = isinstance(self._rate_hz, float) and self._rate_hz > 0
        if not valid_rate:
            print("Error: SCXML rate timer: rate is not valid.")
        return valid_name and valid_rate

    def check_valid_instantiation(self) -> bool:
        """Check if the timer has undefined entries (i.e. from BT ports)."""
        return True

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML rate timer: invalid parameters."
        xml_time_rate = ET.Element(
            RosTimeRate.get_tag_name(), {"rate_hz": str(self._rate_hz), "name": self._name})
        return xml_time_rate


class RosRateCallback(RosCallback):
    """Callback that triggers each time the associated timer ticks."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_rate_callback"

    @staticmethod
    def get_declaration_type() -> Type[RosTimeRate]:
        return RosTimeRate

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosRateCallback":
        """Create a RosRateCallback object from an XML tree."""
        assert_xml_tag_ok(RosRateCallback, xml_tree)
        timer_name = get_xml_argument(RosRateCallback, xml_tree, "name")
        target = get_xml_argument(RosRateCallback, xml_tree, "target")
        condition = get_xml_argument(RosRateCallback, xml_tree, "cond", none_allowed=True)
        exec_body = execution_body_from_xml(xml_tree)
        return RosRateCallback(timer_name, target, condition, exec_body)

    def __init__(self, timer: Union[RosTimeRate, str], target: str, condition: Optional[str] = None,
                 body: Optional[ScxmlExecutionBody] = None):
        """
        Generate a new rate timer and callback.

        Multiple rate callbacks can share the same timer name, but the rate must match.

        :param timer: The RosTimeRate instance triggering the callback, or its name
        :param body: The body of the callback
        """
        self._condition = condition
        super().__init__(timer, target, body)

    def check_validity(self) -> bool:
        valid_parent = super().check_validity()
        valid_condition = self._condition is None or \
            is_non_empty_string(RosRateCallback, "cond", self._condition)
        return valid_parent and valid_condition

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_timer_defined(self._interface_name)

    def get_plain_scxml_event(self, ros_declarations: ScxmlRosDeclarationsContainer) -> str:
        return generate_rate_timer_event(self._interface_name)

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> ScxmlTransition:
        event_name = self.get_plain_scxml_event(ros_declarations)
        target = self._target
        cond = self._condition
        body = as_plain_execution_body(self._body, ros_declarations)
        return ScxmlTransition(target, [event_name], cond, body)

    def as_xml(self) -> ET.Element:
        xml_rate_callback = super().as_xml()
        if self._condition is not None:
            xml_rate_callback.set("cond", self._condition)
        return xml_rate_callback
