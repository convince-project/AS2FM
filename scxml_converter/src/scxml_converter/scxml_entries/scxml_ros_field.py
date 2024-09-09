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

"""Declaration of the ROS Field SCXML tag extension."""

from typing import Union

from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import ScxmlParam, BtGetValueInputPort
from scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok, get_xml_argument, read_value_from_xml_arg_or_child)
from scxml_converter.scxml_entries.utils import (
    CallbackType, get_plain_expression, is_non_empty_string, ROS_FIELD_PREFIX)


class RosField(ScxmlParam):
    """Field of a ROS msg published in a topic."""

    @staticmethod
    def get_tag_name() -> str:
        return "field"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element, cb_type: CallbackType) -> "RosField":
        """Create a RosField object from an XML tree."""
        assert_xml_tag_ok(RosField, xml_tree)
        name = get_xml_argument(RosField, xml_tree, "name")
        expr = read_value_from_xml_arg_or_child(RosField, xml_tree, "expr",
                                                (BtGetValueInputPort, str))
        return RosField(name, expr, cb_type)

    def __init__(self, name: str, expr: Union[BtGetValueInputPort, str], cb_type: CallbackType):
        self._name = name
        self._expr = expr
        self._cb_type = cb_type
        assert self.check_validity(), "Error: SCXML topic publish field: invalid parameters."

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(RosField, "name", self._name)
        valid_expr = is_non_empty_string(RosField, "expr", self._expr)
        return valid_name and valid_expr

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        """Update the values of potential entries making use of BT ports."""
        if isinstance(self._expr, BtGetValueInputPort):
            self._expr = bt_ports_handler.get_in_port_value(self._expr.get_key_name())

    def as_plain_scxml(self, _) -> ScxmlParam:
        # In order to distinguish the message body from additional entries, add a prefix to the name
        plain_field_name = f"{ROS_FIELD_PREFIX}.{self._name}"
        return ScxmlParam(plain_field_name, CallbackType.get_plain_callback(self._cb_type),
                          expr=get_plain_expression(self._expr, self._cb_type))

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic publish field: invalid parameters."
        xml_field = ET.Element(RosField.get_tag_name(), {"name": self._name, "expr": self._expr})
        return xml_field
