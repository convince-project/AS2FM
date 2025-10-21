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

from typing import Dict

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import ScxmlBase
from as2fm.scxml_converter.scxml_entries.utils import is_non_empty_string
from as2fm.scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok, get_xml_attribute


class BtGetValueInputPort(ScxmlBase):
    """
    Get the value of an input port in a bt plugin.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_get_input"

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, _: Dict[str, StructDefinition]
    ) -> "BtGetValueInputPort":
        assert_xml_tag_ok(BtGetValueInputPort, xml_tree)
        key_str = get_xml_attribute(BtGetValueInputPort, xml_tree, "key")
        assert isinstance(key_str, str)  # This is always satisfied: only for MyPy
        return BtGetValueInputPort(key_str)

    def __init__(self, key_str: str):
        self._key = key_str

    def check_validity(self) -> bool:
        return is_non_empty_string(BtGetValueInputPort, "key", self._key)

    def get_key_name(self) -> str:
        return self._key

    def as_plain_scxml(self, _, __):
        # When starting the conversion to plain SCXML, we expect this to be already converted
        raise RuntimeError("Error: SCXML BT Port value getter cannot be converted to plain SCXML.")

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "Error: SCXML BT Input Port: invalid parameters."
        xml_bt_in_port = ET.Element(BtGetValueInputPort.get_tag_name(), {"key": self._key})
        return xml_bt_in_port
