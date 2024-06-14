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
Container for a single SCXML variable assignment. In XML, it has the tag `assign`.
"""

from xml.etree import ElementTree as ET


class ScxmlAssign:
    """This class represents a variable assignment."""
    def __init__(self, name: str, expr: str):
        self.name = name
        self.expr = expr

    def check_validity(self) -> bool:
        # TODO: Check that the location to assign exists in the datamodel
        valid_name = isinstance(self.name, str) and len(self.name) > 0
        valid_expr = isinstance(self.expr, str) and len(self.expr) > 0
        if not valid_name:
            print("Error: SCXML assign: name is not valid.")
        if not valid_expr:
            print("Error: SCXML assign: expr is not valid.")
        return valid_name and valid_expr

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid assign object."
        return ET.Element('assign', {"location": self.name, "expr": self.expr})
