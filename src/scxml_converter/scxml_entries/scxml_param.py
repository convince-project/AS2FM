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
Container for a single parameter, sent within an event. In XML, it has the tag `param`.
"""

from typing import Optional, Union
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import ScxmlBase, BtGetValueInputPort
from scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok, get_xml_argument, read_value_from_xml_arg_or_child)
from scxml_converter.scxml_entries.utils import CallbackType, is_non_empty_string


class ScxmlParam(ScxmlBase):
    """This class represents a single parameter."""

    @staticmethod
    def get_tag_name() -> str:
        return "param"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlParam":
        """Create a ScxmlParam object from an XML tree."""
        assert_xml_tag_ok(ScxmlParam, xml_tree)
        name = get_xml_argument(ScxmlParam, xml_tree, "name")
        expr = read_value_from_xml_arg_or_child(ScxmlParam, xml_tree, "expr",
                                                (BtGetValueInputPort, str), True)
        location = get_xml_argument(ScxmlParam, xml_tree, "location", none_allowed=True)
        return ScxmlParam(name, expr=expr, location=location)

    def __init__(self, name: str, *,
                 expr: Optional[Union[BtGetValueInputPort, str]] = None,
                 location: Optional[str] = None):
        """
        Initialize the SCXML Parameter object.

        The location entryu is kept for consistency, but using expr achieves the same result.

        :param name: The name of the parameter.
        :param expr: The expression to assign to the parameter. Can come from a BT port.
        :param location: The expression to assign to the parameter, if that's a data variable.
        """
        # TODO: We might need types in ScxmlParams as well, for later converting them to JANI.
        self._name = name
        self._expr = expr
        self._location = location
        self._cb_type: Optional[CallbackType] = None

    def set_callback_type(self, cb_type: CallbackType):
        self._cb_type = cb_type

    def get_name(self) -> str:
        return self._name

    def get_expr(self) -> Optional[str]:
        return self._expr

    def get_location(self) -> Optional[str]:
        return self._location

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        """Update the values of potential entries making use of BT ports."""
        if isinstance(self._expr, BtGetValueInputPort):
            self._expr = bt_ports_handler.get_in_port_value(self._expr.get_key_name())

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(ScxmlParam, "name", self._name)
        valid_expr = False
        if self._location is None:
            valid_expr = is_non_empty_string(ScxmlParam, "expr", self._expr)
        elif self._expr is None:
            valid_expr = is_non_empty_string(ScxmlParam, "location", self._location)
        else:
            print("Error: SCXML param: expr and location are both set.")
        return valid_name and valid_expr

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid param."
        xml_param = ET.Element(ScxmlParam.get_tag_name(), {"name": self._name})
        if self._expr is not None:
            xml_param.set("expr", self._expr)
        if self._location is not None:
            xml_param.set("location", self._location)
        return xml_param