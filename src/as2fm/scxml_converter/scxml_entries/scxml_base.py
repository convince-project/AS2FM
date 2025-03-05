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
Base SCXML class, defining the methods all SCXML entries shall implement.
"""

from typing import Optional

from lxml import etree as ET


class ScxmlBase:
    """This class is the base class for all SCXML entries."""

    @staticmethod
    def get_tag_name() -> str:
        """Get the tag name of the XML element."""
        raise NotImplementedError

    @classmethod
    def from_xml_tree(cls, xml_tree: ET.Element) -> "ScxmlBase":
        """External interface to create a ScxmlBase object from an XML tree."""
        instance = cls.from_xml_tree_impl(xml_tree)
        instance.set_xml_tree(xml_tree)
        return instance

    @classmethod
    def from_xml_tree_impl(cls, xml_tree: ET.Element) -> "ScxmlBase":
        """Child-specific implementation to create a ScxmlBase object from an XML tree."""
        raise NotImplementedError

    def set_xml_tree(self, xml_tree: ET.Element):
        """Set the xml_element this object was made from"""
        self.xml_tree = xml_tree

    def get_xml_tree(self) -> Optional[ET.Element]:
        """Get the xml_element this object was made from."""
        try:
            return self.xml_tree
        except AttributeError:
            return None

    def check_validity(self) -> bool:
        """Check if the object is valid."""
        raise NotImplementedError

    def update_bt_ports_values(self, bt_ports_handler):
        """Update the values of potential entries making use of BT ports."""
        raise NotImplementedError

    def as_plain_scxml(self, ros_declarations) -> "ScxmlBase":
        """Convert the object to its plain SCXML  version."""
        raise NotImplementedError

    def as_xml(self):
        """Convert the object to an XML element."""
        raise NotImplementedError

    def get_body(self):
        """Get the body of the object."""
        raise NotImplementedError

    def get_id(self) -> str:
        """Get the ID of the object."""
        raise NotImplementedError
