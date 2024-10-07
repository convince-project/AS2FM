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

from typing import Any, Union, Optional, Tuple
from xml.etree import ElementTree as ET

from as2fm_common.common import is_array_type

from scxml_converter.scxml_entries import (ScxmlBase, BtGetValueInputPort)

from scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok, get_xml_argument, read_value_from_xml_arg_or_child)
from scxml_converter.scxml_entries.utils import (
    convert_string_to_type, get_array_max_size, get_data_type_from_string, is_non_empty_string)


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
            comment_above: Optional[str]) -> Optional[Tuple[str, str]]:
        """Interpret the type of the data from the comment above the data tag.

        :param comment_above: The comment above the data tag (optional)
        :return: The type of the data, None if not found
        """
        if comment_above is None:
            return None
        # match string inside xml comment brackets
        type_match = re.search(r'TYPE\ (.+):(.+)', comment_above.strip())
        if type_match is None:
            return None
        return type_match.group(1), type_match.group(2)

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element, comment_above: Optional[str] = None) -> "ScxmlData":
        """Create a ScxmlData object from an XML tree."""
        assert_xml_tag_ok(ScxmlData, xml_tree)
        data_id = get_xml_argument(ScxmlData, xml_tree, "id")
        data_type = get_xml_argument(ScxmlData, xml_tree, "type", none_allowed=True)
        if data_type is None:
            comment_tuple = ScxmlData._interpret_type_from_comment_above(comment_above)
            assert comment_tuple is not None, f"Error: SCXML data: type of {data_id} not found."
            assert comment_tuple[0] == data_id, \
                "Error: SCXML data: unexpected ID in type in comment " \
                f"({comment_tuple[0]}!={data_id})."
            data_type = comment_tuple[1]
        data_expr = read_value_from_xml_arg_or_child(
            ScxmlData, xml_tree, "expr", (BtGetValueInputPort, str))
        lower_bound = read_value_from_xml_arg_or_child(
            ScxmlData, xml_tree, "lower_bound_incl", (BtGetValueInputPort, str), none_allowed=True)
        upper_bound = read_value_from_xml_arg_or_child(
            ScxmlData, xml_tree, "upper_bound_incl", (BtGetValueInputPort, str), none_allowed=True)
        return ScxmlData(data_id, data_expr, data_type, lower_bound, upper_bound)

    def __init__(
            self, id_: str, expr: ValidExpr, data_type: str,
            lower_bound: ValidBound = None, upper_bound: ValidBound = None):
        self._id: str = id_
        self._expr: ValidExpr = expr
        self._data_type: str = data_type
        self._lower_bound: ValidBound = lower_bound
        self._upper_bound: ValidBound = upper_bound

    def get_name(self) -> str:
        return self._id

    def get_type(self) -> type:
        python_type = get_data_type_from_string(self._data_type)
        assert python_type is not None, \
            f"Error: SCXML data: '{self._id}' has unknown type '{self._data_type}'."
        return python_type

    def get_array_max_size(self) -> Optional[int]:
        assert is_array_type(self.get_type()), \
            f"Error: SCXML data: '{self._id}' type is not an array."
        return get_array_max_size(self._data_type)

    def get_expr(self) -> ValidExpr:
        return self._expr

    def check_valid_bounds(self) -> bool:
        if all(bound is None for bound in [self._lower_bound, self._upper_bound]):
            # Nothing to check
            return True
        if self.get_type() not in (float, int):
            print(f"Error: SCXML data: '{self._id}' has bounds but has type {self._data_type}, "
                  "not a number.")
            return False
        lower_bound = None
        upper_bound = None
        if self._lower_bound is not None:
            lower_bound = convert_string_to_type(self._lower_bound, self._data_type)
        if self._upper_bound is not None:
            upper_bound = convert_string_to_type(self._upper_bound, self._data_type)
        if all(bound is not None for bound in [lower_bound, upper_bound]):
            if lower_bound > upper_bound:
                print(f"Error: SCXML data: 'lower_bound_incl' {lower_bound} is not smaller "
                      f"than 'upper_bound_incl' {upper_bound}.")
                return False
        return True

    def check_validity(self) -> bool:
        valid_id = is_non_empty_string(ScxmlData, "id", self._id)
        if get_data_type_from_string(self._data_type) is None:
            print(f"Error: SCXML data: '{self._id}' has unknown type '{self._data_type}'.")
            return False
        if isinstance(self._expr, str):
            valid_expr = is_non_empty_string(ScxmlData, "expr", self._expr)
        else:
            valid_expr = isinstance(self._expr, (int, float, bool))
            if not valid_expr:
                print(f"Error: SCXML data: '{self._id}': initial expression ",
                      f"evaluates to an invalid type '{type(self._expr)}'.")
        valid_bounds = self.check_valid_bounds()
        return valid_id and valid_expr and valid_bounds

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid data object."
        xml_data = ET.Element(ScxmlData.get_tag_name(),
                              {"id": self._id, "expr": str(self._expr), "type": self._data_type})
        if self._lower_bound is not None:
            xml_data.set("lower_bound_incl", str(self._lower_bound))
        if self._upper_bound is not None:
            xml_data.set("upper_bound_incl", str(self._upper_bound))
        return xml_data

    def as_plain_scxml(self, _):
        raise RuntimeError("Error: SCXML data: unexpected call to as_plain_scxml.")

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        if isinstance(self._expr, BtGetValueInputPort):
            self._expr = bt_ports_handler.get_in_port_value(self._expr.get_key_name())
        if isinstance(self._lower_bound, BtGetValueInputPort):
            self._lower_bound = bt_ports_handler.get_in_port_value(self._lower_bound.get_key_name())
        if isinstance(self._upper_bound, BtGetValueInputPort):
            self._upper_bound = bt_ports_handler.get_in_port_value(self._upper_bound.get_key_name())
