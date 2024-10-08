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

from typing import Iterable, List, Optional, Type, Union

import lxml.etree as ET

from as2fm.as2fm_common.common import is_comment
from as2fm.scxml_converter.scxml_entries import ScxmlBase


def assert_xml_tag_ok(scxml_type: Type[ScxmlBase], xml_tree: ET.Element):
    """Ensures the xml_tree we are trying to parse has the expected name."""
    assert (
        xml_tree.tag == scxml_type.get_tag_name()
    ), f"SCXML conversion: Expected tag {scxml_type.get_tag_name()}, but got {xml_tree.tag}"


def get_xml_argument(
    scxml_type: Type[ScxmlBase],
    xml_tree: ET.Element,
    arg_name: str,
    *,
    none_allowed=False,
    empty_allowed=False,
) -> Optional[str]:
    """Load an argument from the xml tree's root tag."""
    arg_value = xml_tree.get(arg_name)
    error_prefix = f"SCXML conversion of {scxml_type.get_tag_name()}"
    if arg_value is None:
        assert none_allowed, f"{error_prefix}: Expected argument {arg_name} in {xml_tree.tag}"
    elif len(arg_value) == 0:
        assert (
            empty_allowed
        ), f"{error_prefix}: Expected non-empty argument {arg_name} in {xml_tree.tag}"
    return arg_value


def get_children_as_scxml(
    xml_tree: ET.Element, scxml_types: Iterable[Type[ScxmlBase]]
) -> List[ScxmlBase]:
    """
    Load the children of the xml tree as scxml entries.

    :param xml_tree: The xml tree to read the children from.
    :param scxml_types: The classes to read from the children. All others will be discarded.
    :return: A list of scxml entries.
    """
    scxml_list = []
    tag_to_type = {scxml_type.get_tag_name(): scxml_type for scxml_type in scxml_types}
    for child in xml_tree:
        if is_comment(child):
            continue
        if child.tag in tag_to_type:
            scxml_list.append(tag_to_type[child.tag].from_xml_tree(child))
    return scxml_list


def read_value_from_xml_child(
    xml_tree: ET.Element,
    child_tag: str,
    valid_types: Iterable[Type[Union[ScxmlBase, str]]],
    *,
    none_allowed: bool = False,
) -> Optional[Union[str, ScxmlBase]]:
    """
    Try to read the value of a child tag from the xml tree. If the child is not found, return None.
    """
    xml_child = xml_tree.findall(child_tag)
    if xml_child is None or len(xml_child) == 0:
        if not none_allowed:
            print(f"Error: reading from {xml_tree.tag}: Cannot find child '{child_tag}'.")
        return None
    if len(xml_child) > 1:
        print(f"Error: reading from {xml_tree.tag}: multiple children '{child_tag}', expected one.")
        return None
    tag_children = [child for child in xml_child[0] if not is_comment(child)]
    n_tag_children = len(tag_children)
    if n_tag_children == 0 and str in valid_types:
        # Try to read the text value
        text_value = xml_child[0].text
        if text_value is None or len(text_value) == 0:
            print(f"Error: reading from {xml_tree.tag}: Child '{child_tag}' has no text value.")
            return None
        return text_value
    if n_tag_children > 1:
        print(f"Error: reading from {xml_tree.tag}: Child '{child_tag}' has multiple children:")
        for child in tag_children:
            print(f"\t- {child.tag}")
        return None
    # Remove string from valid types, if present
    valid_types = tuple(t for t in valid_types if t != str)
    scxml_entry = get_children_as_scxml(xml_child[0], valid_types)
    if len(scxml_entry) == 0:
        print(f"Error: reading from {xml_tree.tag}: Child '{child_tag}' has no valid children.")
        return None
    return scxml_entry[0]


def read_value_from_xml_arg_or_child(
    scxml_type: Type[ScxmlBase],
    xml_tree: ET.Element,
    tag_name: str,
    valid_types: Iterable[Type[Union[ScxmlBase, str]]],
    none_allowed: bool = False,
) -> Optional[Union[str, ScxmlBase]]:
    """
    Read a value from an xml attribute or, if not found, the child tag with the same name.

    To read the value from the xml arguments, valid_types must include string.
    """
    assert str in valid_types, (
        "Error: read_value_from_arg_or_child: valid_types must include str. "
        "If strings are not expected, use 'read_value_from_xml_child'."
    )
    read_value = get_xml_argument(scxml_type, xml_tree, tag_name, none_allowed=True)
    if read_value is None:
        read_value = read_value_from_xml_child(
            xml_tree, tag_name, valid_types, none_allowed=none_allowed
        )
    if not none_allowed:
        assert (
            read_value is not None
        ), f"Error: SCXML conversion of {scxml_type.get_tag_name()}: Missing argument {tag_name}."
    return read_value
