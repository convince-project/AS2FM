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
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import ScxmlBase, ScxmlData
from scxml_converter.scxml_entries.bt_utils import BtPortsHandler


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
        assert xml_tree.tag == ScxmlDataModel.get_tag_name(), \
            f"Error: SCXML datamodel: XML tag name is not {ScxmlDataModel.get_tag_name()}."
        data_entries_xml = xml_tree.findall("data")
        assert data_entries_xml is not None, "Error: SCXML datamodel: No data entries found."
        data_entries = []
        for data_entry_xml in data_entries_xml:
            data_entries.append(ScxmlData.from_xml_tree(data_entry_xml))
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

    def as_xml(self) -> Optional[ET.Element]:
        assert self.check_validity(), "SCXML: found invalid datamodel object."
        if self._data_entries is None or len(self._data_entries) == 0:
            return None
        xml_datamodel = ET.Element(ScxmlDataModel.get_tag_name())
        for data_entry in self._data_entries:
            xml_datamodel.append(data_entry.as_xml())
        return xml_datamodel
