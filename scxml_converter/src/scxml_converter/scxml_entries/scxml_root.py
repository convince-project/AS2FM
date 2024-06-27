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
The main entry point of an SCXML Model. In XML, it has the tag `scxml`.
"""

from typing import List, get_args
from scxml_converter.scxml_entries import (ScxmlState, ScxmlDataModel, ScxmlRosDeclarations,
                                           RosTimeRate, RosTopicSubscriber, RosTopicPublisher)

from xml.etree import ElementTree as ET


class ScxmlRoot:
    """This class represents a whole scxml model, that is used to define specific skills."""

    def __init__(self, name: str):
        self._name = name
        self._version = "1.0"  # This is the only version mentioned in the official documentation
        self._initial_state: str = None
        self._states: List[ScxmlState] = []
        self._data_model: ScxmlDataModel = None
        self._ros_declations: List[ScxmlRosDeclarations] = None

    def get_tag_name() -> str:
        return "scxml"

    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlRoot":
        """Create a ScxmlRoot object from an XML tree."""
        # --- Get the ElementTree objects
        assert xml_tree.tag == ScxmlRoot.get_tag_name(), \
            f"Error: SCXML root: XML root tag name is not {ScxmlRoot.get_tag_name()}."
        assert "name" in xml_tree.attrib, \
            "Error: SCXML root: 'name' attribute not found in input xml."
        assert "version" in xml_tree.attrib and xml_tree.attrib["version"] == "1.0", \
            "Error: SCXML root: 'version' attribute not found or invalid in input xml."
        # Data Model
        datamodel_elements = xml_tree.findall(ScxmlDataModel.get_tag_name())
        assert datamodel_elements is None or len(datamodel_elements) == 1, \
            "Error: SCXML root: multiple datamodels found in input xml, up to 1 are allowed."
        # ROS Declaration
        ros_time_rates = xml_tree.findall(RosTimeRate.get_tag_name())
        ros_topic_subs = xml_tree.findall(RosTopicSubscriber.get_tag_name())
        ros_topic_pubs = xml_tree.findall(RosTopicPublisher.get_tag_name())
        # States
        assert "initial" in xml_tree.attrib, \
            "Error: SCXML root: 'initial' attribute not found in input xml."
        initial_state = xml_tree.attrib["initial"]
        state_elements = xml_tree.findall(ScxmlState.get_tag_name())
        assert state_elements is not None and len(state_elements) > 0, \
            "Error: SCXML root: no state found in input xml."
        # Fill Data in the ScxmlRoot object
        scxml_root = ScxmlRoot(xml_tree.attrib["name"])
        # Data Model
        if datamodel_elements is not None:
            scxml_root.set_data_model(ScxmlDataModel.from_xml_tree(datamodel_elements[0]))
        # ROS Declarations
        if ros_time_rates is not None:
            for ros_time_rate in ros_time_rates:
                scxml_root.add_ros_declaration(RosTimeRate.from_xml_tree(ros_time_rate))
        if ros_topic_subs is not None:
            for ros_topic_sub in ros_topic_subs:
                scxml_root.add_ros_declaration(RosTopicSubscriber.from_xml_tree(ros_topic_sub))
        if ros_topic_pubs is not None:
            for ros_topic_pub in ros_topic_pubs:
                scxml_root.add_ros_declaration(RosTopicPublisher.from_xml_tree(ros_topic_pub))
        # States
        for state_element in state_elements:
            scxml_state = ScxmlState.from_xml_tree(state_element)
            is_initial = scxml_state.get_id() == initial_state
            scxml_root.add_state(scxml_state, initial=is_initial)
        return scxml_root

    def from_scxml_file(xml_path) -> "ScxmlRoot":
        """Create a ScxmlRoot object from an SCXML file."""
        xml_file = ET.parse(xml_path)
        # Remove the namespace from all tags in the XML file
        for child in xml_file:
            if "{" in child.tag:
                child.tag = child.tag.split("}")[1]
        # Do the conversion
        return ScxmlRoot.from_xml_tree(xml_file.getroot())

    def add_state(self, state: ScxmlState, *, initial: bool = False):
        """Append a state to the list of states. If initial is True, set it as the initial state."""
        self._states.append(state)
        if initial:
            assert self._initial_state is None, "Error: SCXML root: Initial state already set"
            self._initial_state = state.get_id()

    def set_data_model(self, data_model: ScxmlDataModel):
        assert self._data_model is None, "Data model already set"
        self._data_model = data_model

    def add_ros_declaration(self, ros_declaration: ScxmlRosDeclarations):
        assert isinstance(ros_declaration, get_args(ScxmlRosDeclarations)), \
            "Error: SCXML root: invalid ROS declaration type."
        assert ros_declaration.check_validity(), "Error: SCXML root: invalid ROS declaration."
        if self._ros_declations is None:
            self._ros_declations = []
        self._ros_declations.append(ros_declaration)

    def check_validity(self) -> bool:
        valid_name = isinstance(self._name, str) and len(self._name) > 0
        valid_initial_state = self._initial_state is not None
        valid_states = isinstance(self._states, list) and len(self._states) > 0
        if valid_states:
            for state in self._states:
                valid_states = isinstance(state, ScxmlState) and state.check_validity()
                if not valid_states:
                    break
        valid_data_model = self._data_model is None or self._data_model.check_validity()
        if not valid_name:
            print("Error: SCXML root: name is not valid.")
        if not valid_initial_state:
            print("Error: SCXML root: no initial state set.")
        if not valid_states:
            print("Error: SCXML root: states are not valid.")
        if not valid_data_model:
            print("Error: SCXML root: datamodel is not valid.")
        return valid_name and valid_initial_state and valid_states and valid_data_model

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid root object."
        xml_root = ET.Element("scxml", {
            "name": self._name,
            "version": self._version,
            "model_src": "",
            "initial": self._initial_state,
            "xmlns": "http://www.w3.org/2005/07/scxml"
        })
        if self._data_model is not None:
            xml_root.append(self._data_model.as_xml())
        if self._ros_declations is not None:
            for ros_declaration in self._ros_declations:
                xml_root.append(ros_declaration.as_xml())
        for state in self._states:
            xml_root.append(state.as_xml())
        ET.indent(xml_root, "    ")
        return xml_root
