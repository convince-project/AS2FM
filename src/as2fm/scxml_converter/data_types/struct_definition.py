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

from typing import Any, Dict, List, Optional, Type, Union

from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.array_type import ArrayInfo
from as2fm.as2fm_common.ast_utils import ast_expression_to_string
from as2fm.as2fm_common.common import ValidPlainScxmlTypes
from as2fm.as2fm_common.ecmascript_interpretation import (
    get_object_expression_as_dict,
    make_ast_array_expression,
)
from as2fm.as2fm_common.logging import check_assertion, get_error_msg
from as2fm.scxml_converter.data_types.type_utils import (
    get_array_type_and_dimensions_from_string,
    is_type_string_array,
    is_type_string_base_type,
)

ExpandedDataStructType = Dict[str, Union[str, Dict[str, "ExpandedDataStructType"]]]

# Members (= params) of object can be base types or arrays
AllowedMemberTypes = Union[Type[ValidPlainScxmlTypes], ArrayInfo]


class StructDefinition:
    """
    Represents a custom data structs defined in SCXML, loaded from a file, for example XML.
    """

    def __init__(self, name: str, members: dict):
        """
        Initializes the ScxmlDataType instance.

        :param name: The name of the custom data type.
        :param members: A dictionary where keys are member names and values are their types.
        """
        self._name = name
        self._members: Dict[str, str] = members
        # This needs to be generated once all struct definitions are loaded.
        self._members_list: Optional[Dict[str, str]] = None

    @staticmethod
    def from_file(fname: str):
        """
        Implement this method depending on the source of the type definitions
        """
        raise NotImplementedError("This must be implemented in the child class.")

    def get_name(self) -> str:
        """Get the name of the custom struct."""
        return self._name

    def set_xml_origin(self, xml_origin: XmlElement):
        """Set the xml_element this object was made from."""
        self.xml_origin = xml_origin

    def get_xml_origin(self) -> Optional[XmlElement]:
        """Get the xml_element this object was made from."""
        try:
            return self.xml_origin
        except AttributeError:
            return None

    def get_members(self) -> Dict[str, str]:
        """Get members and their type. e.g. `{'x': 'int', 's': 'Point2D'}`."""
        return self._members

    def get_expanded_members(self) -> Dict[str, str]:
        """
        Return a dictionary containing the members belonging to that struct and the related types.

        E.g., for a Point2D, the expanded members are {'x': float32, 'y': float32}
        For a Polygon, the expanded members are {'points.x': float32[], 'points.y': float32[]}
        """
        assert self._members_list is not None
        return self._members_list

    def expand_members(self, all_structs: Dict[str, "StructDefinition"]):
        """
        Expands the members dictionary to resolve all fields to their base types.

        :param all_structs: A dictionary of all ScxmlDataStruct instances by their names.
        :param array_signature: Array information to be appended to the last, expanded base entry.
        """
        if self._members_list is not None:
            return
        self._members_list = {}
        for member_name, member_type in self._members.items():
            potential_base_type = member_type
            if is_type_string_base_type(member_type):
                self._members_list.update({member_name: member_type})
            if is_type_string_array(member_type):
                array_type_str, array_max_sizes = get_array_type_and_dimensions_from_string(
                    member_type
                )
                potential_base_type = array_type_str
                if is_type_string_base_type(array_type_str):
                    self._members_list.update({member_name: member_type})
            if not is_type_string_base_type(potential_base_type):
                member_type_proc = member_type
                array_info = ""
                if is_type_string_array(member_type):
                    array_type_str, array_max_sizes = get_array_type_and_dimensions_from_string(
                        member_type
                    )
                    check_assertion(
                        len(array_max_sizes) == 1,
                        self.get_xml_origin(),
                        "Expected only 1D arrays in complex struct definitions.",
                    )
                    array_size = array_max_sizes[0]
                    array_info = "[]" if array_size is None else f"[{array_size}]"
                    member_type_proc = array_type_str
                if member_type_proc not in all_structs and not is_type_string_base_type(
                    member_type_proc
                ):
                    raise ValueError(
                        get_error_msg(
                            self.get_xml_origin(),
                            f"Unknown type '{member_type_proc}' for member "
                            f"'{member_name}' in struct '{self._name}'.",
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

    def get_expanded_expressions(self, expr: str) -> Dict[str, str]:
        """Extracts all object keys from a given ecmascript object definition."""
        if self._members_list is None:
            raise ValueError(f"Struct '{self._name}' has not been expanded yet.")
        # Interpret the expression
        expr_type = get_object_expression_as_dict(expr)
        flat_dict = self._flatten_object_dict(expr_type, "")
        for key in flat_dict:
            flat_dict[key] = ast_expression_to_string(flat_dict[key])
        return flat_dict

    def _flatten_object_dict(
        self, object_to_convert: Dict[str, Any], prefix: str
    ) -> Dict[str, Any]:
        """
        Expand an input dictionary to have all possible entries in the first level.
        """
        ret_dict: Dict[str, str] = {}
        for obj_key, obj_val in object_to_convert.items():
            obj_full_name = obj_key if prefix == "" else f"{prefix}.{obj_key}"
            if isinstance(obj_val, list):
                if len(obj_val) > 0:
                    assert not isinstance(
                        obj_val[0], list
                    ), "An object list entry can only contain other objects or base types."
                    if isinstance(obj_val[0], dict):
                        # List of dictionaries
                        expanded_dicts_list: List[Dict[str, str]] = []
                        for single_obj_dict in obj_val:
                            # Ensure we are not dict and base types in the same list
                            assert isinstance(single_obj_dict, dict), "Expected only dict entries."
                            expanded_dicts_list.append(
                                self._flatten_object_dict(single_obj_dict, obj_full_name)
                            )
                        # Check single_obj_dict[0] has all sub-keys of obj_full_name
                        self._validate_object(expanded_dicts_list[0], obj_full_name)
                        # Make sure that array access is at the end
                        for obj_sub_key in expanded_dicts_list[0]:
                            # Make a list of all entries related to a single-sub-key
                            single_key_list = [
                                single_dict[obj_sub_key] for single_dict in expanded_dicts_list
                            ]
                            # Write them in the dictionary to be returned
                            self._update_instance_dictionary(ret_dict, obj_sub_key, single_key_list)
                    else:
                        # List of base types (AST nodes)
                        self._update_instance_dictionary(ret_dict, obj_full_name, obj_val)
                else:
                    # Empty list
                    self._update_instance_dictionary(ret_dict, obj_full_name, obj_val)
            elif isinstance(obj_val, dict):
                assert len(obj_val) > 0, "Unexpected empty dictionary in value definition."
                ret_dict.update(self._flatten_object_dict(obj_val, obj_full_name))
            # Neither a dict nor a list: just an AST (base) expression
            else:
                # Any other base type
                self._update_instance_dictionary(ret_dict, obj_full_name, obj_val)
        return ret_dict

    def _update_instance_dictionary(self, instance_dict, entry_key, entry_value):
        """
        Add the value provided in entry_value to instance_dict.

        :param instance_dict: The dict containing the fields of the processed instance
        :param entry_key: The key of the entry to add to instance_dict
        :param entry_value: The value we want to add to instance_dict
        """
        if entry_key in self._members_list:
            assert entry_key not in instance_dict, f"Found duplicate key '{entry_key}'."
            if isinstance(entry_value, list):
                instance_dict[entry_key] = make_ast_array_expression(entry_value)
            else:
                # This is a base type, expected to be already an AST node
                instance_dict[entry_key] = entry_value
        else:
            # We couldn't find the complete entry key: check if it is a valid prefix
            sub_keys = self._get_list_keys_with_prefix(entry_key)
            assert len(sub_keys) > 0, get_error_msg(
                self.get_xml_origin(),
                f"Provided key '{entry_key}' is incompatible with {self._name} type."
                f"Expected keys shall be in {[x for x in self._members_list.keys()]} set.",
            )
            # Incomplete key shall be used only with empty lists
            assert (
                isinstance(entry_value, list) and len(entry_value) == 0
            ), f"The provided incomplete key '{entry_key}' can be used only with empty lists."
            for sub_key in sub_keys:
                assert sub_key not in instance_dict, f"Error: found duplicate key {sub_key}."
                instance_dict[sub_key] = make_ast_array_expression([])

    def _get_list_keys_with_prefix(self, prefix: str):
        return [
            matching_key
            for matching_key in self.get_expanded_members()
            if matching_key.startswith(prefix)
        ]

    def _validate_object(self, obj_instance: Dict[str, Any], prefix: str):
        expected_keys = self._get_list_keys_with_prefix(prefix)
        assert len(obj_instance) == len(expected_keys)
        for expected_key in expected_keys:
            assert (
                expected_key in obj_instance
            ), f"The object {obj_instance} has no key {expected_key}"
