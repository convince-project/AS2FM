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

from as2fm.as2fm_common.common import remove_namespace
from as2fm.as2fm_common.logging import get_error_msg, set_filepath_for_all_elements
from as2fm.scxml_converter.xml_data_types.xml_struct_definition import XmlStructDefinition


def read_types_file(
    xml_path: str,
) -> Dict[str, XmlStructDefinition]:
    """
    Read the file containing custom type definitions.

    :param xml_path: Path of the XML file containing the top-level `types`-tag.
    """
    declarations = {}
    parser_wo_comments = ET.XMLParser(remove_comments=True)
    with open(xml_path, "r", encoding="utf-8") as f:
        xml = ET.parse(f, parser=parser_wo_comments)
    set_filepath_for_all_elements(xml.getroot(), xml_path)
    assert remove_namespace(xml.getroot().tag) == "types", get_error_msg(
        xml.getroot(), "The top-level XML element must be types."
    )
    for first_level in xml.getroot():
        assert remove_namespace(first_level.tag) == "struct", get_error_msg(
            first_level,
            "The children of the top-level XML element must be `struct`,"
            f"not {remove_namespace(first_level)}.",
        )
        loaded_struct = XmlStructDefinition.from_xml(first_level)
        declarations.update({loaded_struct.get_name(): loaded_struct})
    return declarations
