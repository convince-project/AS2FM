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

from typing import Dict, List, Type, Union

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.logging import get_error_msg
from as2fm.scxml_converter.ascxml_extensions import AscxmlConfiguration, AscxmlDeclaration
from as2fm.scxml_converter.ascxml_extensions.ros_entries import RosCallback, RosDeclaration
from as2fm.scxml_converter.ascxml_extensions.ros_entries.ros_utils import generate_rate_timer_event
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries.utils import CallbackType, is_non_empty_string
from as2fm.scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok,
    get_xml_attribute,
    read_value_from_xml_arg_or_child,
)


class RosTimeRate(RosDeclaration):
    """Object used in the SCXML root to declare a new timer with its related tick rate."""

    @staticmethod
    def get_tag_name() -> str:
        return "ros_time_rate"

    @classmethod
    def get_communication_interface(cls):
        raise RuntimeError("Unexpected method call.")

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
    ) -> "RosTimeRate":
        """Create a RosTimeRate object from an XML tree."""
        assert_xml_tag_ok(RosTimeRate, xml_tree)
        timer_name = get_xml_attribute(RosTimeRate, xml_tree, "name")
        valid_rate_types = AscxmlConfiguration.__subclasses__() + [str]
        timer_rate = read_value_from_xml_arg_or_child(
            cls, xml_tree, "rate_hz", custom_data_types, valid_rate_types
        )
        assert isinstance(timer_name, str)  # MyPy Check
        assert isinstance(timer_rate, (str, AscxmlConfiguration))  # MyPy check
        return RosTimeRate(timer_name, timer_rate)

    def __init__(self, name: str, rate_hz: Union[str, float, AscxmlConfiguration]):
        self._name = name
        self._rate_hz: Union[float, AscxmlConfiguration] = 0.0
        if isinstance(rate_hz, AscxmlConfiguration):
            self._rate_hz = rate_hz
        else:
            self._rate_hz = float(rate_hz)

    def get_interface_name(self) -> str:
        raise RuntimeError("Error: SCXML rate timer: deleted method 'get_interface_name'.")

    def get_interface_type(self) -> str:
        raise RuntimeError("Error: SCXML rate timer: deleted method 'get_interface_type'.")

    def check_valid_interface_type(self) -> bool:
        # Timers have no type, so it can always return true
        return True

    def get_name(self) -> str:
        return self._name

    def get_rate(self) -> Union[float, AscxmlConfiguration]:
        return self._rate_hz

    def preprocess_declaration(self, ascxml_declarations: List[AscxmlDeclaration], **kwargs):
        if isinstance(self._rate_hz, AscxmlConfiguration):
            self._rate_hz.update_configured_value(ascxml_declarations)
            assert self._rate_hz.is_constant_value(), get_error_msg(
                self.get_xml_origin(), "ROS declarations require a constant configurable value."
            )
            self._rate_hz = float(self._rate_hz.get_configured_value())

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

    def check_interface_defined(self, ascxml_declarations: List[AscxmlDeclaration]) -> bool:
        for ascxml_decl in ascxml_declarations:
            if isinstance(ascxml_decl, RosTimeRate):
                if ascxml_decl.get_name() == self._interface_name:
                    return True
        return False

    def get_plain_scxml_event(self, _) -> str:
        return generate_rate_timer_event(self._interface_name)
