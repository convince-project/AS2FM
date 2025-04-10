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
Container for a single variable definition in SCXML. In XML, it has the tag `data`.
"""

import re
from typing import Any, List, Optional, Tuple, Union

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import is_comment
from as2fm.as2fm_common.logging import log_error
from as2fm.scxml_converter.scxml_entries import BtGetValueInputPort, ScxmlBase
from as2fm.scxml_converter.scxml_entries.bt_utils import BtPortsHandler, is_blackboard_reference
from as2fm.scxml_converter.scxml_entries.ros_utils import ScxmlRosDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    RESERVED_NAMES,
    is_non_empty_string,
)
from as2fm.scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok,
    get_xml_attribute,
    read_value_from_xml_arg_or_child,
)
from as2fm.scxml_converter.xml_data_types.type_utils import (
    convert_string_to_type,
    get_data_type_from_string,
    is_type_string_base_type,
)
from as2fm.scxml_converter.xml_data_types.xml_struct_definition import XmlStructDefinition

ValidExpr = Union[BtGetValueInputPort, str, int, float, bool]
ValidBound = Optional[Union[BtGetValueInputPort, str, int, float]]


def valid_bound(bound_value: Any) -> bool:
    """Check if a bound is invalid."""
    if bound_value is None:
        return True
    if isinstance(bound_value, str):
        return len(bound_value) > 0
    return isinstance(bound_value, (int, float))


class ScxmlData(ScxmlBase):
    """This class represents the variables defined in the model."""

    @staticmethod
    def get_tag_name() -> str:
        return "data"

    @staticmethod
    def _interpret_type_from_comment_above(
        comment_above: Optional[str],
    ) -> Optional[Tuple[str, str]]:
        """Interpret the type of the data from the comment above the data tag.

        :param comment_above: The comment above the data tag (optional)
        :return: The type of the data, None if not found
        """
        if comment_above is None:
            return None
        # match string inside xml comment brackets
        type_match = re.search(r"TYPE\ (.+):(.+)", comment_above.strip())
        if type_match is None:
            return None
        return type_match.group(1), type_match.group(2)

    @classmethod
    def from_xml_tree_impl(
        cls,
        xml_tree: XmlElement,
        custom_data_types: List[XmlStructDefinition],
        comment_above: Optional[str] = None,
    ) -> "ScxmlData":
        """Create a ScxmlData object from an XML tree."""
        assert_xml_tag_ok(ScxmlData, xml_tree)
        data_id = get_xml_attribute(ScxmlData, xml_tree, "id")
        data_type = get_xml_attribute(ScxmlData, xml_tree, "type", undefined_allowed=True)
        if data_type is None:
            if is_comment(comment_above):
                pass
            comment_tuple = ScxmlData._interpret_type_from_comment_above(comment_above)
            assert comment_tuple is not None, f"Error: SCXML data: type of {data_id} not found."
            assert comment_tuple[0] == data_id, (
                "Error: SCXML data: unexpected ID in type in comment "
                f"({comment_tuple[0]}!={data_id})."
            )
            data_type = comment_tuple[1]
        data_expr = read_value_from_xml_arg_or_child(
            ScxmlData, xml_tree, "expr", custom_data_types, (BtGetValueInputPort, str)
        )
        lower_bound = read_value_from_xml_arg_or_child(
            ScxmlData,
            xml_tree,
            "lower_bound_incl",
            custom_data_types,
            (BtGetValueInputPort, str),
            none_allowed=True,
        )
        upper_bound = read_value_from_xml_arg_or_child(
            ScxmlData,
            xml_tree,
            "upper_bound_incl",
            custom_data_types,
            (BtGetValueInputPort, str),
            none_allowed=True,
        )
        instance = ScxmlData(data_id, data_expr, data_type, lower_bound, upper_bound)
        instance.set_xml_origin(xml_tree)
        instance.set_custom_data_types(custom_data_types)
        return instance

    def __init__(
        self,
        id_: str,
        expr: ValidExpr,
        data_type: str,
        lower_bound: ValidBound = None,
        upper_bound: ValidBound = None,
    ):
        self._id: str = id_
        if isinstance(expr, (str, BtGetValueInputPort)):
            self._expr = expr
        else:
            self._expr = str(expr)
        self._data_type: str = data_type
        self._lower_bound: Optional[str] = None if lower_bound is None else str(lower_bound)
        self._upper_bound: Optional[str] = None if upper_bound is None else str(upper_bound)

    def get_name(self) -> str:
        return self._id

    def get_type_str(self) -> str:
        """Get the type of the data as a string."""
        return self._data_type

    def get_type(self) -> type:
        """
        Get the type of the data as a Python type.

        Use this only after substitution of custom data types.
        """
        python_type = get_data_type_from_string(self._data_type)
        assert (
            python_type is not None
        ), f"Error: SCXML data: '{self._id}' has unknown type '{self._data_type}'."
        return python_type

    def get_expr(self) -> ValidExpr:
        return self._expr

    def check_valid_bounds(self) -> bool:
        if all(bound is None for bound in [self._lower_bound, self._upper_bound]):
            # Nothing to check
            return True
        if self.get_type() not in (float, int):
            log_error(
                self.get_xml_origin(),
                f"Error: SCXML data: '{self._id}' has bounds but has type {self._data_type}, "
                "not a number.",
            )
            return False
        lower_bound = None
        upper_bound = None
        if self._lower_bound is not None:
            lower_bound = convert_string_to_type(self._lower_bound, self._data_type)
        if self._upper_bound is not None:
            upper_bound = convert_string_to_type(self._upper_bound, self._data_type)
        if all(bound is not None for bound in [lower_bound, upper_bound]):
            if lower_bound > upper_bound:
                print(
                    f"Error: SCXML data: 'lower_bound_incl' {lower_bound} is not smaller "
                    f"than 'upper_bound_incl' {upper_bound}."
                )
                return False
        return True

    def check_validity(self) -> bool:
        valid_id = is_non_empty_string(ScxmlData, "id", self._id)
        if valid_id in RESERVED_NAMES:
            print(f"Error: SCXML data: name '{self._id}' in reserved IDs list: {RESERVED_NAMES}.")
            return False
        if not is_type_string_base_type(self._data_type) and self._data_type not in [
            custom_struct.get_name() for custom_struct in self.get_custom_data_types()
        ]:
            print(f"Error: SCXML data: '{self._id}' has unknown type '{self._data_type}'.")
            return False
        if isinstance(self._expr, str):
            valid_expr = is_non_empty_string(ScxmlData, "expr", self._expr)
        else:
            valid_expr = isinstance(self._expr, (int, float, bool))
            if not valid_expr:
                print(
                    f"Error: SCXML data: '{self._id}': initial expression for type ",
                    f"{self._data_type} evaluates to an invalid type '{type(self._expr)}'.",
                )
        valid_bounds = self.check_valid_bounds()
        return valid_id and valid_expr and valid_bounds

    def as_xml(self, type_as_attribute: bool = True) -> XmlElement:
        """
        Generate the XML element representing the single data entry.

        :param type_as_attribute: If True, the type of the data is added as an attribute.
        """
        assert self.check_validity(), "SCXML: found invalid data object."
        xml_data = ET.Element(ScxmlData.get_tag_name(), {"id": self._id, "expr": self._expr})
        if type_as_attribute:
            xml_data.set("type", self._data_type)
        if self._lower_bound is not None:
            xml_data.set("lower_bound_incl", str(self._lower_bound))
        if self._upper_bound is not None:
            xml_data.set("upper_bound_incl", str(self._upper_bound))
        return xml_data

    def is_plain_scxml(self) -> bool:
        """Check if the data type is a base type."""
        return self.check_validity() and is_type_string_base_type(self._data_type)

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> List["ScxmlData"]:
        # TODO: By using ROS declarations, we can add the support for the ROS types as well.
        # TODO: This is fine also in case it is an array of base types...
        if is_type_string_base_type(self._data_type):
            return [self]
        data_type = None
        for custom_struct in self.get_custom_data_types():
            if custom_struct.get_name() == self._data_type:
                data_type = custom_struct
                break
        assert data_type is not None, f"Cannot find custom data type {self._data_type}."
        assert isinstance(self._expr, str), "We only support string init expr. for custom types."
        expanded_data_values = data_type.get_instance_from_expression(self._expr)
        expanded_data_types = data_type.get_expanded_members()
        return [
            ScxmlData(key, expanded_data_values[key], expanded_data_types[key])
            for key in expanded_data_types
        ]

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        if isinstance(self._expr, BtGetValueInputPort):
            self._expr = bt_ports_handler.get_in_port_value(self._expr.get_key_name())
            assert not is_blackboard_reference(self._expr), (
                f"Error: SCXML Data: '{self._id}': cannot set the initial expression from "
                f" the BT blackboard variable {self._expr}"
            )
        if isinstance(self._lower_bound, BtGetValueInputPort):
            self._lower_bound = bt_ports_handler.get_in_port_value(self._lower_bound.get_key_name())
            assert not is_blackboard_reference(self._lower_bound), (
                f"Error: SCXML Data: '{self._id}': cannot set the lower bound from "
                f" the BT blackboard variable {self._lower_bound}"
            )
        if isinstance(self._upper_bound, BtGetValueInputPort):
            self._upper_bound = bt_ports_handler.get_in_port_value(self._upper_bound.get_key_name())
            assert not is_blackboard_reference(self._upper_bound), (
                f"Error: SCXML Data: '{self._id}': cannot set the upper bound from "
                f" the BT blackboard variable {self._upper_bound}"
            )
