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

from typing import Dict, List, Optional, Type, Union

from lxml import etree as ET
from lxml.etree import _Element as XmlElement
from typing_extensions import Self

from as2fm.as2fm_common.ecmascript_interpretation import has_operators, is_literal
from as2fm.as2fm_common.logging import check_assertion, log_warning
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import AscxmlConfiguration, AscxmlDeclaration, ScxmlBase
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    CallbackType,
    convert_expression_with_object_arrays,
    get_plain_variable_name,
    is_non_empty_string,
)
from as2fm.scxml_converter.scxml_entries.xml_utils import (
    add_configurable_to_xml,
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
        cls: Type[Self], xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
    ) -> "ScxmlParam":
        """Create a ScxmlParam object from an XML tree."""
        assert_xml_tag_ok(cls, xml_tree)
        name = get_xml_attribute(cls, xml_tree, "name")
        assert name is not None  # MyPy check
        valid_expr_types = AscxmlConfiguration.__subclasses__() + [str]
        expr = read_value_from_xml_arg_or_child(
            cls, xml_tree, "expr", custom_data_types, valid_expr_types
        )
        assert isinstance(expr, (str, AscxmlConfiguration))  # MyPy check
        return cls(name, expr=expr)

    def __init__(
        self,
        name: str,
        *,
        expr: Union[AscxmlConfiguration, str],
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
        self._cb_type: Optional[CallbackType] = cb_type

    def set_callback_type(self, cb_type: Optional[CallbackType]):
        self._cb_type = cb_type

    def get_name(self) -> str:
        return self._name

    def get_expr(self) -> Union[AscxmlConfiguration, str]:
        return self._expr

    def update_configured_value(self, ascxml_declarations: List[AscxmlDeclaration]):
        """Set the value of the configured value based on the declarations content."""
        if isinstance(self._expr, AscxmlConfiguration):
            self._expr.update_configured_value(ascxml_declarations)

    def evaluate_expr(self):
        """Replace expression of type AscxmlConfiguration with their current value."""
        if isinstance(self._expr, AscxmlConfiguration):
            self._expr = self._expr.get_configured_value()

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(type(self), "name", self._name)
        valid_expr = isinstance(self._expr, AscxmlConfiguration) or is_non_empty_string(
            type(self), "expr", self._expr
        )
        return valid_name and valid_expr

    def _set_plain_name_and_expression(self, struct_declarations: ScxmlStructDeclarationsContainer):
        """In place substitution of member accesses in the name and expression."""
        self._name = get_plain_variable_name(self._name, self.get_xml_origin())
        assert isinstance(self._expr, str)  # MyPy check
        self._expr = convert_expression_with_object_arrays(
            self._expr, self.get_xml_origin(), struct_declarations
        )

    def as_plain_scxml(self, struct_declarations, ascxml_declarations, **kwargs):
        plain_params: List[ScxmlParam] = []
        self.evaluate_expr()
        assert isinstance(self._expr, str)  # We don't expect anything else after evaluate_expr
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
                    new_expr = f"{self.get_expr()}.{member_key}"
                    plain_params.append(
                        ScxmlParam(name=new_name, expr=new_expr, cb_type=self._cb_type)
                    )
        for plain_param in plain_params:
            plain_param._set_plain_name_and_expression(struct_declarations)
        return plain_params

    def is_plain_scxml(self, verbose: bool = False):
        plain_expr = isinstance(self._expr, str)
        if not plain_expr and verbose:
            log_warning(None, f"No plain SCXML param: expr type {type(self._expr)} isn't a string.")

    def as_xml(self) -> XmlElement:
        check_assertion(self.check_validity(), self.get_xml_origin(), "Invalid parameter.")
        xml_param = ET.Element(self.get_tag_name(), {"name": self._name})
        add_configurable_to_xml(xml_param, self._expr, "expr")
        return xml_param
