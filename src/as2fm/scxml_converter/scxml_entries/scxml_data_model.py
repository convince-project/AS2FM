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
Container for the variables defined in the SCXML model. In XML, it has the tag `datamodel`.
"""

from typing import Dict, List, Optional

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import is_comment
from as2fm.as2fm_common.logging import get_error_msg, log_error
from as2fm.scxml_converter.scxml_entries import ScxmlBase, ScxmlData
from as2fm.scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from as2fm.scxml_converter.scxml_entries.ros_utils import ScxmlRosDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok
from as2fm.scxml_converter.xml_data_types.xml_struct_definition import XmlStructDefinition


class ScxmlDataModel(ScxmlBase):
    """This class represents the variables defined in the model."""

    def __init__(self, data_entries: Optional[List[ScxmlData]] = None):
        if data_entries is None:
            data_entries = []
        self._data_entries: List[ScxmlData] = data_entries

    @staticmethod
    def get_tag_name() -> str:
        return "datamodel"

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, custom_data_types: Dict[str, XmlStructDefinition]
    ) -> "ScxmlDataModel":
        """Create a ScxmlDataModel object from an XML tree."""
        assert_xml_tag_ok(ScxmlDataModel, xml_tree)
        data_entries = []
        prev_xml_comment: Optional[str] = None
        for data_entry_xml in xml_tree:
            if is_comment(data_entry_xml):
                prev_xml_comment = data_entry_xml.text.strip()
            else:
                de = ScxmlData.from_xml_tree(
                    data_entry_xml, custom_data_types, comment_above=prev_xml_comment
                )
                assert isinstance(de, ScxmlData), get_error_msg(
                    xml_tree, "Must be a ScxmlData instance."
                )
                data_entries.append(de)
                prev_xml_comment = None
        return ScxmlDataModel(data_entries)

    def get_data_entries(self) -> List[ScxmlData]:
        return self._data_entries

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        for data_entry in self._data_entries:
            data_entry.update_bt_ports_values(bt_ports_handler)

    def check_validity(self) -> bool:
        xml_origin = self.get_xml_origin()
        if not isinstance(self._data_entries, list):
            log_error(xml_origin, "Error: SCXML datamodel: data entries are not a list.")
            return False
        for data_entry in self._data_entries:
            if not isinstance(data_entry, ScxmlData):
                log_error(
                    xml_origin,
                    f"Error: SCXML datamodel: invalid data entry type {type(data_entry)}.",
                )
                return False
            if not data_entry.check_validity():
                log_error(
                    xml_origin,
                    f"Error: SCXML datamodel: invalid data entry '{data_entry.get_name()}'.",
                )
                return False
        return True

    def is_plain_scxml(self) -> bool:
        """Check if all data entries are already plain-scxml (using only base types)."""
        return self.check_validity() and all(data.is_plain_scxml() for data in self._data_entries)

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ros_declarations: ScxmlRosDeclarationsContainer,
    ) -> List["ScxmlDataModel"]:
        plain_data_entries = []
        for data_entry in self._data_entries:
            plain_data_entries.extend(
                data_entry.as_plain_scxml(struct_declarations, ros_declarations)
            )
        return [ScxmlDataModel(plain_data_entries)]

    def as_xml(self, type_as_attribute: bool = True) -> Optional[XmlElement]:
        """
        Store the datamodel, containing all model's data entries, as an XML element.

        :param type_as_attribute: If True, store data types as arguments, if False as Comments
        """
        assert self.check_validity(), get_error_msg(
            self.get_xml_origin(), "SCXML: found invalid datamodel object."
        )
        xml_datamodel = ET.Element(ScxmlDataModel.get_tag_name())
        for data_entry in self._data_entries:
            if not type_as_attribute:
                xml_datamodel.append(
                    ET.Comment(f" TYPE {data_entry.get_name()}:{data_entry.get_type_str()} ")
                )
            xml_datamodel.append(data_entry.as_xml(type_as_attribute))
        return xml_datamodel
