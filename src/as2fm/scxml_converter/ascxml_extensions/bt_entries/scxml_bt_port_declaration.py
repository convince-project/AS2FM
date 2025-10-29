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

from typing import Dict, List, Optional

from lxml import etree as ET
from lxml.etree import _Element as XmlElement
from typing_extensions import Self

from as2fm.as2fm_common.logging import check_assertion
from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration
from as2fm.scxml_converter.ascxml_extensions.bt_entries.bt_utils import is_blackboard_reference
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries.utils import is_non_empty_string
from as2fm.scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok, get_xml_attribute


class BtGenericPortDeclaration(AscxmlDeclaration):
    @classmethod
    def from_xml_tree_impl(cls, xml_tree: XmlElement, _: Dict[str, StructDefinition]) -> Self:
        assert_xml_tag_ok(cls, xml_tree)
        key_str = get_xml_attribute(cls, xml_tree, "key")
        type_str = get_xml_attribute(cls, xml_tree, "type")
        assert isinstance(key_str, str) and isinstance(type_str, str)  # Only for MyPy
        return cls(key_str, type_str)

    def __init__(self, key_str: str, type_str: str):
        self._key = key_str
        self._type = type_str
        self._value: Optional[str] = None

    def check_validity(self) -> bool:
        return is_non_empty_string(type(self), "key", self._key) and is_non_empty_string(
            type(self), "type", self._type
        )

    def get_key_name(self) -> str:
        return self._key

    def get_key_type(self) -> str:
        return self._type

    def set_key_value(self, val: str):
        check_assertion(
            self._value is None,
            self.get_xml_origin(),
            f"Multiple assignments to BT port {self._key}",
        )
        self._value = val

    def get_key_value(self) -> Optional[str]:
        return self._value

    def preprocess_declaration(self, ascxml_declarations, **kwargs):
        # Nothing to do here!
        pass

    def as_plain_scxml(self, _, __):
        # This is discarded in the to_plain_scxml_and_declarations method from ScxmlRoot
        raise RuntimeError("Error: SCXML BT Ports declarations cannot be converted to plain SCXML.")

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "Error: SCXML BT Input Port: invalid parameters."
        xml_bt_port = ET.Element(self.get_tag_name(), {"key": self._key, "type": self._type})
        return xml_bt_port


class BtInputPortDeclaration(BtGenericPortDeclaration):
    """
    Declare an input port in a bt plugin.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_declare_port_in"


class BtOutputPortDeclaration(BtGenericPortDeclaration):
    """
    Declare an input port in a bt plugin.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_declare_port_out"

    def set_key_value(self, val):
        check_assertion(
            is_blackboard_reference(val),
            self.get_xml_origin(),
            f"Value of BT output port {self._key} must be a Blackboard variable reference.",
        )
        super().set_key_value(val)
