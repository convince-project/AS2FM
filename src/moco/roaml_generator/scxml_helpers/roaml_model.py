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

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Type
from warnings import warn

import lxml.etree as ET
from lxml.etree import _Element as XmlElement

from moco.moco_common.common import remove_namespace, string_as_bool
from moco.moco_common.logging import (
    check_assertion,
    get_error_msg,
    set_filepath_for_all_sub_elements,
)
from moco.roaml_converter.data_types.json_struct_definition import JsonStructDefinition
from moco.roaml_converter.data_types.struct_definition import StructDefinition
from moco.roaml_converter.data_types.xml_struct_definition import XmlStructDefinition


@dataclass()
class FullModel:
    # The maximum time the model is allowed to run, in nanoseconds
    max_time: Optional[int] = None
    # Max size of "dynamic" arrays defined in the SCXML models
    max_array_size: int = field(default=100)
    # Tick rate for the loaded BT in Hz
    bt_tick_rate: float = field(default=1.0)
    # Whether to keep ticking the BT after it returns SUCCESS / FAILURE
    bt_tick_when_not_running: bool = field(default=False)
    # List of data declarations. Each entry will contain the type and path to the file
    data_declarations: List[Tuple[str, str]] = field(default_factory=list)
    # Path to the behavior tree loaded in the model
    bt: Optional[str] = None
    # Paths to the SCXML models of the BT nodes used in the model
    plugins: List[str] = field(default_factory=list)
    # Paths to the SCXML models of the non-BT nodes in the model
    skills: List[str] = field(default_factory=list)
    # Similar to the skills, currently unused
    components: List[str] = field(default_factory=list)
    # Path to the properties definition, currently in JANI
    properties: List[str] = field(default_factory=list)


class RoamlParameters:
    """Handler for the parameters section of a ROAML file."""

    @staticmethod
    def get_tag():
        return "parameters"

    @staticmethod
    def from_roaml_xml(parent_element: XmlElement) -> "RoamlParameters":
        """Generate a RoamlParameters instance from the roaml (parent) xml def."""
        params_xml = parent_element.findall(RoamlParameters.get_tag())
        if len(params_xml) == 0:
            params_xml = parent_element.findall("mc_parameters")
            if len(params_xml) > 0:
                warn(
                    get_error_msg(
                        params_xml[0],
                        "The tag 'mc_parameters' is deprecated: switch to "
                        + f"the tag '{RoamlParameters.get_tag()}'.",
                    )
                )
        check_assertion(
            len(params_xml) == 1,
            parent_element,
            f"Found {len(params_xml)} tags {RoamlParameters.get_tag()}, expected 1.",
        )
        return RoamlParameters(params_xml[0])

    def __init__(self, params_element: Optional[XmlElement]):
        self._max_time: Optional[int] = None
        self._max_array_size: int = 100
        self._bt_tick_rate: float = 1.0
        self._bt_tick_when_not_running: bool = False

        assert params_element is not None, "No params elements provided."
        self._parse_parameters(params_element)

    def _parse_parameters(self, params_element: XmlElement) -> None:
        """Parse the parameters section from XML."""
        for param in params_element:
            param_tag = remove_namespace(param.tag)
            if param_tag == "max_time":
                self._max_time = self._parse_time_element(param)
            elif param_tag == "max_array_size":
                self._max_array_size = int(param.attrib["value"])
            elif param_tag == "bt_tick_rate":
                self._bt_tick_rate = float(param.attrib["value"])
            elif param_tag == "bt_tick_if_not_running":
                self._bt_tick_when_not_running = string_as_bool(param.attrib["value"])
            else:
                raise ValueError(get_error_msg(param, f"Invalid parameter tag: {param_tag}"))

        if self._max_time is None:
            raise ValueError(get_error_msg(params_element, "`max_time` must be defined."))

    @staticmethod
    def _parse_time_element(time_element: XmlElement) -> int:
        """
        Interpret a time element. Output is in nanoseconds.

        :param time_element: The time element to interpret.
        :return: The interpreted time in nanoseconds.
        """
        TIME_MULTIPLIERS = {"s": 1_000_000_000, "ms": 1_000_000, "us": 1_000, "ns": 1}
        time_unit = time_element.attrib["unit"]
        assert time_unit in TIME_MULTIPLIERS, f"Invalid time unit: {time_unit}"
        return int(time_element.attrib["value"]) * TIME_MULTIPLIERS[time_unit]

    def get_max_time(self) -> Optional[int]:
        return self._max_time

    def get_max_array_size(self) -> int:
        return self._max_array_size

    def get_bt_tick_rate(self) -> float:
        return self._bt_tick_rate

    def get_tick_when_not_running(self) -> bool:
        return self._bt_tick_when_not_running


class RoamlDataStructures:
    """Handler for the data_declarations section of a ROAML file."""

    AVAILABLE_STRUCT_DEFINITIONS: Dict[str, Type[StructDefinition]] = {
        "xml": XmlStructDefinition,
        "json": JsonStructDefinition,
    }

    @staticmethod
    def get_tag():
        return "data_declarations"

    @staticmethod
    def from_roaml_xml(parent_element: XmlElement, folder: str) -> "RoamlDataStructures":
        """
        Load the Data Structures declaration from the RoAML XML node.

        :parent_element: The RoAML element to extract the information from.
        :parent folder: Path to the folder containing the RoAML xml file.
        :return: An instance of RoamlDataStructures.
        """
        data_tag = RoamlDataStructures.get_tag()
        data_decls = parent_element.findall(data_tag)
        if len(data_decls) == 0:
            return RoamlDataStructures(None, folder)
        elif len(data_decls) == 1:
            return RoamlDataStructures(data_decls[0], folder)
        else:
            raise AssertionError(
                get_error_msg(
                    data_decls[1], f"Expected one {data_tag} entry, found {len(data_decls)}"
                )
            )

    def __init__(self, data_element: Optional[XmlElement], folder_path: str):
        self._data_declarations: List[Tuple[str, str]] = []

        if data_element is not None:
            self._parse_data_declarations(data_element, folder_path)

    def _parse_data_declarations(self, data_element: XmlElement, folder_path: str) -> None:
        """Parse the data_declarations section from XML."""
        for child in data_element:
            if remove_namespace(child.tag) == "input":
                if child.attrib["type"] not in self.AVAILABLE_STRUCT_DEFINITIONS.keys():
                    raise ValueError(
                        get_error_msg(child, f"Unsupported type {child.attrib['type']}.")
                    )
                self._data_declarations.append(
                    (child.attrib["type"], os.path.join(folder_path, child.attrib["src"]))
                )
            else:
                raise ValueError(
                    get_error_msg(child, f"Invalid data_declarations tag: {child.tag} != input")
                )

    def get_data_declarations(self) -> List[Tuple[str, str]]:
        return self._data_declarations


class RoamlBehaviorTree:
    """Handler for the behavior_tree section of a ROAML file."""

    @staticmethod
    def get_tag():
        return "behavior_tree"

    @staticmethod
    def from_roaml_xml(parent_element: XmlElement, folder: str) -> "RoamlBehaviorTree":
        """
        Load the BT declaration and related plugins from the RoAML XML node.

        :parent_element: The RoAML element to extract the information from.
        :parent folder: Path to the folder containing the RoAML xml file.
        :return: An instance of RoamlBehaviorTree.
        """
        bt_tag = RoamlBehaviorTree.get_tag()
        bt_decls = parent_element.findall(bt_tag)
        if len(bt_decls) == 0:
            return RoamlBehaviorTree(None, folder)
        elif len(bt_decls) == 1:
            return RoamlBehaviorTree(bt_decls[0], folder)
        else:
            raise AssertionError(
                get_error_msg(bt_decls[1], f"Expected one {bt_tag} entry, found {len(bt_decls)}")
            )

    def __init__(self, bt_element: Optional[XmlElement], folder_path: str):
        self._bt_path: Optional[str] = None
        self._plugins: List[str] = []

        if bt_element is not None:
            self._parse_behavior_tree(bt_element, folder_path)

    def _parse_behavior_tree(self, bt_element: XmlElement, folder_path: str) -> None:
        """Parse the behavior_tree section from XML."""
        for child in bt_element:
            if remove_namespace(child.tag) == "input":
                if child.attrib["type"] == "bt.cpp-xml":
                    if self._bt_path is not None:
                        raise ValueError("Only one Behavior Tree is supported.")
                    self._bt_path = os.path.join(folder_path, child.attrib["src"])
                elif child.attrib["type"] == "bt-plugin-ascxml":
                    self._plugins.append(os.path.join(folder_path, child.attrib["src"]))
                elif child.attrib["type"] == "bt-plugin-ros-scxml":
                    self._plugins.append(os.path.join(folder_path, child.attrib["src"]))
                    warn(
                        get_error_msg(
                            bt_element,
                            "Deprecated type 'bt-plugin-ros-scxml', switch to 'bt-plugin-ascxml'.",
                        )
                    )
                else:
                    raise ValueError(
                        get_error_msg(child, f"Invalid input type: {child.attrib['type']}")
                    )
            else:
                raise ValueError(
                    get_error_msg(child, f"Invalid behavior_tree tag: {child.tag} != input")
                )

        if self._bt_path is None:
            raise ValueError(get_error_msg(bt_element, "A Behavior Tree must be defined."))

    def get_bt_path(self) -> Optional[str]:
        return self._bt_path

    def get_plugins(self) -> List[str]:
        return self._plugins


class RoamlNodes:
    """Handler for the node_models section of a ROAML file."""

    @staticmethod
    def get_tag():
        return "node_models"

    @staticmethod
    def from_roaml_xml(parent_element: XmlElement, folder: str) -> "RoamlNodes":
        """
        Load the executable nodes declaration from the RoAML XML node.

        :parent_element: The RoAML element to extract the information from.
        :parent folder: Path to the folder containing the RoAML xml file.
        :return: An instance of RoamlNodes.
        """
        nodes_tag = RoamlNodes.get_tag()
        nodes_entries = parent_element.findall(nodes_tag)
        if len(nodes_entries) == 0:
            return RoamlNodes(None, folder)
        elif len(nodes_entries) == 1:
            return RoamlNodes(nodes_entries[0], folder)
        else:
            raise AssertionError(
                get_error_msg(
                    nodes_entries[1], f"Expected one {nodes_tag} entry, found {len(nodes_entries)}"
                )
            )

    def __init__(self, nodes_element: Optional[XmlElement], folder_path: str):
        self._skills: List[str] = []

        if nodes_element is not None:
            self._parse_node_models(nodes_element, folder_path)

    def _parse_node_models(self, nodes_element: XmlElement, folder_path: str) -> None:
        """Parse the node_models section from XML."""
        for node_model in nodes_element:
            if remove_namespace(node_model.tag) != "input":
                raise ValueError(get_error_msg(node_model, "Only input tags are supported."))

            node_type = node_model.attrib["type"]
            if node_type == "node-ascxml":
                self._skills.append(os.path.join(folder_path, node_model.attrib["src"]))
            elif node_type == "ros-scxml":
                self._skills.append(os.path.join(folder_path, node_model.attrib["src"]))
                warn(
                    get_error_msg(
                        nodes_element, "Deprecated type 'ros-scxml', switch to 'node-ascxml'."
                    )
                )
            else:
                raise ValueError(
                    get_error_msg(node_model, f"Unsupported node model type: {node_type}")
                )

    def get_skills(self) -> List[str]:
        return self._skills


class RoamlProperties:
    """Handler for the properties section of a RoAML file."""

    @staticmethod
    def get_tag():
        return "properties"

    @staticmethod
    def from_roaml_xml(parent_element: XmlElement, folder: str) -> "RoamlProperties":
        """
        Load the declaration of the properties to be verified from the RoAML XML node.

        :parent_element: The RoAML element to extract the information from.
        :parent folder: Path to the folder containing the RoAML xml file.
        :return: An instance of RoamlProperties.
        """
        prop_tag = RoamlProperties.get_tag()
        prop_entries = parent_element.findall(prop_tag)
        if len(prop_entries) == 1:
            return RoamlProperties(prop_entries[0], folder)
        else:
            raise AssertionError(
                get_error_msg(
                    prop_entries[1], f"Expected one {prop_tag} entry, found {len(prop_entries)}"
                )
            )

    def __init__(self, props_element: Optional[XmlElement] = None, folder_path: str = ""):
        self._properties: List[str] = []

        if props_element is not None:
            self._parse_properties(props_element, folder_path)

    def _parse_properties(self, props_element: XmlElement, folder_path: str) -> None:
        """Parse the properties section from XML."""
        for jani_property in props_element:
            if remove_namespace(jani_property.tag) != "input":
                raise ValueError(get_error_msg(jani_property, "Only input tags are supported."))

            if jani_property.attrib["type"] != "jani":
                raise ValueError(
                    get_error_msg(
                        jani_property,
                        f"Only Jani properties are supported, not {jani_property.attrib['type']}.",
                    )
                )

            self._properties.append(os.path.join(folder_path, jani_property.attrib["src"]))

        if len(self._properties) != 1:
            raise ValueError(
                get_error_msg(props_element, "Only exactly one Jani property is supported.")
            )

    def get_properties(self) -> List[str]:
        return self._properties


class RoamlMain:
    """This is the entry point of any RoAML model."""

    @staticmethod
    def get_tag():
        return "roaml"

    def __init__(self, xml_path: str):
        # Load the XML
        self._folder_path = os.path.dirname(xml_path)
        parser_wo_comments = ET.XMLParser(remove_comments=True)
        with open(xml_path, "r", encoding="utf-8") as f:
            xml = ET.parse(f, parser=parser_wo_comments)
            self._xml_root_orig = xml.getroot()
            set_filepath_for_all_sub_elements(self._xml_root_orig, xml_path)
        roaml_tag: str = remove_namespace(self._xml_root_orig.tag)
        # Check the tags
        if roaml_tag == "convince_mc_tc":
            warn(
                get_error_msg(
                    self._xml_root_orig,
                    f"The tag {roaml_tag} is deprecated: switch to the tag '{self.get_tag()}'.",
                )
            )
        else:
            check_assertion(
                roaml_tag == self.get_tag(),
                xml.getroot(),
                f"Unknown top level tag {roaml_tag}: expected '{self.get_tag()}'.",
            )
        # Initialize the children entries
        # -- Params
        self._roaml_params = RoamlParameters.from_roaml_xml(self._xml_root_orig)
        self._roaml_data = RoamlDataStructures.from_roaml_xml(
            self._xml_root_orig, self._folder_path
        )
        self._roaml_bt = RoamlBehaviorTree.from_roaml_xml(self._xml_root_orig, self._folder_path)
        self._roaml_nodes = RoamlNodes.from_roaml_xml(self._xml_root_orig, self._folder_path)
        self._roaml_properties = RoamlProperties.from_roaml_xml(
            self._xml_root_orig, self._folder_path
        )

    def get_loaded_model(self) -> FullModel:
        """Get the parsed model as a FullModel object."""
        loaded_model = FullModel()
        loaded_model.max_time = self._roaml_params.get_max_time()
        loaded_model.max_array_size = self._roaml_params.get_max_array_size()
        loaded_model.bt_tick_rate = self._roaml_params.get_bt_tick_rate()
        loaded_model.bt_tick_when_not_running = self._roaml_params.get_tick_when_not_running()
        loaded_model.data_declarations = self._roaml_data.get_data_declarations()
        loaded_model.bt = self._roaml_bt.get_bt_path()
        loaded_model.plugins = self._roaml_bt.get_plugins()
        loaded_model.skills = self._roaml_nodes.get_skills()
        loaded_model.properties = self._roaml_properties.get_properties()
        return loaded_model
