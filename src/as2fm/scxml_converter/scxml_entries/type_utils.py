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

"""Collection of utilities for handling custom data structs in SCXML."""

from typing import Dict, List, Optional, Tuple, Type, Union

from as2fm.as2fm_common.ecmascript_interpretation import ArrayAccess, split_by_access
from as2fm.as2fm_common.logging import get_error_msg
from as2fm.scxml_converter.xml_data_types.type_utils import (
    ArrayInfo,
    get_array_info,
    get_type_string_of_array,
    is_type_string_array,
    is_type_string_base_type,
)
from as2fm.scxml_converter.xml_data_types.xml_struct_definition import XmlStructDefinition


class ScxmlStructDeclarationsContainer:
    """
    Object containing all the type-related information needed when generating the plain-SCXML model.

    In this class, we hold all the information about:
    * Data variables and related type
    * Events and related types
    * ROS Services and Actions
    * Timer callbacks
    """

    def __init__(
        self,
        automaton_name: str,
        data_model,
        struct_definitions: Dict[str, XmlStructDefinition],
    ):
        self._automaton_name = automaton_name
        self._data_model = data_model
        self._struct_definitions = struct_definitions
        self._type_per_variable: Dict[
            str, Tuple[Union[XmlStructDefinition, str], Optional[ArrayInfo]]
        ] = {}
        for data_entry in self._data_model.get_data_entries():
            variable_name: str = data_entry.get_name()
            assert (
                variable_name not in self._type_per_variable.keys()
            ), f"Variable name {variable_name} must be unique."
            data_type_def = data_entry.get_type_str()
            if is_type_string_array(data_type_def):
                data_type_single = get_type_string_of_array(data_type_def)
                array_info: Optional[ArrayInfo] = get_array_info(data_type_def, False)
            else:
                data_type_single = data_type_def
                array_info = None
            if is_type_string_base_type(data_type_single):
                self._type_per_variable[variable_name] = (data_type_def, array_info)
            else:
                data_type_struct = struct_definitions[data_type_single]
                self._type_per_variable[variable_name] = (
                    data_type_struct,
                    array_info,
                )

    def get_data_type(
        self, variable_name: str, elem
    ) -> Tuple[Union[XmlStructDefinition, str], Optional[ArrayInfo]]:
        """
        Retrieve the type of a variable.

        Used, when trying to assign to it.

        e.g. `x` => ('int32', None)` <-- retrieve from dict
        e.g. `xs` => ('int32', ArrayInfo)` <-- retrieve from dict
        e.g. `xs[1]` => ('int32', None)` <- handle *specially*

        e.g. `a_point` => (XmlStructDefinition(Point2D), None)` <-- retrieve from dict
        e.g. `polygon.points` => `(XmlStructDefinition(Point2D), ArrayInfo)` <- ???
        e.g. `polygon.points[1]` => `(XmlStructDefinition(Point2D), None)` <- ???
        e.g. `polygon.points[1].x` => `(int32, None)` <- ???

        """
        access_trace = split_by_access(variable_name, elem)
        return self._get_data_type_for_variable(access_trace, elem)

    def _get_data_type_for_variable(
        self, access_trace: List[Union[str, Type[ArrayAccess]]], elem
    ) -> Tuple[Union[XmlStructDefinition, str], Optional[ArrayInfo]]:
        """leftmost string is variable"""
        if len(access_trace) == 1:
            variable_name = access_trace[0]
            assert variable_name != ArrayAccess, get_error_msg(
                elem, "Can not be only an array access."
            )
            return self._type_per_variable[variable_name]
        if access_trace[-1] == ArrayAccess:
            # We are accessing an array at the end.
            # -> Discard array info and treat as single item.
            return self._get_data_type_for_variable(access_trace[:-1], elem)
        if len(access_trace) >= 2:
            # Accessing a property of a struct.
            # -> Get struct type and evaluate the property.
            struct_type, _ = self._type_per_variable[access_trace[0]]
            if access_trace[1] == ArrayAccess:
                # This is an array, but we access an instance
                return self._get_data_type_for_property(struct_type, access_trace[2:], elem)
            else:
                return self._get_data_type_for_property(struct_type, access_trace[1:], elem)

        raise RuntimeError()

    def _get_data_type_for_property(
        self,
        struct_type: Union[XmlStructDefinition, str],
        access_trace: List[Union[str, Type[ArrayAccess]]],
        elem,
    ) -> Tuple[Union[XmlStructDefinition, str], Optional[ArrayInfo]]:
        """leftmost string is property"""
        if len(access_trace) == 1:
            property_name = access_trace[0]
            assert property_name != ArrayAccess, get_error_msg(
                elem, "Can not be only an array access."
            )
            return struct_type, None
        if access_trace[-1] == ArrayAccess:
            # We are accessing an array at the end.
            # Then we can take the array type and treat it as a single object of that type.
            return self._get_data_type_for_property(struct_type, access_trace[:-1], elem)
        if len(access_trace) >= 2:
            # Accessing a property of a struct.
            # -> Get their type and evaluate further.
            prop_struct_type_str = struct_type.get_members()[access_trace[0]]
            single_struct_type_name = get_type_string_of_array(prop_struct_type_str)
            prop_struct_type = self._struct_definitions[single_struct_type_name]
            if access_trace[1] == ArrayAccess:
                # This is an array, but we access an instance
                return self._get_data_type_for_property(prop_struct_type, access_trace[2:], elem)
            else:
                return self._get_data_type_for_property(prop_struct_type, access_trace[1:], elem)

        raise RuntimeError()
