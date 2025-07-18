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

from typing import Dict, List, Optional, Type

from lxml.etree import _Element as XmlElement
from typing_extensions import Self

from as2fm.scxml_converter.data_types.struct_definition import StructDefinition


class ScxmlBase:
    """This class is the base class for all SCXML entries."""

    @staticmethod
    def get_tag_name() -> str:
        """Get the tag name of the XML element."""
        raise NotImplementedError

    @classmethod
    def from_xml_tree(
        cls: Type[Self],
        xml_tree: XmlElement,
        custom_data_types: Dict[str, StructDefinition],
        **kwargs,
    ) -> Self:
        """External interface to create a ScxmlBase object from an XML tree."""
        instance = cls.from_xml_tree_impl(xml_tree, custom_data_types, **kwargs)
        instance.set_xml_origin(xml_tree)
        instance.set_custom_data_types(custom_data_types)
        return instance

    @classmethod
    def from_xml_tree_impl(
        cls: Type[Self], xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
    ) -> Self:
        """Child-specific implementation to create a ScxmlBase object from an XML tree."""
        raise NotImplementedError

    def set_custom_data_types(self, custom_data_types: Dict[str, StructDefinition]):
        """Save container with custom data types."""
        self.custom_data_types = custom_data_types

    def get_custom_data_types(self) -> Dict[str, StructDefinition]:
        """Get the container with custom data types."""
        return self.custom_data_types

    def set_xml_origin(self, xml_origin: XmlElement):
        """Set the xml_element this object was made from."""
        self.xml_origin = xml_origin

    def get_xml_origin(self) -> Optional[XmlElement]:
        """Get the xml_element this object was made from."""
        try:
            return self.xml_origin
        except AttributeError:
            return None

    def check_validity(self) -> bool:
        """Check if the object is valid."""
        raise NotImplementedError

    def update_bt_ports_values(self, bt_ports_handler):
        """Update the values of potential entries making use of BT ports."""
        raise NotImplementedError

    def is_plain_scxml(self) -> bool:
        """Check if the object is compatible with the plain SCXML standard."""
        raise NotImplementedError

    def as_plain_scxml(self, struct_declarations, ros_declarations) -> List:
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
