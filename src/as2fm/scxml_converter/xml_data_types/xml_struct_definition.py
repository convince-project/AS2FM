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

from typing import Any, Dict, Optional, Union

from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.ecmascript_interpretation import interpret_non_base_ecma_script_expr
from as2fm.as2fm_common.logging import get_error_msg
from as2fm.scxml_converter.xml_data_types.type_utils import (
    get_array_max_size,
    get_type_string_of_array,
    is_type_string_array,
    is_type_string_base_type,
)

ExpandedDataStructType = Dict[str, Union[str, Dict[str, "ExpandedDataStructType"]]]


class XmlStructDefinition:
    """
    Represents a custom data type defined in SCXML, loaded from an XML element.
    """

    def __init__(self, name: str, members: dict):
        """
        Initializes the ScxmlDataType instance.

        :param name: The name of the custom data type.
        :param members: A dictionary where keys are member names and values are their types.
        """
        self.name = name
        self.members: Dict[str, str] = members
        # This needs to be generated once all struct definitions are loaded.
        self._members_list: Optional[Dict[str, str]] = None

    @classmethod
    def from_xml(cls, xml_element: XmlElement):
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
        instance = cls(name, members)
        instance.set_xml_origin(xml_element)

    def set_xml_origin(self, xml_origin: XmlElement):
        """Set the xml_element this object was made from."""
        self.xml_origin = xml_origin

    def get_xml_origin(self) -> Optional[XmlElement]:
        """Get the xml_element this object was made from."""
        try:
            return self.xml_origin
        except AttributeError:
            return None

    def get_expanded_members(self) -> Dict[str, str]:
        assert self._members_list is not None
        return self._members_list

    def expand_members(self, all_structs: Dict[str, "XmlStructDefinition"]):
        """
        Expands the members dictionary to resolve all fields to their base types.

        :param all_structs: A dictionary of all ScxmlDataStruct instances by their names.
        :param array_signature: Array information to be appended to the last, expanded base entry.
        """
        if self._members_list is not None:
            return
        self._members_list = {}
        for member_name, member_type in self.members.items():
            if is_type_string_base_type(member_type):
                self._members_list.update({member_name: member_type})
            else:
                member_type_proc = member_type
                array_info = ""
                if is_type_string_array(member_type):
                    array_size = get_array_max_size(member_type)
                    array_info = "[]" if array_size is None else f"[{array_size}]"
                    member_type_proc = get_type_string_of_array(member_type)
                if member_type_proc not in all_structs:
                    raise ValueError(
                        get_error_msg(
                            self.get_xml_origin(),
                            f"Unknown type '{member_type_proc}' for member "
                            f"'{member_name}' in struct '{self.name}'.",
                        )
                    )
                all_structs[member_type_proc].expand_members(all_structs)
                for child_m_name, child_m_type in (
                    all_structs[member_type_proc].get_expanded_members().items()
                ):
                    # We need to add member's array bit before the ones from previous expansions
                    array_bracket_idx = child_m_type.find("[")
                    if array_bracket_idx < 0:
                        expanded_type = child_m_type + array_info
                    else:
                        child_type_only = child_m_type[:array_bracket_idx]
                        child_array_info = child_m_type[array_bracket_idx:]
                        expanded_type = child_type_only + array_info + child_array_info
                    self._members_list.update({f"{member_name}.{child_m_name}": expanded_type})

    def get_instance_from_expression(self, expr: str) -> Dict[str, Any]:
        """
        Creates an instance of the data structure from an ECMAScript-like expression.

        :param expr: The expression defining the instance.
        :return: A dictionary representing the instance.
        """
        if self._members_list is None:
            raise ValueError(f"Struct '{self.name}' has not been expanded yet.")

        # Interpret the expression
        interpreted_expr = interpret_non_base_ecma_script_expr(expr)
        if interpreted_expr:
            pass
        # TODO: All
        return {}
