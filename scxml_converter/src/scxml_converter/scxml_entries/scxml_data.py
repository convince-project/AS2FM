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

from typing import Any
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import ScxmlBase
from scxml_converter.scxml_entries.utils import SCXML_DATA_STR_TO_TYPE


class ScxmlData(ScxmlBase):
    """This class represents the variables defined in the model."""

    @staticmethod
    def get_tag_name() -> str:
        return "data"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlData":
        """Create a ScxmlData object from an XML tree."""
        assert xml_tree.tag == ScxmlData.get_tag_name(), \
            f"Error: SCXML data: XML tag name is not {ScxmlData.get_tag_name()}."
        data_id = xml_tree.attrib.get("id")
        assert data_id is not None, "Error: SCXML data: 'id' not found."
        data_expr = xml_tree.attrib.get("expr")
        assert data_expr is not None, "Error: SCXML data: 'expr' not found."
        data_type = xml_tree.attrib.get("type")
        assert data_type is not None, "Error: SCXML data: 'type' not found."
        lower_bound = xml_tree.attrib.get("lower_bound_incl", None)
        upper_bound = xml_tree.attrib.get("upper_bound_incl", None)
        return ScxmlData(data_id, data_expr, data_type, lower_bound, upper_bound)

    def __init__(
            self, id: str, expr: str, data_type: str,
            lower_bound: Any = None, upper_bound: Any = None):
        self._id = id
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
        validity = True
        # ID
        if not (isinstance(self._id, str) and len(self._id) > 0):
            print(f"Error: SCXML data: 'id' {self._id} is not valid.")
            validity = False
        # Expression
        if not (isinstance(self._expr, str) and len(self._expr) > 0):
            print(f"Error: SCXML data: 'expr' {self._expr} is not valid.")
            validity = False
        # Data type
        if not (isinstance(self._data_type, str) and self._data_type in SCXML_DATA_STR_TO_TYPE):
            print(f"Error: SCXML data: 'type' {self._data_type} is not valid.")
            validity = False
        type_of_data = SCXML_DATA_STR_TO_TYPE[self._data_type]
        # Lower bound
        if self._lower_bound is not None:
            if not isinstance(self._lower_bound, type_of_data):
                print(f"Error: SCXML data: 'lower_bound_incl' type {self._lower_bound} is invalid.")
                validity = False
        # Upper bound
        if self._upper_bound is not None:
            if not isinstance(self._upper_bound, type_of_data):
                print(f"Error: SCXML data: 'upper_bound_incl' type {self._upper_bound} is invalid.")
                validity = False
        # Check if lower bound is smaller than upper bound
        if validity and self._upper_bound is not None and self._lower_bound is not None:
            if self._lower_bound >= self._upper_bound:
                print(f"Error: SCXML data: 'lower_bound_incl' {self._lower_bound} is not smaller "
                      f"than 'upper_bound_incl' {self._upper_bound}.")
                validity = False
        return validity

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid data object."
        xml_data = ET.Element(ScxmlData.get_tag_name(),
                              {"id": self._id, "expr": self._expr, "type": self._data_type})
        if self._lower_bound is not None:
            xml_data.set("lower_bound_incl", str(self._lower_bound_incl))
        if self._upper_bound is not None:
            xml_data.set("upper_bound_incl", str(self._upper_bound))
        return xml_data
