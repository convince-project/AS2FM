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

from typing import List, Optional

from lxml import etree as ET

from as2fm.as2fm_common.common import is_comment
from as2fm.scxml_converter.scxml_entries import ScxmlBase, ScxmlData
from as2fm.scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from as2fm.scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok


class ScxmlDataModel(ScxmlBase):
    """This class represents the variables defined in the model."""

    def __init__(self, data_entries: List[ScxmlData] = None):
        # TODO: Check ScxmlData from scxml_helpers, for alternative parsing
        self._data_entries = data_entries

    @staticmethod
    def get_tag_name() -> str:
        return "datamodel"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlDataModel":
        """Create a ScxmlDataModel object from an XML tree."""
        assert_xml_tag_ok(ScxmlDataModel, xml_tree)
        data_entries = []
        prev_xml_comment: Optional[str] = None
        for data_entry_xml in xml_tree:
            if is_comment(data_entry_xml):
                prev_xml_comment = data_entry_xml.text.strip()
            else:
                data_entries.append(ScxmlData.from_xml_tree(data_entry_xml, prev_xml_comment))
                prev_xml_comment = None
        return ScxmlDataModel(data_entries)

    def get_data_entries(self) -> Optional[List[ScxmlData]]:
        return self._data_entries

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        for data_entry in self._data_entries:
            data_entry.update_bt_ports_values(bt_ports_handler)

    def check_validity(self) -> bool:
        if self._data_entries is not None:
            if not isinstance(self._data_entries, list):
                print("Error: SCXML datamodel: data entries are not a list.")
                return False
            for data_entry in self._data_entries:
                if not isinstance(data_entry, ScxmlData):
                    print(f"Error: SCXML datamodel: invalid data entry type {type(data_entry)}.")
                    return False
                if not data_entry.check_validity():
                    print(f"Error: SCXML datamodel: invalid data entry '{data_entry.get_name()}'.")
                    return False
        return True

    def as_xml(self, type_as_attribute: bool = True) -> Optional[ET.Element]:
        """
        Store the datamodel, containing all model's data entries, as an XML element.

        :param type_as_attribute: If True, store data types as arguments, if False as Comments
        """
        assert self.check_validity(), "SCXML: found invalid datamodel object."
        xml_datamodel = ET.Element(ScxmlDataModel.get_tag_name())
        for data_entry in self._data_entries:
            if not type_as_attribute:
                xml_datamodel.append(
                    ET.Comment(f" TYPE {data_entry.get_name()}:{data_entry.get_type_str()} ")
                )
            xml_datamodel.append(data_entry.as_xml(type_as_attribute))
        return xml_datamodel
