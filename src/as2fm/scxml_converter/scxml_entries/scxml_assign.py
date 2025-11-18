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

from copy import deepcopy
from typing import Dict, List, Optional, Union

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.logging import get_error_msg, log_warning
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import AscxmlConfiguration, AscxmlDeclaration, ScxmlBase
from as2fm.scxml_converter.scxml_entries.scxml_executable_entry import ScxmlExecutableEntry
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    convert_expression_with_object_arrays,
    convert_expression_with_string_literals,
    get_plain_expression,
    is_non_empty_string,
)
from as2fm.scxml_converter.scxml_entries.xml_utils import (
    add_configurable_to_xml,
    assert_xml_tag_ok,
    get_xml_attribute,
    read_value_from_xml_arg_or_child,
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
        assert isinstance(location, str)  # MyPy check
        expr_types = [str] + AscxmlConfiguration.__subclasses__()
        expr = read_value_from_xml_arg_or_child(
            ScxmlAssign, xml_tree, "expr", custom_data_types, expr_types
        )
        assert isinstance(expr, (str, AscxmlConfiguration))  # MyPy check
        return ScxmlAssign(location, expr)

    def __init__(self, location: str, expr: Union[str, AscxmlConfiguration]):
        self._location = location
        self._expr = expr
        self._cb_prefixes: Optional[List[str]] = None

    def set_callback_prefixes(self, cb_prefixes: List[str]) -> None:
        """Set the cb type for this assignment."""
        self._cb_prefixes = cb_prefixes

    def get_location(self) -> str:
        """Get the location to assign."""
        return self._location

    def get_expr(self) -> Union[str, AscxmlConfiguration]:
        """Get the expression to assign."""
        return self._expr

    def update_configurable_entry(self, ascxml_declarations: List[AscxmlDeclaration]):
        if isinstance(self._expr, AscxmlConfiguration):
            self._expr.update_configured_value(ascxml_declarations)

    def get_config_request_receive_events(self):
        if isinstance(self._expr, AscxmlConfiguration):
            return self._expr.get_config_request_response_events()
        return None

    def check_validity(self) -> bool:
        """
        Check that the ScxmlAssign instance is valid.

        Note that this assumes all values from BT ports are already substituted.
        """
        # TODO: Check that the location to assign exists in the data-model
        valid_location = is_non_empty_string(ScxmlAssign, "location", self._location)
        valid_expr = isinstance(self._expr, (str, AscxmlConfiguration))
        return valid_location and valid_expr

    def check_valid_ros_instantiations(self, _) -> bool:
        """Check if the ros instantiations have been declared."""
        # This has nothing to do with ROS. Return always True
        return True

    def is_plain_scxml(self, verbose: bool = False) -> bool:
        if type(self) is ScxmlAssign:
            valid_expr = isinstance(self._expr, str)
            if not valid_expr and verbose:
                log_warning(
                    None, f"No plain SCXML assign: expr type {type(self._expr)} isn't a string."
                )
            return valid_expr
        if verbose:
            log_warning(
                None, f"No plain SCXML: tag {self.get_tag_name()} isn't a plain assignment."
            )
        return False

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        assert self._cb_prefixes is not None, "Error: SCXML assign: callback type not set."
        if isinstance(self._expr, AscxmlConfiguration):
            self._expr = self._expr.get_configured_value()
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
        plain_assignments: List[ScxmlBase] = []
        for single_expr, single_loc in zip(expanded_expressions, expanded_locations):
            plain_expr = get_plain_expression(single_expr, self._cb_prefixes, struct_declarations)
            plain_location = convert_expression_with_object_arrays(single_loc, struct_declarations)
            plain_assignments.append(ScxmlAssign(plain_location, plain_expr))
        return plain_assignments

    def replace_strings_types_with_integer_arrays(self) -> "ScxmlAssign":
        """Replace all string literals in the contained expressions."""
        # Make sure that possible configurable values are already evaluated at this point.
        assert isinstance(self._expr, str), get_error_msg(
            self.get_xml_origin(), "Expected expression to be already evaluate at this stage."
        )
        return ScxmlAssign(self.get_location(), convert_expression_with_string_literals(self._expr))

    def add_events_targets(self, _):
        # Assignments have no events to handle: do nothing!
        return [deepcopy(self)]

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "SCXML: found invalid assign object."
        assign_xml = ET.Element(ScxmlAssign.get_tag_name(), {"location": self._location})
        add_configurable_to_xml(assign_xml, self._expr, "expr")
        return assign_xml
