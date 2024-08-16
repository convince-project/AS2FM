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

from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import ScxmlParam
from scxml_converter.scxml_entries.bt_utils import BtPortsHandler


class RosField(ScxmlParam):
    """Field of a ROS msg published in a topic."""

    def __init__(self, name: str, expr: str):
        self._name = name
        self._expr = expr
        assert self.check_validity(), "Error: SCXML topic publish field: invalid parameters."

    @staticmethod
    def get_tag_name() -> str:
        return "field"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "RosField":
        """Create a RosField object from an XML tree."""
        assert xml_tree.tag == RosField.get_tag_name(), \
            f"Error: SCXML topic publish field: XML tag name is not {RosField.get_tag_name()}"
        name = xml_tree.attrib.get("name")
        expr = xml_tree.attrib.get("expr")
        assert name is not None and expr is not None, \
            "Error: SCXML topic publish field: 'name' or 'expr' attribute not found in input xml."
        return RosField(name, expr)

    def check_validity(self) -> bool:
        valid_name = isinstance(self._name, str) and len(self._name) > 0
        valid_expr = isinstance(self._expr, str) and len(self._expr) > 0
        if not valid_name:
            print("Error: SCXML topic publish field: name is not valid.")
        if not valid_expr:
            print("Error: SCXML topic publish field: expr is not valid.")
        return valid_name and valid_expr

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        """Update the values of potential entries making use of BT ports."""
        # For now we do nothing, but it might be useful in the future
        pass

    def as_plain_scxml(self, _) -> ScxmlParam:
        from scxml_converter.scxml_entries.ros_utils import replace_ros_interface_expression
        return ScxmlParam(self._name, expr=replace_ros_interface_expression(self._expr))

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "Error: SCXML topic publish field: invalid parameters."
        xml_field = ET.Element(RosField.get_tag_name(), {"name": self._name, "expr": self._expr})
        return xml_field
