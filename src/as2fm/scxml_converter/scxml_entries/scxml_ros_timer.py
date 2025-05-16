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

from typing import Dict, Type

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.scxml_converter.data_types.xml_struct_definition import XmlStructDefinition
from as2fm.scxml_converter.scxml_entries import ScxmlRosDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from as2fm.scxml_converter.scxml_entries.ros_utils import generate_rate_timer_event
from as2fm.scxml_converter.scxml_entries.scxml_ros_base import RosCallback, RosDeclaration
from as2fm.scxml_converter.scxml_entries.utils import CallbackType, is_non_empty_string
from as2fm.scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok, get_xml_attribute


class RosTimeRate(RosDeclaration):
    """Object used in the SCXML root to declare a new timer with its related tick rate."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_time_rate"

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, _: Dict[str, XmlStructDefinition]
    ) -> "RosTimeRate":
        """Create a RosTimeRate object from an XML tree."""
        assert_xml_tag_ok(RosTimeRate, xml_tree)
        timer_name = get_xml_attribute(RosTimeRate, xml_tree, "name")
        timer_rate_str = get_xml_attribute(RosTimeRate, xml_tree, "rate_hz")
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

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "Error: SCXML rate timer: invalid parameters."
        xml_time_rate = ET.Element(
            RosTimeRate.get_tag_name(), {"rate_hz": str(self._rate_hz), "name": self._name}
        )
        return xml_time_rate


class RosRateCallback(RosCallback):
    """Callback that triggers each time the associated timer ticks."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_rate_callback"

    @staticmethod
    def get_callback_type() -> CallbackType:
        return CallbackType.ROS_TIMER

    @staticmethod
    def get_declaration_type() -> Type[RosTimeRate]:
        return RosTimeRate

    def check_interface_defined(self, ros_declarations: ScxmlRosDeclarationsContainer) -> bool:
        return ros_declarations.is_timer_defined(self._interface_name)

    def get_plain_scxml_event(self, _) -> str:
        return generate_rate_timer_event(self._interface_name)
