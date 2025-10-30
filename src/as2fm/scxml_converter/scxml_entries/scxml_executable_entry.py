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
from typing import Dict, List, Optional, Set, Tuple

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

# Map each event ID to a list of automata transitioning using that event
EventsToAutomata = Dict[str, Set[str]]


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

    @abstractmethod
    def set_callback_type(self, cb_type: CallbackType):
        """
        Set the callback type of the body this entry belongs to.

        It needs to be done for this entry and its children.
        """
        pass

    @abstractmethod
    def replace_strings_types_with_integer_arrays(self):
        """Replace all string literals in the contained expressions with plain scxml ones."""
        # TODO: This method should be renamed, it is very unclear...
        pass

    @abstractmethod
    def add_events_targets(
        self, events_to_models: EventsToAutomata
    ) -> List["ScxmlExecutableEntry"]:
        """Add the target models for all events sent by this executable entry."""
        pass


ScxmlExecutionBody = List[ScxmlExecutableEntry]


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
        if not isinstance(entry, ScxmlExecutableEntry):
            print(f"Error: SCXML execution body: invalid entry type '{type(entry)}'.")
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
    tag_to_cls = generate_tag_to_class_map(ScxmlExecutableEntry)  # type: ignore
    exec_tag = xml_tree.tag
    assert exec_tag in tag_to_cls, get_error_msg(
        xml_tree, f"Error: SCXML conversion: tag {exec_tag} isn't an executable entry."
    )
    ExecBodyClass = tag_to_cls[exec_tag]
    assert issubclass(ExecBodyClass, ScxmlExecutableEntry), get_error_msg(
        xml_tree.xml_origin,
        f"Unexpected class '{ExecBodyClass}', not inheriting from 'ScxmlExecutableEntry'.",
    )
    return ExecBodyClass.from_xml_tree(xml_tree, custom_data_types)


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


def set_execution_body_callback_type(exec_body: ScxmlExecutionBody, cb_type: CallbackType) -> None:
    """
    Set the callback type for the provided execution body.

    :param exec_body: The execution body that required the callback type to be set.
    :param cb_type: The callback type to set.
    """
    for entry in exec_body:
        entry.set_callback_type(cb_type)


def is_plain_execution_body(exec_body: Optional[ScxmlExecutionBody], verbose: bool = False) -> bool:
    """Check if al entries in the exec body are plain scxml."""
    if exec_body is None:
        return True
    return all(entry.is_plain_scxml(verbose=verbose) for entry in exec_body)


def as_plain_execution_body(
    exec_body: Optional[ScxmlExecutionBody],
    struct_declarations: ScxmlStructDeclarationsContainer,
    ascxml_declarations: List[AscxmlDeclaration],
    **kwargs,
) -> Optional[ScxmlExecutionBody]:
    """
    Convert the execution body to plain SCXML.

    :param exec_body: The execution body to convert
    :param struct_declarations: Information about the type of data in the automaton's datamodel
    :param ascxml_declarations: All ASCXML declarations set in the model.
    :param kwargs: Additional arguments, framework specific.
    :return: The converted execution body
    """
    if exec_body is None:
        return None
    new_body = []
    for entry in exec_body:
        new_body.extend(entry.as_plain_scxml(struct_declarations, ascxml_declarations, **kwargs))
    assert all(isinstance(entry, ScxmlExecutableEntry) for entry in new_body)
    return new_body  # type: ignore


def replace_string_expressions_in_execution_body(
    exec_body: ScxmlExecutionBody,
) -> ScxmlExecutionBody:
    """In-place replacement for all string literals in the expressions in the exec_body."""
    if exec_body is None:
        return None
    # TODO: In-Place or not in-place substitution? Both would work here...
    new_body: ScxmlExecutionBody = []
    for entry in exec_body:
        new_body.append(entry.replace_strings_types_with_integer_arrays())
    return new_body


def add_targets_to_scxml_sends(
    exec_body: ScxmlExecutionBody, events_to_automata: EventsToAutomata
) -> ScxmlExecutionBody:
    """For each ScxmlSend in the body, generate instances containing the target automaton."""
    if exec_body is None:
        return None
    new_body: ScxmlExecutionBody = []
    for entry in exec_body:
        new_body.extend(entry.add_events_targets(events_to_automata))
    return new_body
