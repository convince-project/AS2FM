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

from typing import Type

from scxml_converter.scxml_entries import ScxmlBase
from xml.etree.ElementTree import Element


def assert_xml_tag_ok(scxml_type: Type[ScxmlBase], xml_tree: Element):
    """Ensures the xml_tree we are trying to parse has the expected name."""
    assert xml_tree.tag == scxml_type.get_tag_name(), \
        f"SCXML conversion: Expected tag {scxml_type.get_tag_name()}, but got {xml_tree.tag}"


def get_xml_argument(scxml_type: Type[ScxmlBase], xml_tree: Element, arg_name: str, *,
                     none_allowed=False, empty_allowed=False):
    """Load an argument from the xml tree's root tag."""
    arg_value = xml_tree.get(arg_name)
    error_prefix = f"SCXML conversion of {scxml_type.get_tag_name()}"
    if arg_value is None:
        assert none_allowed, f"{error_prefix}: Expected argument {arg_name} in {xml_tree.tag}"
    elif len(arg_value) == 0:
        assert empty_allowed, \
            f"{error_prefix}: Expected non-empty argument {arg_name} in {xml_tree.tag}"
    return xml_tree.attrib[arg_name]
