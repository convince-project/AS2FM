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
SCXML entries related to Behavior Trees' Ports declaration.
"""

from typing import Dict, List, Union

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.scxml_converter.scxml_entries import ScxmlBase
from as2fm.scxml_converter.scxml_entries.utils import is_non_empty_string
from as2fm.scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok, get_xml_attribute
from as2fm.scxml_converter.xml_data_types.xml_struct_definition import XmlStructDefinition


class BtInputPortDeclaration(ScxmlBase):
    """
    Declare an input port in a bt plugin.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_declare_port_in"

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, _: Dict[str, XmlStructDefinition]
    ) -> "BtInputPortDeclaration":
        assert_xml_tag_ok(BtInputPortDeclaration, xml_tree)
        key_str = get_xml_attribute(BtInputPortDeclaration, xml_tree, "key")
        type_str = get_xml_attribute(BtInputPortDeclaration, xml_tree, "type")
        return BtInputPortDeclaration(key_str, type_str)

    def __init__(self, key_str: str, type_str: str):
        self._key = key_str
        self._type = type_str

    def check_validity(self) -> bool:
        return is_non_empty_string(
            BtInputPortDeclaration, "key", self._key
        ) and is_non_empty_string(BtInputPortDeclaration, "type", self._type)

    def get_key_name(self) -> str:
        return self._key

    def get_key_type(self) -> str:
        return self._type

    def as_plain_scxml(self, _, __) -> List[ScxmlBase]:
        # This is discarded in the to_plain_scxml_and_declarations method from ScxmlRoot
        raise RuntimeError("Error: SCXML BT Ports declarations cannot be converted to plain SCXML.")

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "Error: SCXML BT Input Port: invalid parameters."
        xml_bt_in_port = ET.Element(
            BtInputPortDeclaration.get_tag_name(), {"key": self._key, "type": self._type}
        )
        return xml_bt_in_port


class BtOutputPortDeclaration(ScxmlBase):
    """
    Declare an input port in a bt plugin.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_declare_port_out"

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, _: Dict[str, XmlStructDefinition]
    ) -> "BtOutputPortDeclaration":
        assert_xml_tag_ok(BtOutputPortDeclaration, xml_tree)
        key_str = get_xml_attribute(BtOutputPortDeclaration, xml_tree, "key")
        type_str = get_xml_attribute(BtOutputPortDeclaration, xml_tree, "type")
        return BtOutputPortDeclaration(key_str, type_str)

    def __init__(self, key_str: str, type_str: str):
        self._key = key_str
        self._type = type_str

    def check_validity(self) -> bool:
        return is_non_empty_string(
            BtOutputPortDeclaration, "key", self._key
        ) and is_non_empty_string(BtOutputPortDeclaration, "type", self._type)

    def get_key_name(self) -> str:
        return self._key

    def get_key_type(self) -> str:
        return self._type

    def as_plain_scxml(self, _, __) -> List[ScxmlBase]:
        # This is discarded in the to_plain_scxml_and_declarations method from ScxmlRoot
        raise RuntimeError("Error: SCXML BT Ports declarations cannot be converted to plain SCXML.")

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "Error: SCXML BT Input Port: invalid parameters."
        xml_bt_in_port = ET.Element(
            BtOutputPortDeclaration.get_tag_name(), {"key": self._key, "type": self._type}
        )
        return xml_bt_in_port


BtPortDeclarations = Union[BtInputPortDeclaration, BtOutputPortDeclaration]
