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
A single state in SCXML. In XML, it has the tag `state`.
"""

from typing import Dict, List, Optional

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import is_comment
from as2fm.as2fm_common.logging import check_assertion, get_error_msg, log_warning
from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import (
    EventsToAutomata,
    ScxmlBase,
    ScxmlExecutableEntry,
    ScxmlExecutionBody,
    ScxmlSend,
    ScxmlTransition,
    ScxmlTransitionTarget,
)
from as2fm.scxml_converter.scxml_entries.scxml_executable_entry import (
    add_targets_to_scxml_sends,
    as_plain_execution_body,
    execution_body_from_xml,
    get_config_entries_request_receive_events,
    is_plain_execution_body,
    replace_string_expressions_in_execution_body,
    set_execution_body_callback_type,
    update_exec_body_configurable_values,
    valid_execution_body,
)
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import CallbackType, generate_tag_to_class_map


class ScxmlState(ScxmlBase):
    """This class represents a single scxml state."""

    @staticmethod
    def get_tag_name() -> str:
        return "state"

    @staticmethod
    def _transitions_from_xml(
        state_id: str, xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
    ) -> List[ScxmlTransition]:
        transitions: List[ScxmlTransition] = []
        tag_to_cls = generate_tag_to_class_map(ScxmlTransition)
        for child in xml_tree:
            if is_comment(child):
                continue
            elif child.tag in tag_to_cls:
                TagClass = tag_to_cls[child.tag]
                assert issubclass(TagClass, ScxmlTransition)  # MyPy check
                transitions.append(TagClass.from_xml_tree(child, custom_data_types))
            else:
                assert child.tag in (
                    "onentry",
                    "onexit",
                ), get_error_msg(
                    xml_tree, f"Error: SCXML state {state_id}: unexpected tag {child.tag}."
                )
        return transitions

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
    ) -> "ScxmlState":
        """Create a ScxmlState object from an XML tree."""
        assert (
            xml_tree.tag == ScxmlState.get_tag_name()
        ), f"Error: SCXML state: XML tag name is not {ScxmlState.get_tag_name()}."
        id_ = xml_tree.attrib.get("id")
        assert id_ is not None and len(id_) > 0, "Error: SCXML state: id is not valid."
        scxml_state = ScxmlState(id_)
        # Get the onentry and onexit execution bodies
        on_entry = xml_tree.findall("onentry")
        assert (
            len(on_entry) <= 1
        ), f"Error: SCXML state: {len(on_entry)} onentry tags found, expected 0 or 1."
        on_exit = xml_tree.findall("onexit")
        assert (
            len(on_exit) <= 1
        ), f"Error: SCXML state: {len(on_exit)} onexit tags found, expected 0 or 1."
        if len(on_entry) > 0:
            for exec_entry in execution_body_from_xml(on_entry[0], custom_data_types):
                scxml_state.append_on_entry(exec_entry)
        if len(on_exit) > 0:
            for exec_entry in execution_body_from_xml(on_exit[0], custom_data_types):
                scxml_state.append_on_exit(exec_entry)
        # Get the transitions in the state body
        for body_entry in ScxmlState._transitions_from_xml(id_, xml_tree, custom_data_types):
            scxml_state.add_transition(body_entry)
        return scxml_state

    def __init__(
        self,
        state_id: str,
        *,
        on_entry: Optional[ScxmlExecutionBody] = None,
        on_exit: Optional[ScxmlExecutionBody] = None,
        body: Optional[List[ScxmlTransition]] = None,
    ):
        """
        Initialize a new ScxmlState object.

        :param state_id: The id of the state, unique in the ScxmlRoot object.
        :param on_entry: The executable entries to be executed on entry.
        :param on_exit: The executable entries to be executed on exit.
        :param body: The transitions leaving the state.
        """
        self._id: str = state_id
        self._on_entry: ScxmlExecutionBody = on_entry if on_entry is not None else []
        self._on_exit: ScxmlExecutionBody = on_exit if on_exit is not None else []
        self._body: List[ScxmlTransition] = body if body is not None else []

    def get_id(self) -> str:
        return self._id

    def get_onentry(self) -> ScxmlExecutionBody:
        return self._on_entry

    def get_onexit(self) -> ScxmlExecutionBody:
        return self._on_exit

    def get_body(self) -> List[ScxmlTransition]:
        """Return the transitions leaving the state."""
        return self._body

    def _generate_variable_config_retrieval(self):
        """
        Split the state in config. request and receive, if there are non constant ones.
        """
        generated_states: List[ScxmlState] = [self]
        on_entry_config_events = get_config_entries_request_receive_events(self._on_entry)
        on_exit_config_events = get_config_entries_request_receive_events(self._on_exit)
        check_assertion(
            len(on_entry_config_events) == 0,
            self.get_xml_origin(),
            (
                f"Error: SCXML state {self.get_id()}: reading blackboard variables from onentry. "
                "This isn't yet supported."
            ),
        )
        check_assertion(
            len(on_exit_config_events) == 0,
            self.get_xml_origin(),
            (
                f"Error: SCXML state {self.get_id()}: reading blackboard variables from onexit. "
                "This isn't yet supported."
            ),
        )
        for transit_id in range(len(self._body)):
            transition_config_events = self._body[transit_id].get_config_request_receive_events()
            if len(transition_config_events) > 0:
                check_assertion(
                    len(transition_config_events) == 1,
                    self.get_xml_origin(),
                    "Only one category of variable conf. entries per body are currently supported.",
                )
                # For now, make sure this is a transitions with a single target
                check_assertion(
                    len(self._body[transit_id].get_targets()) == 1,
                    self.get_xml_origin(),
                    "Var. config entries support isn't compatible yet with prob. transitions.",
                )
                conf_req_event, conf_rec_event = transition_config_events[0]
                # Prepare the new state with the original body, using the received config updates
                states_count = len(generated_states)
                new_state_id = (
                    f"{self.get_id()}_{self._body[transit_id].get_tag_name()}_{states_count}"
                )
                new_state = ScxmlState(new_state_id)
                blackboard_transition = ScxmlTransition(
                    self._body[transit_id].get_targets(), [conf_rec_event]
                )
                new_state.add_transition(blackboard_transition)
                generated_states.append(new_state)
                # Set the new target and body to the original transition: request the conf. updates
                new_transition_target = ScxmlTransitionTarget(
                    new_state_id, body=[ScxmlSend(conf_req_event)]
                )
                self._body[transit_id].set_targets([new_transition_target])
        return generated_states

    def add_transition(self, transition: ScxmlTransition) -> None:
        self._body.append(transition)

    def append_on_entry(self, executable_entry: ScxmlExecutableEntry) -> None:
        self._on_entry.append(executable_entry)

    def append_on_exit(self, executable_entry: ScxmlExecutableEntry) -> None:
        self._on_exit.append(executable_entry)

    def set_on_entry(self, on_entry: ScxmlExecutionBody) -> None:
        self._on_entry = on_entry

    def set_on_exit(self, on_exit: ScxmlExecutionBody) -> None:
        self._on_exit = on_exit

    def check_validity(self) -> bool:
        valid_id = isinstance(self._id, str) and len(self._id) > 0
        valid_on_entry = self._on_entry is None or valid_execution_body(self._on_entry)
        valid_on_exit = self._on_exit is None or valid_execution_body(self._on_exit)
        valid_body = True
        if self._body is not None:
            valid_body = isinstance(self._body, list)
            if valid_body:
                for transition in self._body:
                    valid_transition = (
                        isinstance(transition, ScxmlTransition) and transition.check_validity()
                    )
                    if not valid_transition:
                        valid_body = False
                        break
        if not valid_id:
            print("Error: SCXML state: id is not valid.")
        if not valid_on_entry:
            print(f"Error: SCXML state {self._id}: on_entry is not valid.")
        if not valid_on_exit:
            print(f"Error: SCXML state {self._id}: on_exit is not valid.")
        if not valid_body:
            print(f"Error: SCXML state {self._id}: executable body is not valid.")
        return valid_on_entry and valid_on_exit and valid_body

    def is_plain_scxml(self, verbose: bool = False) -> bool:
        """Check if all SCXML entries in the state are plain scxml."""
        plain_entry = is_plain_execution_body(self._on_entry, verbose)
        plain_exit = is_plain_execution_body(self._on_exit, verbose)
        plain_body = all(transition.is_plain_scxml(verbose) for transition in self._body)
        if verbose:
            if not plain_entry:
                log_warning(None, f"Failed conversion of state {self._id}: onentry not plain.")
            if not plain_exit:
                log_warning(None, f"Failed conversion of state {self._id}: onexit not plain.")
            if not plain_entry:
                log_warning(None, f"Failed conversion of state {self._id}: non plain transitions.")
        return plain_entry and plain_exit and plain_body

    def _as_plain_scxml_replacements(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> "ScxmlState":
        """Implementation of plain scxml sub-entries conversion."""
        set_execution_body_callback_type(self._on_entry, CallbackType.STATE)
        set_execution_body_callback_type(self._on_exit, CallbackType.STATE)
        plain_entry = as_plain_execution_body(
            self._on_entry, struct_declarations, ascxml_declarations, **kwargs
        )
        plain_exit = as_plain_execution_body(
            self._on_exit, struct_declarations, ascxml_declarations, **kwargs
        )
        plain_body: List[ScxmlBase] = []
        for entry in self._body:
            plain_body.extend(
                entry.as_plain_scxml(struct_declarations, ascxml_declarations, **kwargs)
            )
        assert all(isinstance(entry, ScxmlTransition) for entry in plain_body)  # MyPy check
        return ScxmlState(
            self._id, on_entry=plain_entry, on_exit=plain_exit, body=plain_body  # type: ignore
        )

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        """Remove framework specific entries and make a state containing only plain SCXML."""
        # Update the value of all AscxmlConfig entries in the state
        update_exec_body_configurable_values(self._on_entry, ascxml_declarations)
        update_exec_body_configurable_values(self._on_exit, ascxml_declarations)
        for transition in self._body:
            transition.update_exec_body_configurable_values(ascxml_declarations)
        # Expand the state to get possible variable config entries
        expanded_states = self._generate_variable_config_retrieval()
        plain_states: List[ScxmlBase] = []
        for new_state in expanded_states:
            plain_states.append(
                new_state._as_plain_scxml_replacements(
                    struct_declarations, ascxml_declarations, **kwargs
                )
            )
        return plain_states

    def add_target_to_event_send(self, events_to_targets: EventsToAutomata) -> None:
        """Update all send event tags to include the target scxml model."""
        self._on_entry = add_targets_to_scxml_sends(self._on_entry, events_to_targets)
        self._on_exit = add_targets_to_scxml_sends(self._on_exit, events_to_targets)
        for transition in self._body:
            transition.add_targets_to_scxml_sends(events_to_targets)

    def replace_strings_types_with_integer_arrays(self) -> None:
        """Replace all the strings that appear in the SCXML expressions."""
        self._on_entry = replace_string_expressions_in_execution_body(self._on_entry)
        self._on_exit = replace_string_expressions_in_execution_body(self._on_exit)
        for transition in self._body:
            transition.replace_strings_types_with_integer_arrays()

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "SCXML: found invalid state object."
        xml_state = ET.Element(ScxmlState.get_tag_name(), {"id": self._id})
        if len(self._on_entry) > 0:
            xml_on_entry = ET.Element("onentry")
            for executable_entry in self._on_entry:
                xml_on_entry.append(executable_entry.as_xml())
            xml_state.append(xml_on_entry)
        if len(self._on_exit) > 0:
            xml_on_exit = ET.Element("onexit")
            for executable_entry in self._on_exit:
                xml_on_exit.append(executable_entry.as_xml())
            xml_state.append(xml_on_exit)
        for transition in self._body:
            xml_state.append(transition.as_xml())
        return xml_state
