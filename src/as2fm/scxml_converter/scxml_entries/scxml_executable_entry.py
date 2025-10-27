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
Definition of SCXML Tags that can be part of executable content
"""

from abc import abstractmethod
from copy import deepcopy
from typing import Dict, List, Optional, Set, Tuple, get_args

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import is_comment
from as2fm.as2fm_common.logging import get_error_msg
from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration

from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import (
    ScxmlBase,
)
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    CallbackType,
    generate_tag_to_class_map,
)


ScxmlExecutionBody = List["ScxmlExecutableEntry"]
ConditionalExecutionBody = Tuple[str, ScxmlExecutionBody]
# Map each event ID to a list of automata transitioning using that event
EventsToAutomata = Dict[str, Set[str]]


def update_exec_body_configurable_values(
    exec_body: Optional[ScxmlExecutionBody], ascxml_declarations: List[AscxmlDeclaration]
):
    """Update the value of each configurable entry in the execution body."""
    if exec_body is not None:
        for entry in exec_body:
            entry.update_configurable_entry(ascxml_declarations)


def get_config_entries_request_receive_events(
    exec_body: Optional[ScxmlExecutionBody],
) -> List[Tuple[str, str]]:
    """
    Get the request-receive event pairs associated to all config. entries in the executable body.
    """
    body_conf_events: List[Tuple[str, str]] = []
    if exec_body is not None:
        for entry in exec_body:
            config_events = entry.get_config_request_receive_events()
            if config_events is not None and config_events not in body_conf_events:
                body_conf_events.append(config_events)
    return body_conf_events


def update_exec_body_bt_ports_values(
    exec_body: Optional[ScxmlExecutionBody], bt_ports_handler: BtPortsHandler
) -> None:
    """
    Update the BT ports values in the execution body.
    """
    if exec_body is not None:
        for entry in exec_body:
            entry.update_bt_ports_values(bt_ports_handler)


def has_bt_blackboard_input(
    exec_body: Optional[ScxmlExecutionBody], bt_ports_info: BtPortsHandler
) -> bool:
    """
    Check if any entry in the execution body requires reading from the blackboard.
    """
    if exec_body is None:
        return False
    for entry in exec_body:
        # If any entry in the executable body requires reading from the blackboard, report it
        if entry.has_bt_blackboard_input(bt_ports_info):
            return True
    return False


class ScxmlExecutableEntry(ScxmlBase):
    """Generic class for entries that can be part of an executable block."""

    @abstractmethod
    def update_configurable_entry(self, ascxml_declarations: List[AscxmlDeclaration]):
        """Update possible configurable entries in the executable object."""
        pass

    @abstractmethod
    def get_config_request_receive_events(self) -> Optional[Tuple[str, str]]:
        """
        Return the events for requesting-receiving the updated value of a conf. entry, if any."""
        pass

# Get the resolved types from the forward references in ScxmlExecutableEntry
_ResolvedScxmlExecutableEntry = tuple(
    entry._evaluate(globals(), locals(), frozenset()) for entry in get_args(ScxmlExecutableEntry)
)


def valid_execution_body_entry_types(exec_body: Optional[ScxmlExecutionBody]) -> bool:
    """
    Check if the type of the entries in an execution body are valid.

    :param exec_body: The execution body to check
    :return: True if all types of the body entries are the expected ones, False otherwise
    """
    if exec_body is None:
        return True
    if not isinstance(exec_body, list):
        print(f"Error: SCXML execution body: invalid type found: {type(exec_body)} is not a list.")
        return False
    for entry in exec_body:
        if not isinstance(entry, _ResolvedScxmlExecutableEntry):
            print(
                f"Error: SCXML execution body: entry type {type(entry)} not in valid set."
                f" {_ResolvedScxmlExecutableEntry}."
            )
            return False
    return True


def valid_execution_body(exec_body: ScxmlExecutionBody) -> bool:
    """
    Check if an execution body is valid.

    :param execution_body: The execution body to check
    :return: True if the execution body is valid, False otherwise
    """
    if not valid_execution_body_entry_types(exec_body):
        return False
    for entry in exec_body:
        if not entry.check_validity():
            print(f"Error: SCXML execution body: content of {entry.get_tag_name()} is invalid.")
            return False
    return True


def execution_entry_from_xml(
    xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
) -> ScxmlExecutableEntry:
    """
    Create an execution entry from an XML tree.

    :param xml_tree: The XML tree to create the execution entry from.
    :return: The execution entry
    """
    # TODO: This should be generated only once, since it stays as it is
    tag_to_cls: Dict[str, ScxmlExecutableEntry] = {
        cls.get_tag_name(): cls for cls in _ResolvedScxmlExecutableEntry
    }
    tag_to_cls.update(generate_tag_to_class_map(ScxmlSend))
    exec_tag = xml_tree.tag
    assert exec_tag in tag_to_cls, get_error_msg(
        xml_tree, f"Error: SCXML conversion: tag {exec_tag} isn't an executable entry."
    )
    return tag_to_cls[exec_tag].from_xml_tree(xml_tree, custom_data_types)


def execution_body_from_xml(
    xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
) -> ScxmlExecutionBody:
    """
    Create an execution body from an XML tree.

    :param xml_tree: The XML tree to create the execution body from.
    :return: The execution body
    """
    exec_body: ScxmlExecutionBody = []
    for exec_elem_xml in xml_tree:
        if not is_comment(exec_elem_xml):
            exec_body.append(execution_entry_from_xml(exec_elem_xml, custom_data_types))
    return exec_body


def append_execution_body_to_xml(xml_parent: XmlElement, exec_body: ScxmlExecutionBody) -> None:
    """
    Append an execution body to an existing XML element.

    :param xml_parent: The parent XML element to append the executable entries to
    :param exec_body: The execution body to append
    """
    for exec_entry in exec_body:
        xml_parent.append(exec_entry.as_xml())


def set_execution_body_callback_type(exec_body: ScxmlExecutionBody, cb_type: CallbackType) -> None:
    """
    Set the callback type for the provided execution body.

    :param exec_body: The execution body that required the callback type to be set.
    :param cb_type: The callback type to set.
    """
    for entry in exec_body:
        entry.set_callback_type(cb_type)


def is_plain_execution_body(exec_body: Optional[ScxmlExecutionBody]) -> bool:
    """Check if al entries in the exec body are plain scxml."""
    if exec_body is None:
        return True
    return all(entry.is_plain_scxml() for entry in exec_body)


def as_plain_execution_body(
    exec_body: Optional[ScxmlExecutionBody],
    struct_declarations: ScxmlStructDeclarationsContainer,
    ros_declarations: ScxmlRosDeclarationsContainer,
) -> Optional[ScxmlExecutionBody]:
    """
    Convert the execution body to plain SCXML.

    :param exec_body: The execution body to convert
    :param struct_declarations: Information about the type of data in the automaton's datamodel
    :param ros_declarations: The ROS declarations
    :return: The converted execution body
    """
    if exec_body is None:
        return None
    new_body: ScxmlExecutionBody = []
    for entry in exec_body:
        new_body.extend(entry.as_plain_scxml(struct_declarations, ros_declarations))
    return new_body


def replace_string_expressions_in_execution_body(
    exec_body: ScxmlExecutionBody,
) -> ScxmlExecutionBody:
    """In-place replacement for all string literals in the expressions in the exec_body."""
    # TODO: In-Place or not in-place substitution? Both would work here...
    new_body: ScxmlExecutionBody = []
    for entry in exec_body:
        new_body.append(entry.replace_strings_types_with_integer_arrays())
    return new_body


def add_targets_to_scxml_sends(
    exec_body: ScxmlExecutionBody, events_to_automata: EventsToAutomata
) -> ScxmlExecutionBody:
    """For each ScxmlSend in the body, generate instances containing the target automaton."""
    assert exec_body is not None, "Unexpected value of exec_body."
    new_body: ScxmlExecutionBody = []
    for entry in exec_body:
        if isinstance(entry, ScxmlIf):
            if_conditionals = []
            for cond, cond_body in entry.get_conditional_executions():
                if_conditionals.append(
                    (cond, add_targets_to_scxml_sends(cond_body, events_to_automata))
                )
            else_body = add_targets_to_scxml_sends(entry.get_else_execution(), events_to_automata)
            new_body.append(ScxmlIf(if_conditionals, else_body))
        elif isinstance(entry, ScxmlSend):
            target_automata = events_to_automata.get(entry.get_event(), {"NONE"})
            assert (
                entry.get_target_automaton() is None
            ), f"Error: SCXML send: target automaton already set for event {entry.get_event()}."
            for automaton in target_automata:
                new_entry = deepcopy(entry)
                new_entry.set_target_automaton(automaton)
                new_body.append(new_entry)
        elif isinstance(entry, ScxmlAssign):
            new_body.append(deepcopy(entry))
        else:
            raise ValueError(f"Error: SCXML send: invalid entry type {type(entry)}.")
    return new_body
