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

from typing import Any, Union, Optional
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (ScxmlBase, BtGetValueInputPort)

from scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok, get_xml_argument, read_value_from_xml_arg_or_child)
from scxml_converter.scxml_entries.utils import SCXML_DATA_STR_TO_TYPE, is_non_empty_string


ValidExpr = Union[BtGetValueInputPort, str, int, float]


def get_valid_entry_data_type(
        value: Optional[Union[str, int, float]], data_type: str) -> Optional[Any]:
    """
    Convert a value to the provided data type. Raise if impossible.
    """
    if value is None:
        return None
    assert data_type in SCXML_DATA_STR_TO_TYPE, \
        f"Error: SCXML conversion of data entry: Unknown data type {data_type}."
    if isinstance(value, str):
        assert len(value) > 0, "Error: SCXML conversion of data bounds: Empty string."
        return SCXML_DATA_STR_TO_TYPE[data_type](value)
    assert isinstance(value, SCXML_DATA_STR_TO_TYPE[data_type]), \
        f"Error: SCXML conversion of data entry: Expected {data_type}, but got {type(value)}."
    return value


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
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlData":
        """Create a ScxmlData object from an XML tree."""
        assert_xml_tag_ok(ScxmlData, xml_tree)
        data_id = get_xml_argument(ScxmlData, xml_tree, "id")
        data_type = get_xml_argument(ScxmlData, xml_tree, "type")
        data_expr = read_value_from_xml_arg_or_child(ScxmlData, xml_tree, "expr",
                                                     (BtGetValueInputPort, str))
        lower_bound = read_value_from_xml_arg_or_child(ScxmlData, xml_tree, "lower_bound_incl",
                                                       (BtGetValueInputPort, str), True)
        upper_bound = read_value_from_xml_arg_or_child(ScxmlData, xml_tree, "upper_bound_incl",
                                                       (BtGetValueInputPort, str), True)
        return ScxmlData(data_id, data_expr, data_type, lower_bound, upper_bound)

    def __init__(
            self, id_: str, expr: ValidExpr, data_type: str,
            lower_bound: Optional[ValidExpr] = None, upper_bound: Optional[ValidExpr] = None):
        self._id = id_
        self._expr = expr
        self._data_type = data_type
        self._lower_bound = lower_bound
        self._upper_bound = upper_bound

    def get_name(self) -> str:
        return self._id

    def get_type(self) -> type:
        return SCXML_DATA_STR_TO_TYPE[self._data_type]

    def get_expr(self) -> str:
        return self._expr

    def check_validity(self) -> bool:
        valid_id = is_non_empty_string(ScxmlData, "id", self._id)
        valid_expr = is_non_empty_string(ScxmlData, "expr", self._expr)
        valid_type = is_non_empty_string(ScxmlData, "type", self._data_type) and \
            self._data_type in SCXML_DATA_STR_TO_TYPE
        if not (valid_bound(self._lower_bound) and valid_bound(self._upper_bound)):
            print("Error: SCXML data: invalid lower_bound_incl or upper_bound_incl. "
                  f"lower_bound_incl: {self._lower_bound}, upper_bound_incl: {self._upper_bound}")
            return False
        lower_bound = get_valid_entry_data_type(self._lower_bound, self._data_type)
        upper_bound = get_valid_entry_data_type(self._upper_bound, self._data_type)
        valid_bounds = True
        if lower_bound is not None and upper_bound is not None:
            valid_bounds = lower_bound <= upper_bound
        if not valid_bounds:
            print(f"Error: SCXML data: 'lower_bound_incl' {lower_bound} is not smaller "
                  f"than 'upper_bound_incl' {upper_bound}.")
        return valid_id and valid_expr and valid_type and valid_bounds

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid data object."
        xml_data = ET.Element(ScxmlData.get_tag_name(),
                              {"id": self._id, "expr": self._expr, "type": self._data_type})
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
