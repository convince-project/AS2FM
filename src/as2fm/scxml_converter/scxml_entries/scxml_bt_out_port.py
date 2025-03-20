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
SCXML set output for Behavior Trees' Ports.
"""

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.scxml_converter.scxml_entries import ScxmlParam, ScxmlSend
from as2fm.scxml_converter.scxml_entries.bt_utils import (
    BT_SET_BLACKBOARD_PARAM,
    BtPortsHandler,
    generate_bt_blackboard_set,
    get_blackboard_variable_name,
    is_blackboard_reference,
)
from as2fm.scxml_converter.scxml_entries.utils import is_non_empty_string
from as2fm.scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok, get_xml_attribute


class BtSetValueOutputPort(ScxmlSend):
    """
    Get the value of an input port in a bt plugin.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_set_output"

    @classmethod
    def from_xml_tree_impl(cls, xml_tree: XmlElement) -> "BtSetValueOutputPort":
        assert_xml_tag_ok(BtSetValueOutputPort, xml_tree)
        key_str = get_xml_attribute(BtSetValueOutputPort, xml_tree, "key")
        expr_str = get_xml_attribute(BtSetValueOutputPort, xml_tree, "expr")
        return BtSetValueOutputPort(key_str, expr_str)

    def __init__(self, key_str: str, expr_str: str):
        self._key = key_str
        self._expr = expr_str
        self._blackboard_reference = None

    def check_validity(self) -> bool:
        return is_non_empty_string(BtSetValueOutputPort, "key", self._key) and is_non_empty_string(
            BtSetValueOutputPort, "expr", self._expr
        )

    def has_bt_blackboard_input(self, _) -> bool:
        """We do not expect reading from BT Ports here. Return False!"""
        return False

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        assert bt_ports_handler.out_port_exists(
            self._key
        ), f"Error: SCXML BT Port {self._key} is not declared as output port."
        port_value = bt_ports_handler.get_out_port_value(self._key)
        assert is_blackboard_reference(
            port_value
        ), f"Error: SCXML BT Port {self._key} is not referencing a blackboard variable."
        self._blackboard_reference = get_blackboard_variable_name(port_value)

    def as_plain_scxml(self, _) -> ScxmlSend:
        # This is discarded in the to_plain_scxml_and_declarations method from ScxmlRoot
        assert (
            self._blackboard_reference is not None
        ), "Error: SCXML BT Output Port: must run 'update_bt_ports_values' before 'as_plain_scxml'"
        return ScxmlSend(
            generate_bt_blackboard_set(self._blackboard_reference),
            [ScxmlParam(BT_SET_BLACKBOARD_PARAM, expr=self._expr)],
        )

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "Error: SCXML BT Output Port: invalid parameters."
        xml_bt_in_port = ET.Element(
            BtSetValueOutputPort.get_tag_name(), {"key": self._key, "expr": self._expr}
        )
        return xml_bt_in_port
