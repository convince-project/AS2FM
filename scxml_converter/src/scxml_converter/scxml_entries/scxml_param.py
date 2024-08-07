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

from typing import Optional
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import ScxmlBase


class ScxmlParam(ScxmlBase):
    """This class represents a single parameter."""

    def __init__(self, name: str, *, expr: Optional[str] = None, location: Optional[str] = None):
        # TODO: We might need types in ScxmlParams as well, for later converting them to JANI.
        self._name = name
        self._expr = expr
        self._location = location

    @staticmethod
    def get_tag_name() -> str:
        return "param"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlParam":
        """Create a ScxmlParam object from an XML tree."""
        assert xml_tree.tag == ScxmlParam.get_tag_name(), \
            f"Error: SCXML param: XML tag name is not {ScxmlParam.get_tag_name()}."
        name = xml_tree.attrib.get("name")
        assert name is not None and len(name) > 0, "Error: SCXML param: name is not valid."
        expr = xml_tree.attrib.get("expr")
        location = xml_tree.attrib.get("location")
        assert not (expr is not None and location is not None), \
            "Error: SCXML param: expr and location are both set."
        assert expr is not None or location is not None, \
            "Error: SCXML param: expr and location are both unset."
        return ScxmlParam(name, expr=expr, location=location)

    def get_name(self) -> str:
        return self._name

    def get_expr(self) -> Optional[str]:
        return self._expr

    def get_location(self) -> Optional[str]:
        return self._location

    def check_validity(self) -> bool:
        valid_name = len(self._name) > 0
        if not valid_name:
            print("Error: SCXML param: name is not valid")
        valid_expr = isinstance(self._expr, str) and len(self._expr) > 0 and self._location is None
        valid_location = isinstance(self._location, str) and len(
            self._location) > 0 and self._expr is None
        # Print possible errors
        if self._expr is not None:
            if not isinstance(self._expr, str) or len(self._expr) == 0:
                print("Error: SCXML param: expr is not valid")
        if self._location is not None:
            if not isinstance(self._location, str) or len(self._location) == 0:
                print("Error: SCXML param: location is not valid")
        if self._expr is not None and self._location is not None:
            print("Error: SCXML param: expr and location are both set")
        if self._expr is None and self._location is None:
            print("Error: SCXML param: expr and location are both unset")

        return valid_name and (valid_expr or valid_location)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid param."
        xml_param = ET.Element(ScxmlParam.get_tag_name(), {"name": self._name})
        if self._expr is not None:
            xml_param.set("expr", self._expr)
        if self._location is not None:
            xml_param.set("location", self._location)
        return xml_param
