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

from typing import Dict, List, Optional

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.scxml_converter.scxml_entries.scxml_executable_entry import ScxmlExecutableEntry, ScxmlExecutionBody

from as2fm.as2fm_common.common import is_comment
from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration

from as2fm.scxml_converter.data_types.struct_definition import StructDefinition

from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    CallbackType,
    convert_expression_with_string_literals,
    get_plain_expression,
)
from as2fm.scxml_converter.scxml_entries.xml_utils import (
    assert_xml_tag_ok,
)


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

    def get_conditional_executions(self) -> List[ConditionalExecutionBody]:
        """Get the conditional executions."""
        return self._conditional_executions

    def get_else_execution(self) -> ScxmlExecutionBody:
        """Get the else execution."""
        return self._else_execution

    def has_bt_blackboard_input(self, bt_ports_handler: BtPortsHandler):
        """Check whether the If entry reads content from the BT Blackboard."""
        for _, cond_body in self._conditional_executions:
            if has_bt_blackboard_input(cond_body, bt_ports_handler):
                return True
        return has_bt_blackboard_input(self._else_execution, bt_ports_handler)

    def instantiate_bt_events(
        self, instance_id: int, children_ids: List[int]
    ) -> ScxmlExecutionBody:
        """Instantiate the behavior tree events in the If action, if available."""
        expanded_condition_bodies: List[ConditionalExecutionBody] = []
        for condition, exec_body in self._conditional_executions:
            expanded_condition_bodies.append(
                (condition, instantiate_exec_body_bt_events(exec_body, instance_id, children_ids))
            )
        expanded_else_body = instantiate_exec_body_bt_events(
            self._else_execution, instance_id, children_ids
        )
        return [ScxmlIf(expanded_condition_bodies, expanded_else_body)]

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler):
        for _, exec_body in self._conditional_executions:
            update_exec_body_bt_ports_values(exec_body, bt_ports_handler)
        update_exec_body_bt_ports_values(self._else_execution, bt_ports_handler)

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

    def check_valid_ros_instantiations(
        self, ros_declarations: ScxmlRosDeclarationsContainer
    ) -> bool:
        """Check if the ros instantiations have been declared."""
        # Check the executable content
        assert isinstance(
            ros_declarations, ScxmlRosDeclarationsContainer
        ), "Error: SCXML if: invalid ROS declarations type provided."
        for _, exec_body in self._conditional_executions:
            for exec_entry in exec_body:
                if not exec_entry.check_valid_ros_instantiations(ros_declarations):
                    return False
        for exec_entry in self._else_execution:
            if not exec_entry.check_valid_ros_instantiations(ros_declarations):
                return False
        return True

    def set_thread_id(self, thread_id: int) -> None:
        """Set the thread ID for the executable entries contained in the if object."""
        for _, exec_body in self._conditional_executions:
            for entry in exec_body:
                if hasattr(entry, "set_thread_id"):
                    entry.set_thread_id(thread_id)
        for entry in self._else_execution:
            if hasattr(entry, "set_thread_id"):
                entry.set_thread_id(thread_id)

    def is_plain_scxml(self) -> bool:
        if type(self) is ScxmlIf:
            return all(
                is_plain_execution_body(body) for _, body in self._conditional_executions
            ) and is_plain_execution_body(self._else_execution)
        return False

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ros_declarations: ScxmlRosDeclarationsContainer,
    ) -> List["ScxmlIf"]:
        assert self._cb_type is not None, "Error: SCXML if: callback type not set."
        conditional_executions = []
        for condition, execution in self._conditional_executions:
            set_execution_body_callback_type(execution, self._cb_type)
            execution_body = as_plain_execution_body(
                execution, struct_declarations, ros_declarations
            )
            assert execution_body is not None, "Error: SCXML if: invalid execution body."
            conditional_executions.append(
                (
                    get_plain_expression(condition, self._cb_type, struct_declarations),
                    execution_body,
                )
            )
        set_execution_body_callback_type(self._else_execution, self._cb_type)
        else_execution = as_plain_execution_body(
            self._else_execution, struct_declarations, ros_declarations
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

    def as_xml(self) -> XmlElement:
        # Based on example in https://www.w3.org/TR/scxml/#if
        assert self.check_validity(), "SCXML: found invalid if object."
        first_conditional_execution = self._conditional_executions[0]
        xml_if = ET.Element(ScxmlIf.get_tag_name(), {"cond": first_conditional_execution[0]})
        append_execution_body_to_xml(xml_if, first_conditional_execution[1])
        for condition, execution in self._conditional_executions[1:]:
            xml_if.append(ET.Element("elseif", {"cond": condition}))
            append_execution_body_to_xml(xml_if, execution)
        if len(self._else_execution) > 0:
            xml_if.append(ET.Element("else"))
            append_execution_body_to_xml(xml_if, self._else_execution)
        return xml_if
