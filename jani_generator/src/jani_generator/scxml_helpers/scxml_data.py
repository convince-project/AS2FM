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
Module handling ScXML data tags.
"""

import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, get_args

from mc_toolchain_jani_common.common import ros_type_name_to_python_type
from mc_toolchain_jani_common.ecmascript_interpretation import \
    interpret_ecma_script_expr
from jani_generator.jani_entries.jani_expression import JaniExpression
from jani_generator.jani_entries.jani_variable import JaniVariable, ValidTypes


class ScxmlData:
    """Object representing a data tag from a ScXML file.

    See https://www.w3.org/TR/scxml/#data
    """

    def __init__(self, element: ET.Element,
                 comment_above: Optional[str] = None) -> None:
        """Initialize the ScxmlData object from an xml element.

        :param element: The xml element representing the data tag.
        :param comment_above: The comment in the line above the data tag.
        """

        # reading official attributes
        self.id: str = element.attrib['id']
        self.xml_src: Optional[str] = element.attrib.get('src', None)
        self.xml_expr: Optional[str] = element.attrib.get('expr', None)
        if self.xml_src is not None:
            raise NotImplementedError(
                "src attribute in data tag is not supported yet.")

        # unofficial attributes
        self.xml_type: Optional[str] = element.attrib.get('type', None)

        # trying to find the type of the data
        types_from_comment_above: Optional[Dict[str, type]] = \
            self._interpret_type_from_comment_above(comment_above)
        type_from_comment_above: Optional[type] = \
            types_from_comment_above.get(self.id, None) \
            if types_from_comment_above is not None else None
        type_from_xml_type_attr: Optional[type] = \
            ros_type_name_to_python_type(self.xml_type) \
            if self.xml_type is not None else None
        type_from_expr: Optional[type] = \
            self._interpret_ecma_script_expr_to_type(self.xml_expr) \
            if self.xml_expr is not None else None
        self.type: type = self._evalute_possible_types(
            type_from_comment_above,
            type_from_xml_type_attr,
            type_from_expr)
        if self.type not in get_args(ValidTypes):
            raise ValueError(f"Type {self.type} not supported by Jani.")

        # trying to find the initial value of the data
        self.initial_value: ValidTypes = (
            self.type(interpret_ecma_script_expr(self.xml_expr))
            if self.xml_expr is not None
            else self.type())

    def _interpret_type_from_comment_above(
            self, comment_above: Optional[str]) -> Optional[type]:
        """Interpret the type of the data from the comment above the data tag.

        :param comment_above: The comment above the data tag (optional)
        :return: The type of the data
        """
        if comment_above is None:
            return None
        # match string inside xml comment brackets
        match = re.match(r'<!--(.*?)-->', comment_above.strip())
        comment_content = match.group(1).strip()
        if 'TYPE' not in comment_content:
            return None
        type_infos = {}
        for type_info in comment_content.split():
            if ':' not in type_info:
                continue
            key, value = type_info.split(':')
            type_infos[key] = ros_type_name_to_python_type(value)
        if len(type_infos) == 0:
            return None
        return type_infos

    def _interpret_ecma_script_expr_to_type(self, expr: str) -> type:
        """Interpret the type of the data from the ECMA script expression.

        :param expr: The ECMA script expression
        :return: The type of the data
        """
        my_type = type(interpret_ecma_script_expr(expr))
        if my_type not in get_args(ValidTypes):
            raise ValueError(
                f"Type {my_type} must be supported by Jani.")
        return my_type

    def _evalute_possible_types(
            self,
            type_from_comment_above: Optional[type],
            type_from_xml_type_attr: Optional[type],
            type_from_expr: Optional[type]) -> type:
        """Evaluate the possible types of the data.

        This is done by comparing the types from the comment above, the xml type
        attribute and the expression tag.

        :param type_from_comment_above: The type from the comment above the data tag
        :param type_from_xml_type_attr: The type from the xml type attribute
        :param type_from_expr: The type from the expression tag
        :raises ValueError: If no type or multiple conflicting types are found
        :return: The evaluated type
        """
        types = set()
        if type_from_comment_above is not None:
            types.add(type_from_comment_above)
        if type_from_xml_type_attr is not None:
            types.add(type_from_xml_type_attr)
        if type_from_expr is not None:
            types.add(type_from_expr)
        if len(types) == 0:
            raise ValueError(
                f"Could not determine type for data {self.id}")
        if len(types) == 1:
            return types.pop()
        if len(types) > 1:
            raise ValueError(
                f"Multiple types found for data {self.id}: {types}")
        
    def get_type(self) -> type:
        """Get the type of the data.

        :return: The type of the data
        """
        return self.type

    def to_jani_variable(self) -> JaniVariable:
        """Convert the ScxmlData object to a JaniVariable object.

        :return: The JaniVariable object
        """
        return JaniVariable(
            self.id,
            self.type,
            JaniExpression(self.initial_value)
        )
