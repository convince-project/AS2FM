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

from typing import Dict, List, Optional, Tuple

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import is_comment
from as2fm.as2fm_common.logging import get_error_msg, log_warning
from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries.scxml_base import ScxmlBase
from as2fm.scxml_converter.scxml_entries.scxml_executable_entry import (
    EventsToAutomata,
    ScxmlExecutableEntry,
    ScxmlExecutionBody,
    as_plain_execution_body,
    execution_entry_from_xml,
    get_config_entries_request_receive_events,
    is_plain_execution_body,
    replace_string_expressions_in_execution_body,
    set_execution_body_callback_type,
    update_exec_body_configurable_values,
    valid_execution_body,
)
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    CallbackType,
    convert_expression_with_string_literals,
    get_plain_expression,
)
from as2fm.scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok,
)

ConditionalExecutionBody = Tuple[str, ScxmlExecutionBody]


class ScxmlIf(ScxmlExecutableEntry):
    """This class represents SCXML conditionals."""

    @staticmethod
    def get_tag_name() -> str:
        return "if"

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
    ) -> "ScxmlIf":
        """
        Create a ScxmlIf object from an XML tree.

        :param xml_tree: The XML tree to create the object from.
        :param cb_type: The kind of callback executing this SCXML entry.
        """
        assert_xml_tag_ok(ScxmlIf, xml_tree)
        conditions: List[str] = []
        exec_bodies: List[ScxmlExecutionBody] = []
        conditions.append(xml_tree.attrib["cond"])
        current_body: ScxmlExecutionBody = []
        else_tag_found = False
        for child in xml_tree:
            if is_comment(child):
                continue
            if child.tag == "elseif":
                assert not else_tag_found, "Error: SCXML if: 'elseif' tag found after 'else' tag."
                conditions.append(child.attrib["cond"])
                exec_bodies.append(current_body)
                current_body = []
            elif child.tag == "else":
                assert not else_tag_found, "Error: SCXML if: multiple 'else' tags found."
                else_tag_found = True
                exec_bodies.append(current_body)
                current_body = []
            else:
                current_body.append(execution_entry_from_xml(child, custom_data_types))
        else_body: Optional[ScxmlExecutionBody] = None
        if else_tag_found:
            else_body = current_body
        else:
            exec_bodies.append(current_body)
        assert len(conditions) == len(exec_bodies), (
            "Error: SCXML if: number of conditions and bodies do not match "
            f"({len(conditions)} != {len(exec_bodies)}). Conditions: {conditions}."
        )
        return ScxmlIf(list(zip(conditions, exec_bodies)), else_body)

    def __init__(
        self,
        conditional_executions: List[ConditionalExecutionBody],
        else_execution: Optional[ScxmlExecutionBody] = None,
    ):
        """
        Class representing a conditional execution in SCXML.

        :param conditional_executions: List of (condition - exec. body) pairs. Min n. pairs is one.
        :param else_execution: Execution to be done if no condition is met.
        :param cb_type: The kind of callback executing this SCXML entry.
        """
        self._conditional_executions: List[ConditionalExecutionBody] = conditional_executions
        self._else_execution: ScxmlExecutionBody = []
        if else_execution is not None:
            self._else_execution = else_execution
        self._cb_type: Optional[CallbackType] = None

    def set_callback_type(self, cb_type: CallbackType) -> None:
        """Set the cb type for this entry and its children."""
        self._cb_type = cb_type
        for _, cond_body in self._conditional_executions:
            set_execution_body_callback_type(cond_body, cb_type)
        set_execution_body_callback_type(self._else_execution, cb_type)

    def get_conditional_executions(self) -> List[ConditionalExecutionBody]:
        """Get the conditional executions."""
        return self._conditional_executions

    def get_else_execution(self) -> ScxmlExecutionBody:
        """Get the else execution."""
        return self._else_execution

    def update_configurable_entry(self, ascxml_declarations: List[AscxmlDeclaration]):
        """Update the content of all execution bodies in the ScxmlIf statement."""
        for _, cond_body in self._conditional_executions:
            update_exec_body_configurable_values(cond_body, ascxml_declarations)
        update_exec_body_configurable_values(self._else_execution, ascxml_declarations)

    def get_config_request_receive_events(self) -> Optional[Tuple[str, str]]:
        """Extract and validate the request-receive event from the 'if' block."""
        config_events: Optional[Tuple[str, str]] = None
        # Check the 'else' block first
        events_list = get_config_entries_request_receive_events(self._else_execution)
        assert len(events_list) <= 1, get_error_msg(
            self.get_xml_origin(),
            f"Expected only one kind of configuration holder, found {len(events_list)}.",
        )
        if len(events_list) > 0:
            config_events = events_list[0]
        # And then the remaining conditional bodies
        for _, cond_body in self._conditional_executions:
            events_list = get_config_entries_request_receive_events(cond_body)
            assert len(events_list) <= 1, get_error_msg(
                self.get_xml_origin(),
                f"Expected only one kind of configuration holder, found {len(events_list)}.",
            )
            if len(events_list) > 0:
                if config_events is None:
                    config_events = events_list[0]
                else:
                    # Make sure that there is only one pair across all bodies in the If statement.
                    assert config_events == events_list[0], get_error_msg(
                        self.get_xml_origin(),
                        "Expected only one kind of configuration holder, but found more than one.",
                    )
        return config_events

    def check_validity(self) -> bool:
        valid_conditional_executions = len(self._conditional_executions) > 0 and all(
            isinstance(condition, str) and len(body) > 0 and valid_execution_body(body)
            for condition, body in self._conditional_executions
        )
        if not valid_conditional_executions:
            print("Error: SCXML if: Found invalid entries in conditional executions.")
        valid_else_execution = valid_execution_body(self._else_execution)
        if not valid_else_execution:
            print("Error: SCXML if: invalid else execution body found.")
        return valid_conditional_executions and valid_else_execution

    def is_plain_scxml(self, verbose: bool = False) -> bool:
        if type(self) is ScxmlIf:
            plain_if = all(
                is_plain_execution_body(body) for _, body in self._conditional_executions
            ) and is_plain_execution_body(self._else_execution)
            if verbose and not plain_if:
                log_warning(None, "No plain SCXML if: condition bodies are not plain.")
            return plain_if
        if verbose:
            log_warning(None, f"No plain SCXML: type {type(self)} isn't a plain if.")
        return False

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        assert self._cb_type is not None, get_error_msg(
            self.get_xml_origin(), "Callback type not set."
        )
        conditional_executions = []
        for condition, execution in self._conditional_executions:
            execution_body = as_plain_execution_body(
                execution, struct_declarations, ascxml_declarations, **kwargs
            )
            assert execution_body is not None, get_error_msg(
                self.get_xml_origin(), "Invalid execution body after conversion."
            )
            conditional_executions.append(
                (
                    get_plain_expression(condition, self._cb_type, struct_declarations),
                    execution_body,
                )
            )
        else_execution = as_plain_execution_body(
            self._else_execution, struct_declarations, ascxml_declarations, **kwargs
        )
        return [ScxmlIf(conditional_executions, else_execution)]

    def replace_strings_types_with_integer_arrays(self) -> "ScxmlIf":
        """Replace all string literals in the contained expressions."""
        new_cond_execs: List[ConditionalExecutionBody] = []
        for cond, body in self._conditional_executions:
            new_cond = convert_expression_with_string_literals(cond)
            new_body = replace_string_expressions_in_execution_body(body)
            new_cond_execs.append((new_cond, new_body))
        new_else_body = replace_string_expressions_in_execution_body(self._else_execution)
        return ScxmlIf(new_cond_execs, new_else_body)

    def add_events_targets(self, events_to_models: EventsToAutomata):
        """Add the events targets to the execution bodies in the If statement."""
        if_conditionals: List[ConditionalExecutionBody] = []
        for cond, cond_body in self._conditional_executions:
            new_cond_body = []
            for ex_entry in cond_body:
                new_cond_body.extend(ex_entry.add_events_targets(events_to_models))
            if_conditionals.append((cond, new_cond_body))
        else_body = []
        for ex_entry in self._else_execution:
            else_body.extend(ex_entry.add_events_targets(events_to_models))
        return [ScxmlIf(if_conditionals, else_body)]

    @staticmethod
    def _append_execution_body_to_xml(xml_parent: XmlElement, exec_body: ScxmlExecutionBody):
        """
        Append an execution body to an existing XML element.

        :param xml_parent: The parent XML element to append the executable entries to
        :param exec_body: The execution body to append
        """
        for exec_entry in exec_body:
            xml_parent.append(exec_entry.as_xml())

    def as_xml(self) -> XmlElement:
        # Based on example in https://www.w3.org/TR/scxml/#if
        assert self.check_validity(), "SCXML: found invalid if object."
        first_conditional_execution = self._conditional_executions[0]
        xml_if = ET.Element(ScxmlIf.get_tag_name(), {"cond": first_conditional_execution[0]})
        self._append_execution_body_to_xml(xml_if, first_conditional_execution[1])
        for condition, execution in self._conditional_executions[1:]:
            xml_if.append(ET.Element("elseif", {"cond": condition}))
            self._append_execution_body_to_xml(xml_if, execution)
        if len(self._else_execution) > 0:
            xml_if.append(ET.Element("else"))
            self._append_execution_body_to_xml(xml_if, self._else_execution)
        return xml_if
