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
The main entry point of the supported SCXML Models and a loader function.
In XML, it has either the tag `scxml` or `ascxml`.
"""

from abc import abstractmethod
from os.path import isfile, splitext
from typing import Dict, List, Optional, Set, Type

from lxml import etree as ET
from lxml.etree import _Element as XmlElement
from typing_extensions import Self

from as2fm.as2fm_common.common import is_comment, remove_namespace
from as2fm.as2fm_common.logging import (
    check_assertion,
    get_error_msg,
    log_error,
    log_warning,
    set_filepath_for_all_sub_elements,
)
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import (
    AscxmlDeclaration,
    AscxmlThread,
    EventsToAutomata,
    ScxmlBase,
    ScxmlDataModel,
    ScxmlState,
)
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import is_non_empty_string
from as2fm.scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok,
    get_children_as_scxml,
    get_xml_attribute,
)


class GenericScxmlRoot(ScxmlBase):
    """Generic container for the (A)Scxml models."""

    @classmethod
    @abstractmethod
    def get_tag_name(cls) -> str:
        """Get the expected tag name related to this class."""
        pass

    @classmethod
    def get_file_extension(cls) -> str:
        """Get the expected file extension depending on the specific root tag (scxml vs ascxml)."""
        return f".{cls.get_tag_name()}"

    @classmethod
    @abstractmethod
    def get_declaration_classes(cls) -> List[Type[AscxmlDeclaration]]:
        """
        List the supported AscxmlDeclaration classes related to the specific ASCXML class loader.

        E.g. ASCXML for ROS nodes can support topic, service, actions and timers.
        ASCXML for BT plugins, can support the ROS declarations plus BT ports.
        Plain SCXML, has no additional declaration class to support.
        """
        pass

    @classmethod
    @abstractmethod
    def get_thread_classes(cls) -> List[Type[AscxmlThread]]:
        """
        List the supported AscxmlThread classes related to the specific ASCXML class loader.

        E.g. ASCXML for ROS nodes can action threads, as well as BT plugins.
        Plain SCXML, has no additional thread class to support.
        """
        pass

    @classmethod
    def load_scxml_file(cls, xml_file: str, custom_data_types: Dict[str, StructDefinition]) -> Self:
        """Create a `GenericScxmlRoot` instance from an ASCXML file."""
        print(f"{xml_file=}")
        if isfile(xml_file):
            xml_element = ET.parse(xml_file).getroot()
            set_filepath_for_all_sub_elements(xml_element, xml_file)
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
        _, fext = splitext(xml_file)
        assert fext == cls.get_file_extension(), (
            f"Error loading file {xml_file}: ",
            f"the class {cls} expects the extension '{cls.get_file_extension()}'.",
        )
        return cls.from_xml_tree(xml_element, custom_data_types)

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
    ) -> Self:
        """Create a GenericScxmlRoot object from an XML tree."""
        # --- Get the ElementTree objects
        assert_xml_tag_ok(cls, xml_tree)
        scxml_name = get_xml_attribute(cls, xml_tree, "name")
        assert isinstance(scxml_name, str)  # MyPy check only
        scxml_version = get_xml_attribute(cls, xml_tree, "version")
        assert (
            scxml_version == "1.0"
        ), f"Error: SCXML root: expected version 1.0, found {scxml_version}."
        scxml_init_state = get_xml_attribute(cls, xml_tree, "initial")
        assert isinstance(scxml_init_state, str)  # MyPy check only
        scxml_datamodel = get_children_as_scxml(xml_tree, custom_data_types, (ScxmlDataModel,))
        assert (
            len(scxml_datamodel) <= 1
        ), f"Error: SCXML root: {len(scxml_datamodel)} datamodels found, max 1 allowed."
        # ASCXML Declarations
        ascxml_declarations = get_children_as_scxml(
            xml_tree, custom_data_types, cls.get_declaration_classes()
        )
        # Additional threads
        ascxml_threads = get_children_as_scxml(
            xml_tree, custom_data_types, cls.get_thread_classes()
        )
        # States
        scxml_states = get_children_as_scxml(xml_tree, custom_data_types, (ScxmlState,))
        assert len(scxml_states) > 0, "Error: SCXML root: no state found in input xml."
        # --- Fill Data in the GenericScxmlRoot object
        scxml_root = cls(scxml_name)
        # Data Model
        if len(scxml_datamodel) > 0:
            assert isinstance(scxml_datamodel[0], ScxmlDataModel)  # MyPy check
            scxml_root.set_data_model(scxml_datamodel[0])
        # States
        for scxml_state in scxml_states:
            assert isinstance(scxml_state, ScxmlState)  # MyPy check
            is_initial = scxml_state.get_id() == scxml_init_state
            scxml_root.add_state(scxml_state, initial=is_initial)
        # ASCXML-specific data (declarations and additional-threads)
        scxml_root._ascxml_declarations = ascxml_declarations  # type: ignore
        scxml_root._ascxml_threads = ascxml_threads  # type: ignore
        return scxml_root

    def __init__(self, name: str):
        self._name = name
        self._version = "1.0"  # This is the only version mentioned in the official documentation
        self._initial_state: Optional[str] = None
        self._states: List[ScxmlState] = []
        self._data_model: ScxmlDataModel = ScxmlDataModel()
        self._ascxml_declarations: List[AscxmlDeclaration] = []
        self._ascxml_threads: List[AscxmlThread] = []

    def get_name(self) -> str:
        """Get the name of the automaton represented by this SCXML model."""
        return self._name

    def set_name(self, name: str) -> None:
        """Rename the automaton represented by this SCXML model."""
        assert is_non_empty_string(type(self), "name", name)
        self._name = name

    def get_initial_state_id(self) -> str:
        """Get the ID of the initial state of the SCXML model."""
        assert self._initial_state is not None, "Error: SCXML root: Initial state not set."
        return self._initial_state

    def get_data_model(self) -> ScxmlDataModel:
        return self._data_model

    def get_declarations(self) -> List[AscxmlDeclaration]:
        """Get all the declarations contained in the (A)SCXML model."""
        return self._ascxml_declarations

    def get_threads(self) -> List[AscxmlThread]:
        """Get the threads in the (A)SCXML model."""
        return self._ascxml_threads

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

    def get_state_by_id(self, state_id: str) -> Optional[ScxmlState]:
        for state in self._states:
            if state.get_id() == state_id:
                return state
        return None

    def add_state(self, state: ScxmlState, *, initial: bool = False):
        """Append a state to the list of states in the SCXML model.
        If initial is True, set it as the initial state."""
        self._states.append(state)
        if initial:
            assert self._initial_state is None, "Error: SCXML root: Initial state already set"
            self._initial_state = state.get_id()

    def set_data_model(self, data_model: ScxmlDataModel):
        assert len(self._data_model.get_data_entries()) == 0, "Data model already set"
        self._data_model = data_model

    def check_validity(self) -> bool:
        valid_name = is_non_empty_string(type(self), "name", self._name)
        valid_initial_state = is_non_empty_string(type(self), "initial state", self._initial_state)
        valid_data_model = self._data_model.check_validity()
        valid_states = all(
            isinstance(state, ScxmlState) and state.check_validity() for state in self._states
        )
        valid_declarations = all(
            isinstance(scxml_decl, tuple(self.get_declaration_classes()))
            and scxml_decl.check_validity()
            for scxml_decl in self._ascxml_declarations
        )
        valid_threads = all(
            isinstance(scxml_thread, tuple(self.get_thread_classes()))
            and scxml_thread.check_validity()
            for scxml_thread in self._ascxml_threads
        )
        xml_orig = self.get_xml_origin()
        if not valid_name:
            log_error(xml_orig, "Model without a valid name.")
        if not valid_data_model:
            log_error(xml_orig, f"Model {self._name}: Invalid datamodel definition.")
        if not valid_initial_state:
            log_error(xml_orig, f"Model {self._name}: No initial state defined.")
        if not valid_states:
            log_error(xml_orig, f"Model {self._name}: Invalid states definition.")
        if not valid_threads:
            log_error(xml_orig, f"Model {self._name}: Invalid threads definition.")
        if not valid_declarations:
            log_error(xml_orig, f"Model {self._name}: Invalid declarations definition.")
        return (
            valid_name
            and valid_initial_state
            and valid_states
            and valid_data_model
            and valid_declarations
        )

    def is_plain_scxml(self, verbose: bool = False) -> bool:
        """Check whether there are ROS or BT specific tags in the SCXML model."""
        assert self.check_validity(), get_error_msg(
            self.get_xml_origin(), "SCXML: found invalid root object."
        )
        plain_data_model = self._data_model.is_plain_scxml(verbose)
        no_declarations = len(self._ascxml_declarations) == 0
        no_threads = len(self._ascxml_threads) == 0
        plain_states = all(state.is_plain_scxml(verbose) for state in self._states)
        if verbose:
            if not plain_data_model:
                log_warning(None, f"Failed conversion in {self._name}: no plain data model.")
            if not no_declarations:
                log_warning(None, f"Failed conversion in {self._name}: ASCXML declarations left.")
            if not no_threads:
                log_warning(None, f"Failed conversion in {self._name}: unprocessed threads left.")
            if not plain_states:
                log_warning(None, f"Failed conversion in {self._name}: non-plain states found.")
        return plain_data_model and no_declarations and no_threads and plain_states

    def _to_plain_scxml_impl(self, **kwargs):
        """
        Convert a GenericScxmlRoot object to ScxmlRoot ones.

        This method should be called from the to_plain_scxml one.
        kwargs is used to pass possible, framework specific arguments to the underlying content.
        """
        check_assertion(self.check_validity(), self.get_xml_origin(), "Invalid content.")
        if self.is_plain_scxml():
            # Cast any instance to the ScxmlRoot type before returning it
            new_root = ScxmlRoot(self.get_name())
            new_root.__dict__.update(self.__dict__)
            return [new_root]
        converted_scxmls: List[ScxmlRoot] = []
        # Convert the ROS specific entries to plain SCXML
        main_scxml = ScxmlRoot(self._name)
        main_scxml._initial_state = self._initial_state
        for ascxml_decl in self._ascxml_declarations:
            ascxml_decl.preprocess_declaration(
                self._ascxml_declarations, model_name=self._name, **kwargs
            )
        data_information = ScxmlStructDeclarationsContainer(
            self._name, self._data_model, self.get_custom_data_types()
        )
        data_models = self._data_model.as_plain_scxml(
            data_information, self._ascxml_declarations, **kwargs
        )
        assert len(data_models) == 1, "There can only be on data model per SCXML."
        main_scxml._data_model = data_models[0]
        main_scxml._states = []
        for state in self._states:
            main_scxml._states.extend(
                state.as_plain_scxml(data_information, self._ascxml_declarations, **kwargs)
            )
        converted_scxmls.append(main_scxml)
        for scxml_thread in self._ascxml_threads:
            # Threads have their own datamodel, do not pass the one from this object
            converted_scxmls.extend(
                scxml_thread.as_plain_scxml(None, self._ascxml_declarations, **kwargs)
            )
        for plain_scxml in converted_scxmls:
            assert isinstance(plain_scxml, ScxmlRoot), (
                "Error: SCXML root: conversion to plain SCXML resulted in invalid object "
                f"(expected ScxmlRoot, obtained {type(plain_scxml)}."
            )
            assert plain_scxml.check_validity(), (
                f"The SCXML root object {plain_scxml.get_name()} is not valid: "
                "conversion to plain SCXML failed."
            )
            assert plain_scxml.is_plain_scxml(verbose=True), (
                f"The SCXML root object {plain_scxml.get_name()} is not plain SCXML: "
                "conversion to plain SCXML failed."
            )
        return converted_scxmls

    def to_plain_scxml(self) -> List["ScxmlRoot"]:
        """
        Convert a GenericScxmlRoot object to ScxmlRoot ones, that are framework agnostic.

        :return: a list of ScxmlRoot objects with all custom entries as plain SCXML.
        """
        return self._to_plain_scxml_impl()

    def as_plain_scxml(self, struct_declarations, ascxml_declarations, **kwargs):
        raise RuntimeError("Unexpected use of 'as_plain_scxml' for ScxmlRoot objects.")

    def add_target_to_event_send(self, events_to_targets: EventsToAutomata) -> None:
        """
        For each "ScxmlSend" instance, add the names of the automata receiving the sent event.

        :param events_to_targets: Mapping between the event name and the automata recipients.
        """
        for state in self._states:
            state.add_target_to_event_send(events_to_targets)

    def replace_strings_types_with_integer_arrays(self) -> None:
        """
        Replace all occurrences of strings in the datamodel and the expressions with array of int.
        """
        check_assertion(
            self.is_plain_scxml(),
            self.get_xml_origin(),
            f"{self.get_name()} model is not plain SCXML yet.",
        )
        # Replace string entries in the datamodel
        self._data_model.replace_strings_types_with_integer_arrays()
        # Go over the various states and substitute all the strings in the expressions
        for scxml_state in self._states:
            scxml_state.replace_strings_types_with_integer_arrays()

    def as_xml(self, **kwargs) -> XmlElement:
        assert self.check_validity(), "SCXML: found invalid root object."
        assert self._initial_state is not None, "Error: SCXML root: no initial state set."
        data_type_as_attribute = kwargs.get("data_type_as_attribute", True)
        xml_root = ET.Element(
            self.get_tag_name(),
            {
                "name": self._name,
                "version": self._version,
                "model_src": "",
                "initial": self._initial_state,
                "xmlns": "http://www.w3.org/2005/07/scxml",
            },
        )
        if len(self._data_model.get_data_entries()) > 0:
            data_model_xml = self._data_model.as_xml(data_type_as_attribute)
            assert data_model_xml is not None, "Error: SCXML root: invalid data model."
            xml_root.append(data_model_xml)
        for ascxml_declaration in self._ascxml_declarations:
            xml_root.append(ascxml_declaration.as_xml())
        for ascxml_thread in self._ascxml_threads:
            xml_root.append(ascxml_thread.as_xml())
        for state in self._states:
            xml_root.append(state.as_xml())
        ET.indent(xml_root, "    ")
        return xml_root

    def as_xml_string(self, **kwargs) -> str:
        return ET.tostring(self.as_xml(**kwargs), encoding="unicode")


class ScxmlRoot(GenericScxmlRoot):
    """A whole SCXML model, complying with the existing standard (https://www.w3.org/TR/scxml/)."""

    @staticmethod
    def get_tag_name() -> str:
        """Get the expected tag name related to this class."""
        return "scxml"

    @classmethod
    def get_declaration_classes(cls) -> List[Type[AscxmlDeclaration]]:
        return []

    @classmethod
    def get_thread_classes(cls) -> List[Type[AscxmlThread]]:
        return []
