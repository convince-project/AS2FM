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
SCXML get input for Behavior Trees' Ports.
"""

from lxml import etree as ET

from as2fm.scxml_converter.scxml_entries import ScxmlBase
from as2fm.scxml_converter.scxml_entries.utils import is_non_empty_string
from as2fm.scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok, get_xml_argument


class BtGetValueInputPort(ScxmlBase):
    """
    Get the value of an input port in a bt plugin.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_get_input"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "BtGetValueInputPort":
        assert_xml_tag_ok(BtGetValueInputPort, xml_tree)
        key_str = get_xml_argument(BtGetValueInputPort, xml_tree, "key")
        return BtGetValueInputPort(key_str)

    def __init__(self, key_str: str):
        self._key = key_str

    def check_validity(self) -> bool:
        return is_non_empty_string(BtGetValueInputPort, "key", self._key)

    def get_key_name(self) -> str:
        return self._key

    def as_plain_scxml(self, _) -> ScxmlBase:
        # This is discarded in the to_plain_scxml_and_declarations method from ScxmlRoot
        raise RuntimeError("Error: SCXML BT Port value getter cannot be converted to plain SCXML.")

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML BT Input Port: invalid parameters."
        xml_bt_in_port = ET.Element(BtGetValueInputPort.get_tag_name(), {"key": self._key})
        return xml_bt_in_port
