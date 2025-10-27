# Copyright (c) 2025 - for information on the respective copyright owner
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

from typing import Dict, List, Optional, Union

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import is_comment
from as2fm.as2fm_common.logging import get_error_msg

from as2fm.scxml_converter.scxml_entries.scxml_executable_entry import ScxmlExecutableEntry

from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration
from as2fm.scxml_converter.ascxml_extensions.bt_entries.bt_utils import (
    BtPortsHandler,
    get_input_variable_as_scxml_expression,
    is_blackboard_reference,
    is_removed_bt_event,
)
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import (
    BtGetValueInputPort,
    ScxmlBase,
    ScxmlParam,
    ScxmlRosDeclarationsContainer,
)
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    CallbackType,
    convert_expression_with_object_arrays,
    convert_expression_with_string_literals,
    generate_tag_to_class_map,
    get_plain_expression,
    is_non_empty_string,
)
from as2fm.scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok,
    get_xml_attribute,
    read_value_from_xml_child,
)

class ScxmlAssign(ScxmlExecutableEntry):
    """This class represents a variable assignment."""

    @staticmethod
    def get_tag_name() -> str:
        return "assign"

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
    ) -> "ScxmlAssign":
        """
        Create a ScxmlAssign object from an XML tree.

        :param xml_tree: The XML tree to create the object from.
        """
        assert_xml_tag_ok(ScxmlAssign, xml_tree)
        location = get_xml_attribute(ScxmlAssign, xml_tree, "location")
        expr = get_xml_attribute(ScxmlAssign, xml_tree, "expr", undefined_allowed=True)
        if expr is None:
            expr = read_value_from_xml_child(
                xml_tree, "expr", custom_data_types, (BtGetValueInputPort, str)
            )
            assert expr is not None, "Error: SCXML assign: expr is not valid."
        return ScxmlAssign(location, expr)

    def __init__(self, location: str, expr: Union[str, BtGetValueInputPort]):
        self._location = location
        self._expr = expr
        self._cb_type: Optional[CallbackType] = None

    def set_callback_type(self, cb_type: CallbackType) -> None:
        """Set the cb type for this assignment."""
        self._cb_type = cb_type

    def get_location(self) -> str:
        """Get the location to assign."""
        return self._location

    def get_expr(self) -> Union[str, BtGetValueInputPort]:
        """Get the expression to assign."""
        return self._expr

    def has_bt_blackboard_input(self, bt_ports_handler: BtPortsHandler):
        """Check whether the If entry reads content from the BT Blackboard."""
        return isinstance(self._expr, BtGetValueInputPort) and is_blackboard_reference(
            bt_ports_handler.get_port_value(self._expr.get_key_name())
        )

    def instantiate_bt_events(self, _, __) -> List["ScxmlAssign"]:
        """This functionality is not needed in this class."""
        return [self]

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        """Update the values of potential entries making use of BT ports."""
        if isinstance(self._expr, BtGetValueInputPort):
            self._expr = get_input_variable_as_scxml_expression(
                bt_ports_handler.get_port_value(self._expr.get_key_name())
            )

    def check_validity(self) -> bool:
        """
        Check that the ScxmlAssign instance is valid.

        Note that this assumes all values from BT ports are already substituted.
        """
        # TODO: Check that the location to assign exists in the data-model
        valid_location = is_non_empty_string(ScxmlAssign, "location", self._location)
        valid_expr = is_non_empty_string(ScxmlAssign, "expr", self._expr)
        return valid_location and valid_expr

    def check_valid_ros_instantiations(self, _) -> bool:
        """Check if the ros instantiations have been declared."""
        # This has nothing to do with ROS. Return always True
        return True

    def is_plain_scxml(self) -> bool:
        if type(self) is ScxmlAssign:
            return isinstance(self._expr, str)
        return False

    def as_plain_scxml(
        self, struct_declarations: ScxmlStructDeclarationsContainer, _
    ) -> List["ScxmlAssign"]:
        assert self._cb_type is not None, "Error: SCXML assign: callback type not set."
        assert isinstance(self._expr, str), get_error_msg(
            self.get_xml_origin(), "Unexpected expr. type."
        )
        location_type, array_info = struct_declarations.get_data_type(
            self._location, self.get_xml_origin()
        )
        expanded_expressions = []
        expanded_locations = []
        if isinstance(location_type, StructDefinition):
            # We are dealing with a custom type, more assignments in output
            sub_types = location_type.get_expanded_members()
            # Assumption: This appending of members works only if the expr is a single variable
            # Currently, this is not enforced in this method.
            for struct_member in sub_types.keys():
                # Here we keep dots, since we are running the plain-ification below
                expanded_expressions.append(f"{self._expr}.{struct_member}")
                expanded_locations.append(f"{self._location}.{struct_member}")
        else:
            expanded_expressions = [self._expr]
            expanded_locations = [self._location]
        plain_assignments: List[ScxmlAssign] = []
        for single_expr, single_loc in zip(expanded_expressions, expanded_locations):
            plain_expr = get_plain_expression(single_expr, self._cb_type, struct_declarations)
            plain_location = convert_expression_with_object_arrays(single_loc, struct_declarations)
            plain_assignments.append(ScxmlAssign(plain_location, plain_expr))
        return plain_assignments

    def replace_strings_types_with_integer_arrays(self) -> "ScxmlAssign":
        """Replace all string literals in the contained expressions."""
        return ScxmlAssign(
            self.get_location(), convert_expression_with_string_literals(self.get_expr())
        )

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "SCXML: found invalid assign object."
        return ET.Element(
            ScxmlAssign.get_tag_name(), {"location": self._location, "expr": self._expr}
        )
