# Copyright (c) 2025 - for information on the respective copyright owner
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


from typing import Dict

import lxml.etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import remove_namespace
from as2fm.as2fm_common.logging import get_error_msg, set_filepath_for_all_elements
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition


class XmlStructDefinition(StructDefinition):

    @staticmethod
    def from_xml_element(xml_element: XmlElement):
        """
        Creates an ScxmlDataType instance from an `struct` XML element.

        :param xml_element: The XML struct element defining the custom data type.
        :return: An instance of ScxmlDataType.
        """
        name = xml_element.get("id")
        members = {}
        for member in xml_element.findall("member"):
            member_name = member.get("id")
            member_type = member.get("type")
            assert member_name and member_type, get_error_msg(
                xml_element, "Member with no id or type defined."
            )
            members[member_name] = member_type
        assert len(members) > 0, get_error_msg(xml_element, "struct definition with no members.")
        instance = XmlStructDefinition(name, members)
        instance.set_xml_origin(xml_element)
        return instance

    @staticmethod
    def from_file(
        fname: str,
    ) -> Dict[str, "XmlStructDefinition"]:
        """
        Read the file containing custom type definitions.

        :param xml_path: Path of the XML file containing the top-level `types`-tag.
        """
        declarations = {}
        parser_wo_comments = ET.XMLParser(remove_comments=True)
        with open(fname, "r", encoding="utf-8") as f:
            xml = ET.parse(f, parser=parser_wo_comments)
        set_filepath_for_all_elements(xml.getroot(), fname)
        assert remove_namespace(xml.getroot().tag) == "types", get_error_msg(
            xml.getroot(), "The top-level XML element must be types."
        )
        for first_level in xml.getroot():
            assert remove_namespace(first_level.tag) == "struct", get_error_msg(
                first_level,
                "The children of the top-level XML element must be `struct`,"
                f"not {remove_namespace(first_level)}.",
            )
            loaded_struct = XmlStructDefinition.from_xml_element(first_level)
            declarations.update({loaded_struct.get_name(): loaded_struct})
        return declarations
