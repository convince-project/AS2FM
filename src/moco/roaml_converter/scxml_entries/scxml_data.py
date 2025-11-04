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
from typing import Any, Dict, List, Optional, Tuple, Union

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from moco.moco_common.common import is_comment
from moco.moco_common.logging import check_assertion, get_error_msg, log_error
from moco.roaml_converter.data_types.struct_definition import (
    StructDefinition,
)
from moco.roaml_converter.data_types.type_utils import (
    convert_string_to_type,
    get_array_type_and_dimensions_from_string,
    get_data_type_from_string,
    get_type_string_from_type_and_dimensions,
    get_type_string_of_array,
    is_type_string_array,
    is_type_string_base_type,
)
from moco.roaml_converter.scxml_entries import BtGetValueInputPort, ScxmlBase
from moco.roaml_converter.scxml_entries.bt_utils import (
    BtPortsHandler,
    BtResponse,
    is_blackboard_reference,
)
from moco.roaml_converter.scxml_entries.ros_utils import ScxmlRosDeclarationsContainer
from moco.roaml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from moco.roaml_converter.scxml_entries.utils import (
    convert_expression_with_string_literals,
    get_plain_variable_name,
)
from moco.roaml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok,
    get_xml_attribute,
    read_value_from_xml_arg_or_child,
)

# List of names that shall not be used for variable names
RESERVED_NAMES: List[str] = [] + BtResponse._member_names_

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
        custom_data_types: Dict[str, StructDefinition],
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

    def get_expr(self) -> ValidExpr:
        return self._expr

    def _valid_id(self) -> bool:
        """Check if the data ID is valid."""
        valid_id = len(self._id) > 0 and self._id not in RESERVED_NAMES
        if not valid_id:
            log_error(self.get_xml_origin(), f"Data ID '{self._id}' is invalid.")
        return valid_id

    def _valid_type(self) -> bool:
        """Check if the type string is valid."""
        if len(self._data_type) == 0:
            log_error(self.get_xml_origin(), "No data type found.")
            return False
        base_type = self._data_type
        if is_type_string_array(self._data_type):
            base_type = get_type_string_of_array(self._data_type)
        if is_type_string_base_type(base_type):
            return True
        if base_type in self.get_custom_data_types().keys():
            return True
        log_error(self.get_xml_origin(), f"Cannot find definition of type {self._data_type}.")
        return False

    def _valid_init_expr(self) -> bool:
        """Check if the initial expression makes sense."""
        if isinstance(self._expr, str):
            if len(self._expr) == 0:
                log_error(self.get_xml_origin(), "Empty init expr. found.")
                return False
            return True
        log_error(
            self.get_xml_origin(),
            f"Expected init expr. to be strings, found {type(self._expr)} for data ID {self._id}",
        )
        return False

    def _valid_bounds(self) -> bool:
        if self._lower_bound is None and self._upper_bound is None:
            # Nothing to check
            return True
        if not is_type_string_base_type(self._data_type):
            log_error(
                self.get_xml_origin(),
                f"SCXML data: '{self._id}' has bounds, but type {self._data_type} is not a number.",
            )
            return False
        py_type = get_data_type_from_string(self._data_type)
        if py_type not in (float, int):
            log_error(
                self.get_xml_origin(),
                f"SCXML data: '{self._id}' has bounds, but type {self._data_type} is not a number.",
            )
            return False
        lower_bound = None
        upper_bound = None
        if self._lower_bound is not None:
            lower_bound = convert_string_to_type(
                self._lower_bound, self._data_type, self.get_xml_origin()
            )
        if self._upper_bound is not None:
            upper_bound = convert_string_to_type(
                self._upper_bound, self._data_type, self.get_xml_origin()
            )
        if lower_bound is not None and upper_bound is not None:
            if lower_bound > upper_bound:
                log_error(
                    self.get_xml_origin(),
                    f"SCXML data: 'lower_bound_incl' {lower_bound} is not smaller "
                    f"than 'upper_bound_incl' {upper_bound}.",
                )
                return False
        return True

    def check_validity(self) -> bool:
        """Check if the current scxml data instance is valid."""
        return all(
            [self._valid_id(), self._valid_type, self._valid_init_expr, self._valid_bounds()]
        )

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

    def _is_plain_type(self):
        """Check if the data type is a plain type, accounting for arrays too."""
        data_type_str = self._data_type
        if is_type_string_array(data_type_str):
            data_type_str = get_type_string_of_array(data_type_str)
        return is_type_string_base_type(data_type_str)

    def is_plain_scxml(self) -> bool:
        """Check if the data type is a base type."""
        return self.check_validity() and self._is_plain_type()

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ros_declarations: ScxmlRosDeclarationsContainer,
    ) -> List["ScxmlData"]:
        # TODO: By using ROS declarations, we can add the support for the ROS types as well.
        # TODO: This is fine also in case it is an array of base types...
        if self._is_plain_type():
            return [self]
        data_type_def, _ = struct_declarations.get_data_type(self.get_name(), self.get_xml_origin())
        assert isinstance(data_type_def, StructDefinition), get_error_msg(
            self.get_xml_origin(),
            f"Information for data variable {self.get_name()} "
            + f"has unexpected type {data_type_def.__class__}.",
        )
        assert isinstance(self._expr, str), get_error_msg(
            self.get_xml_origin(), "We only support string init expr. for custom types."
        )
        expanded_data_exprs = data_type_def.get_expanded_expressions(self._expr)
        expanded_data_types = data_type_def.get_expanded_members()
        try:
            plain_data = [
                ScxmlData(
                    f"{self._id}.{key}",
                    expanded_data_exprs[key],
                    expanded_data_types[key],
                )
                for key in expanded_data_types
            ]
        except KeyError as e:
            log_error(
                self.get_xml_origin(),
                f"Error for struct field {e}.\n\tStruct def.: {expanded_data_types}"
                f"\n\tInit values: {expanded_data_exprs}.",
            )
        for single_data in plain_data:
            single_data._id = get_plain_variable_name(single_data._id, self.get_xml_origin())
        return plain_data

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

    def replace_strings_types_with_integer_arrays(self) -> None:
        base_type: str = self._data_type
        array_dims: List[Optional[int]] = []
        if is_type_string_array(self._data_type):
            base_type, array_dims = get_array_type_and_dimensions_from_string(self._data_type)
        check_assertion(
            is_type_string_base_type(base_type),
            self.get_xml_origin(),
            f"Unexpected type '{base_type}' found.",
        )
        check_assertion(
            isinstance(self._expr, str),
            self.get_xml_origin(),
            "Expected the default expr. to be a string at this point.",
        )
        if base_type == "string":
            # Handle the expected type
            array_dims.append(None)
            self._data_type = get_type_string_from_type_and_dimensions("uint32", array_dims)
            # Handle the default expression
            self._expr = convert_expression_with_string_literals(self._expr, self.get_xml_origin())
