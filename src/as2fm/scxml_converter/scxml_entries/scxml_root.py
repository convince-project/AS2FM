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

from copy import deepcopy
from os.path import isfile
from typing import List, Optional, Set, Tuple, get_args

from lxml import etree as ET

from as2fm.as2fm_common.common import is_comment, remove_namespace
from as2fm.scxml_converter.scxml_entries import (
    BtInputPortDeclaration,
    BtOutputPortDeclaration,
    BtPortDeclarations,
    EventsToAutomata,
    RosActionThread,
    ScxmlBase,
    ScxmlDataModel,
    ScxmlRosDeclarationsContainer,
    ScxmlState,
    add_targets_to_scxml_send,
)
from as2fm.scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from as2fm.scxml_converter.scxml_entries.scxml_ros_base import RosDeclaration
from as2fm.scxml_converter.scxml_entries.utils import is_non_empty_string
from as2fm.scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok,
    get_children_as_scxml,
    get_xml_argument,
)


class ScxmlRoot(ScxmlBase):
    """This class represents a whole scxml model, that is used to define specific skills."""

    @staticmethod
    def get_tag_name() -> str:
        return "scxml"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlRoot":
        """Create a ScxmlRoot object from an XML tree."""
        # --- Get the ElementTree objects
        assert_xml_tag_ok(ScxmlRoot, xml_tree)
        scxml_name = get_xml_argument(ScxmlRoot, xml_tree, "name")
        scxml_version = get_xml_argument(ScxmlRoot, xml_tree, "version")
        assert (
            scxml_version == "1.0"
        ), f"Error: SCXML root: expected version 1.0, found {scxml_version}."
        scxml_init_state = get_xml_argument(ScxmlRoot, xml_tree, "initial")
        # Data Model
        datamodel_elements = get_children_as_scxml(xml_tree, (ScxmlDataModel,))
        assert (
            len(datamodel_elements) <= 1
        ), f"Error: SCXML root: {len(datamodel_elements)} datamodels found, max 1 allowed."
        # ROS Declarations
        ros_declarations: List[RosDeclaration] = get_children_as_scxml(
            xml_tree, RosDeclaration.__subclasses__()
        )
        # BT Declarations
        bt_port_declarations: List[BtPortDeclarations] = get_children_as_scxml(
            xml_tree, get_args(BtPortDeclarations)
        )
        # Additional threads
        additional_threads = get_children_as_scxml(xml_tree, (RosActionThread,))
        # States
        scxml_states: List[ScxmlState] = get_children_as_scxml(xml_tree, (ScxmlState,))
        assert len(scxml_states) > 0, "Error: SCXML root: no state found in input xml."
        # --- Fill Data in the ScxmlRoot object
        scxml_root = ScxmlRoot(scxml_name)
        # Data Model
        if len(datamodel_elements) > 0:
            scxml_root.set_data_model(datamodel_elements[0])
        # ROS Declarations
        scxml_root._ros_declarations = ros_declarations
        # BT Declarations
        for bt_port_declaration in bt_port_declarations:
            scxml_root.add_bt_port_declaration(bt_port_declaration)
        # Additional threads
        for scxml_thread in additional_threads:
            scxml_root.add_action_thread(scxml_thread)
        # States
        for scxml_state in scxml_states:
            is_initial = scxml_state.get_id() == scxml_init_state
            scxml_root.add_state(scxml_state, initial=is_initial)
        return scxml_root

    @staticmethod
    def from_scxml_file(xml_file: str) -> "ScxmlRoot":
        """Create a ScxmlRoot object from an SCXML file."""
        print(f"{xml_file=}")
        if isfile(xml_file):
            xml_element = ET.parse(xml_file).getroot()
        elif xml_file.startswith("<?xml"):
            raise NotImplementedError("Can only parse files, not strings.")
        else:
            raise ValueError(f"Error: SCXML root: xml_file '{xml_file}' isn't a file / xml string.")
        # Remove the namespace from all tags in the XML file
        for child in xml_element.iter():
            if is_comment(child):
                continue
            child.tag = remove_namespace(child.tag)
        # Do the conversion
        return ScxmlRoot.from_xml_tree(xml_element)

    def __init__(self, name: str):
        self._name = name
        self._version = "1.0"  # This is the only version mentioned in the official documentation
        self._initial_state: Optional[str] = None
        self._states: List[ScxmlState] = []
        self._data_model: Optional[ScxmlDataModel] = None
        self._ros_declarations: List[RosDeclaration] = []
        self._bt_ports_handler = BtPortsHandler()
        self._bt_plugin_id: Optional[int] = None
        self._bt_children_ids: List[int] = []
        self._additional_threads: List[RosActionThread] = []

    def get_name(self) -> str:
        """Get the name of the automaton represented by this SCXML model."""
        return self._name

    def set_name(self, name: str) -> None:
        """Rename the automaton represented by this SCXML model."""
        assert is_non_empty_string(ScxmlRoot, "name", name)
        self._name = name

    def get_initial_state_id(self) -> str:
        """Get the ID of the initial state of the SCXML model."""
        assert self._initial_state is not None, "Error: SCXML root: Initial state not set."
        return self._initial_state

    def get_data_model(self) -> Optional[ScxmlDataModel]:
        return self._data_model

    def get_states(self) -> List[ScxmlState]:
        return self._states

    def get_transition_events(self) -> Set[str]:
        """Generate the set of events that are expected by the SCXML automaton."""
        assert self.is_plain_scxml(), (
            f"Error: SCXML root: {self.get_name()} must be plain SCXML "
            "for generating the list of transition events."
        )
        transition_events = set()
        for state in self._states:
            for transition in state.get_body():
                transition_events.update({ev for ev in transition.get_events()})
        return transition_events

    def add_targets_to_scxml_sends(self, events_to_targets: EventsToAutomata) -> None:
        for state in self._states:
            state.set_on_entry(add_targets_to_scxml_send(state.get_onentry(), events_to_targets))
            state.set_on_exit(add_targets_to_scxml_send(state.get_onexit(), events_to_targets))
            for transition in state.get_body():
                transition.set_body(
                    add_targets_to_scxml_send(transition.get_body(), events_to_targets)
                )

    def get_state_by_id(self, state_id: str) -> Optional[ScxmlState]:
        for state in self._states:
            if state.get_id() == state_id:
                return state
        return None

    def set_bt_plugin_id(self, instance_id: int) -> None:
        """Update all BT-related events to use the assigned instance ID."""
        self._bt_plugin_id = instance_id

    def get_bt_plugin_id(self) -> Optional[int]:
        """Get the ID of the BT plugin instance, if any."""
        return self._bt_plugin_id

    def add_state(self, state: ScxmlState, *, initial: bool = False):
        """Append a state to the list of states in the SCXML model.
        If initial is True, set it as the initial state."""
        self._states.append(state)
        if initial:
            assert self._initial_state is None, "Error: SCXML root: Initial state already set"
            self._initial_state = state.get_id()

    def set_data_model(self, data_model: ScxmlDataModel):
        assert self._data_model is None, "Data model already set"
        self._data_model = data_model

    def add_ros_declaration(self, ros_declaration: RosDeclaration):
        assert isinstance(
            ros_declaration, RosDeclaration
        ), "Error: SCXML root: invalid ROS declaration type."
        assert ros_declaration.check_validity(), "Error: SCXML root: invalid ROS declaration."
        self._ros_declarations.append(ros_declaration)

    def add_bt_port_declaration(self, bt_port_decl: BtPortDeclarations):
        """Add a BT port declaration to the handler."""
        if isinstance(bt_port_decl, BtInputPortDeclaration):
            self._bt_ports_handler.declare_in_port(
                bt_port_decl.get_key_name(), bt_port_decl.get_key_type()
            )
        elif isinstance(bt_port_decl, BtOutputPortDeclaration):
            self._bt_ports_handler.declare_out_port(
                bt_port_decl.get_key_name(), bt_port_decl.get_key_type()
            )
        else:
            raise ValueError(
                f"Error: SCXML root: invalid BT port declaration type {type(bt_port_decl)}."
            )

    def add_action_thread(self, action_thread: RosActionThread):
        assert isinstance(
            action_thread, RosActionThread
        ), f"Error: SCXML root: invalid action thread type {type(action_thread)}."
        self._additional_threads.append(action_thread)

    def set_bt_port_value(self, port_name: str, port_value: str):
        """Set the value of an input port."""
        self._bt_ports_handler.set_port_value(port_name, port_value)

    def set_bt_ports_values(self, ports_values: List[Tuple[str, str]]):
        """Set the values of multiple input ports."""
        for port_name, port_value in ports_values:
            self.set_bt_port_value(port_name, port_value)

    def get_bt_ports_types_values(self) -> List[Tuple[str, str, str]]:
        """
        Get information about the BT ports in the model.

        :return: A list of Tuples containing bt_port_name, type and value.
        """
        return [
            (p_name, p_type, p_value)
            for p_name, (p_type, p_value) in self._bt_ports_handler.get_all_ports().items()
        ]

    def append_bt_child_id(self, child_id: int):
        """Append a child ID to the list of child IDs."""
        assert isinstance(child_id, int), "Error: SCXML root: invalid child ID type."
        self._bt_children_ids.append(child_id)

    def instantiate_bt_information(self):
        """Instantiate the values of BT ports and children IDs in the SCXML entries."""
        n_bt_children = len(self._bt_children_ids)
        assert self._bt_plugin_id is not None, "Error: SCXML root: BT plugin ID not set."
        # Automatically add the correct amount of children to the specific port
        if self._bt_ports_handler.in_port_exists("CHILDREN_COUNT"):
            self._bt_ports_handler.set_port_value("CHILDREN_COUNT", str(n_bt_children))
        if self._data_model is not None:
            self._data_model.update_bt_ports_values(self._bt_ports_handler)
        for ros_decl_scxml in self._ros_declarations:
            ros_decl_scxml.update_bt_ports_values(self._bt_ports_handler)
        for scxml_thread in self._additional_threads:
            scxml_thread.update_bt_ports_values(self._bt_ports_handler)
        processed_states: List[ScxmlState] = []
        for state in self._states:
            processed_states.extend(
                state.instantiate_bt_events(
                    self._bt_plugin_id, self._bt_children_ids, self._bt_ports_handler
                )
            )
        self._states = processed_states

    def _generate_ros_declarations_helper(self) -> Optional[ScxmlRosDeclarationsContainer]:
        """Generate a HelperRosDeclarations object from the existing ROS declarations."""
        ros_decl_container = ScxmlRosDeclarationsContainer(self._name)
        for ros_declaration in self._ros_declarations:
            if not (
                ros_declaration.check_validity() and ros_declaration.check_valid_instantiation()
            ):
                return None
            ros_decl_container.append_ros_declaration(ros_declaration)
        return ros_decl_container

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(ScxmlRoot, "name", self._name)
        valid_initial_state = is_non_empty_string(ScxmlRoot, "initial state", self._initial_state)
        valid_data_model = self._data_model is None or self._data_model.check_validity()
        valid_states = all(
            isinstance(state, ScxmlState) and state.check_validity() for state in self._states
        )
        valid_threads = all(
            isinstance(scxml_thread, RosActionThread) and scxml_thread.check_validity()
            for scxml_thread in self._additional_threads
        )
        if not valid_data_model:
            print(f"Error: SCXML root({self._name}): datamodel is not valid.")
        if not valid_states:
            print(f"Error: SCXML root({self._name}): states are not valid.")
        if not valid_threads:
            print(f"Error: SCXML root({self._name}): additional threads are not valid.")
        valid_ros = self._check_valid_ros_declarations()
        if not valid_ros:
            print(f"Error: SCXML root({self._name}): ROS declarations are not valid.")
        return (
            valid_name and valid_initial_state and valid_states and valid_data_model and valid_ros
        )

    def _check_valid_ros_declarations(self) -> bool:
        """Check if the ros declarations and instantiations are valid."""
        # Prepare the ROS declarations, to check no undefined ros instances exist
        ros_decl_container = self._generate_ros_declarations_helper()
        if ros_decl_container is None:
            return False
        # Check the ROS instantiations
        if not all(
            state.check_valid_ros_instantiations(ros_decl_container) for state in self._states
        ):
            return False
        if not all(
            scxml_thread.check_valid_ros_instantiations(ros_decl_container)
            for scxml_thread in self._additional_threads
        ):
            return False
        return True

    def is_plain_scxml(self) -> bool:
        """Check whether there are ROS or BT specific tags in the SCXML model."""
        assert self.check_validity(), "SCXML: found invalid root object."
        no_ros_declarations = (len(self._ros_declarations) + len(self._additional_threads)) == 0
        all_states_plain = all(state.is_plain_scxml() for state in self._states)
        return no_ros_declarations and all_states_plain

    def to_plain_scxml_and_declarations(
        self,
    ) -> Tuple[List["ScxmlRoot"], ScxmlRosDeclarationsContainer]:
        """
        Convert all internal ROS specific entries to plain SCXML.

        :return: A tuple with:
            - a list of ScxmlRoot objects with all ROS specific entries converted to plain SCXML
            - The Ros declarations contained in the original SCXML object
        """
        if self.is_plain_scxml():
            return [self], ScxmlRosDeclarationsContainer(self._name)
        converted_scxmls: List[ScxmlRoot] = []
        # Convert the ROS specific entries to plain SCXML
        main_scxml = ScxmlRoot(self._name)
        main_scxml._data_model = deepcopy(self._data_model)
        main_scxml._initial_state = self._initial_state
        ros_declarations = self._generate_ros_declarations_helper()
        assert ros_declarations is not None, "Error: SCXML root: invalid ROS declarations."
        main_scxml._states = [state.as_plain_scxml(ros_declarations) for state in self._states]
        converted_scxmls.append(main_scxml)
        for scxml_thread in self._additional_threads:
            converted_scxmls.extend(scxml_thread.as_plain_scxml(ros_declarations))
        for plain_scxml in converted_scxmls:
            assert isinstance(plain_scxml, ScxmlRoot), (
                "Error: SCXML root: conversion to plain SCXML resulted in invalid object "
                f"(expected ScxmlRoot, obtained {type(plain_scxml)}."
            )
            assert plain_scxml.check_validity(), (
                f"The SCXML root object {plain_scxml.get_name()} is not valid: "
                "conversion to plain SCXML failed."
            )
            assert plain_scxml.is_plain_scxml(), (
                f"The SCXML root object {plain_scxml.get_name()} is not plain SCXML: "
                "conversion to plain SCXML failed."
            )
        return (converted_scxmls, ros_declarations)

    def as_xml(self, **kwargs) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid root object."
        assert self._initial_state is not None, "Error: SCXML root: no initial state set."
        data_type_as_attribute = kwargs.get("data_type_as_attribute", True)
        xml_root = ET.Element(
            "scxml",
            {
                "name": self._name,
                "version": self._version,
                "model_src": "",
                "initial": self._initial_state,
                "xmlns": "http://www.w3.org/2005/07/scxml",
            },
        )
        if self._data_model is not None:
            data_model_xml = self._data_model.as_xml(data_type_as_attribute)
            assert data_model_xml is not None, "Error: SCXML root: invalid data model."
            xml_root.append(data_model_xml)
        for ros_declaration in self._ros_declarations:
            xml_root.append(ros_declaration.as_xml())
        for scxml_thread in self._additional_threads:
            xml_root.append(scxml_thread.as_xml())
        for state in self._states:
            xml_root.append(state.as_xml())
        ET.indent(xml_root, "    ")
        return xml_root

    def as_xml_string(self, **kwargs) -> str:
        return ET.tostring(self.as_xml(**kwargs), encoding="unicode")
