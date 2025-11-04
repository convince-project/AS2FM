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

from typing import Dict, List, Optional, Union

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from moco.moco_common.ecmascript_interpretation import has_operators, is_literal
from moco.roaml_converter.data_types.struct_definition import StructDefinition
from moco.roaml_converter.scxml_entries import BtGetValueInputPort, ScxmlBase
from moco.roaml_converter.scxml_entries.bt_utils import (
    BtPortsHandler,
    get_input_variable_as_scxml_expression,
    is_blackboard_reference,
)
from moco.roaml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from moco.roaml_converter.scxml_entries.utils import (
    CallbackType,
    convert_expression_with_object_arrays,
    get_plain_variable_name,
    is_non_empty_string,
)
from moco.roaml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok,
    get_xml_attribute,
    read_value_from_xml_arg_or_child,
)


class ScxmlParam(ScxmlBase):
    """This class represents a single parameter."""

    @staticmethod
    def get_tag_name() -> str:
        return "param"

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
    ) -> "ScxmlParam":
        """Create a ScxmlParam object from an XML tree."""
        assert_xml_tag_ok(ScxmlParam, xml_tree)
        name = get_xml_attribute(ScxmlParam, xml_tree, "name")
        expr = read_value_from_xml_arg_or_child(
            ScxmlParam, xml_tree, "expr", custom_data_types, (BtGetValueInputPort, str), True
        )
        location = get_xml_attribute(ScxmlParam, xml_tree, "location", undefined_allowed=True)
        return ScxmlParam(name, expr=expr, location=location)

    def __init__(
        self,
        name: str,
        *,
        expr: Optional[Union[BtGetValueInputPort, str]] = None,
        location: Optional[str] = None,
        cb_type: Optional[CallbackType] = None,
    ):
        """
        Initialize the SCXML Parameter object.

        The 'location' entry is kept for consistency, but using expr achieves the same result.

        :param name: The name of the parameter.
        :param expr: The expression to assign to the parameter. Can come from a BT port.
        :param location: The expression to assign to the parameter, if that's a data variable.
        """
        # TODO: We might need types in ScxmlParams as well, for later converting them to JANI.
        self._name = name
        self._expr = expr
        self._location = location
        self._cb_type: Optional[CallbackType] = cb_type

    def set_callback_type(self, cb_type: CallbackType):
        self._cb_type = cb_type

    def get_name(self) -> str:
        return self._name

    def get_expr(self) -> Optional[Union[BtGetValueInputPort, str]]:
        return self._expr

    def get_expr_or_location(self) -> str:
        """
        Return either the expr or location argument, depending on which one is None.

        Ensures that at least one is valid.
        """
        # Deprecated
        if self._expr is not None:
            return self._expr
        assert is_non_empty_string(ScxmlParam, "location", self._location)
        return self._location

    def has_bt_blackboard_input(self, bt_ports_handler: BtPortsHandler):
        return isinstance(self._expr, BtGetValueInputPort) and is_blackboard_reference(
            bt_ports_handler.get_port_value(self._expr.get_key_name())
        )

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        """Update the values of potential entries making use of BT ports."""
        if isinstance(self._expr, BtGetValueInputPort):
            self._expr = get_input_variable_as_scxml_expression(
                bt_ports_handler.get_port_value(self._expr.get_key_name())
            )

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

    def _set_plain_name_and_expression(self, struct_declarations: ScxmlStructDeclarationsContainer):
        """In place substitution of member accesses in the name and expression."""
        self._name = get_plain_variable_name(self._name, self.get_xml_origin())
        self._expr = convert_expression_with_object_arrays(
            self._expr, self.get_xml_origin(), struct_declarations
        )

    def as_plain_scxml(
        self, struct_declarations: ScxmlStructDeclarationsContainer, _
    ) -> List["ScxmlParam"]:
        plain_params: List[ScxmlParam] = []
        assert isinstance(self._expr, str)
        if has_operators(self._expr, self.get_xml_origin()) or is_literal(
            self._expr, self.get_xml_origin()
        ):
            # In this case, we assume the expression evaluates to a base type
            # TODO: Consider checking this assumption
            plain_params.append(self)
        else:
            # In case of single variables or their members, check if expansion is required
            struct_def, _ = struct_declarations.get_data_type(self._expr, self.get_xml_origin())
            if isinstance(struct_def, str):
                # This is a base type, no expansion required
                plain_params.append(self)
            else:
                for member_key in struct_def.get_expanded_members().keys():
                    new_name = f"{self.get_name()}.{member_key}"
                    new_expr = f"{self.get_expr_or_location()}.{member_key}"
                    plain_params.append(
                        ScxmlParam(name=new_name, expr=new_expr, cb_type=self._cb_type)
                    )
        for plain_param in plain_params:
            plain_param._set_plain_name_and_expression(struct_declarations)
        return plain_params

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "SCXML: found invalid param."
        xml_param = ET.Element(ScxmlParam.get_tag_name(), {"name": self._name})
        if self._expr is not None:
            xml_param.set("expr", self._expr)
        if self._location is not None:
            xml_param.set("location", self._location)
        return xml_param
