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

from typing import Dict, List, Optional, Tuple

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.logging import get_error_msg
from as2fm.scxml_converter.ascxml_extensions.bt_entries import (
    BtGenericPortDeclaration,
    BtOutputPortDeclaration,
)
from as2fm.scxml_converter.ascxml_extensions.bt_entries.bt_utils import (
    BT_SET_BLACKBOARD_PARAM,
    generate_bt_blackboard_set,
)
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import AscxmlDeclaration, ScxmlBase, ScxmlParam, ScxmlSend
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
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, _: Dict[str, StructDefinition]
    ) -> "BtSetValueOutputPort":
        assert_xml_tag_ok(BtSetValueOutputPort, xml_tree)
        key_str = get_xml_attribute(BtSetValueOutputPort, xml_tree, "key")
        expr_str = get_xml_attribute(BtSetValueOutputPort, xml_tree, "expr")
        assert isinstance(key_str, str) and isinstance(expr_str, str)  # Always true, for MyPy!
        return BtSetValueOutputPort(key_str, expr_str)

    def __init__(self, key_str: str, expr_str: str):
        self._key = key_str
        self._expr = expr_str
        self._blackboard_reference: Optional[str] = None

    def check_validity(self) -> bool:
        return is_non_empty_string(BtSetValueOutputPort, "key", self._key) and is_non_empty_string(
            BtSetValueOutputPort, "expr", self._expr
        )

    def get_config_request_receive_events(self) -> Optional[Tuple[str, str]]:
        # We do not expect reading from BT Ports here. Return None!
        return None

    def update_configurable_entry(self, ascxml_declarations: List[AscxmlDeclaration]):
        # Find the BT port associated to this object
        for ascxml_decl in ascxml_declarations:
            if (
                isinstance(ascxml_decl, BtGenericPortDeclaration)
                and ascxml_decl.get_key_name() == self._key
            ):
                assert isinstance(ascxml_decl, BtOutputPortDeclaration), get_error_msg(
                    self.get_xml_origin(),
                    "Expected a BT output port in the declarations, found a different one.",
                )
                self._blackboard_reference = ascxml_decl.get_key_value()
                assert self._blackboard_reference is not None, get_error_msg(
                    self.get_xml_origin(), "Cannot retrieve the blackboard variable to set."
                )
                return

    def as_plain_scxml(
        self, struct_declarations, ascxml_declarations: List[AscxmlDeclaration], **kwargs
    ) -> List[ScxmlBase]:
        assert self._blackboard_reference is not None, get_error_msg(
            self.get_xml_origin(), "Expected the blackboard variable to be set at this stage."
        )
        return [
            ScxmlSend(
                generate_bt_blackboard_set(self._blackboard_reference),
                [ScxmlParam(BT_SET_BLACKBOARD_PARAM, expr=self._expr)],
            )
        ]

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "Error: SCXML BT Output Port: invalid parameters."
        xml_bt_in_port = ET.Element(
            BtSetValueOutputPort.get_tag_name(), {"key": self._key, "expr": self._expr}
        )
        return xml_bt_in_port
