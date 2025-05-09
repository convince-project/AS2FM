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

"""
A single transition in SCXML. In XML, it has the tag `transition`.
"""

from typing import Dict, List, Optional
from warnings import warn

from lxml import etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.scxml_converter.scxml_entries import (
    ScxmlBase,
    ScxmlExecutableEntry,
    ScxmlExecutionBody,
    ScxmlRosDeclarationsContainer,
)
from as2fm.scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from as2fm.scxml_converter.scxml_entries.scxml_executable_entries import (
    execution_body_from_xml,
    has_bt_blackboard_input,
    instantiate_exec_body_bt_events,
    is_plain_execution_body,
    set_execution_body_callback_type,
    valid_execution_body,
    valid_execution_body_entry_types,
)
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import CallbackType, is_non_empty_string
from as2fm.scxml_converter.scxml_entries.xml_utils import get_xml_attribute
from as2fm.scxml_converter.xml_data_types.xml_struct_definition import XmlStructDefinition


class ScxmlTransitionTarget(ScxmlBase):
    """This class represents a single scxml transition target."""

    @staticmethod
    def get_tag_name() -> str:
        return "target"

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, custom_data_types: Dict[str, XmlStructDefinition]
    ) -> "ScxmlTransitionTarget":
        """Create a ScxmlTransitionTarget object from an XML tree."""
        assert xml_tree.tag == ScxmlTransitionTarget.get_tag_name(), (
            "Error: SCXML transition target: XML root tag name is "
            + f"not {ScxmlTransitionTarget.get_tag_name()}."
        )
        target_id = get_xml_attribute(cls, xml_tree, "id")
        assert target_id is not None, "Error: SCXML transition target: id not found."
        probability_str: Optional[str] = get_xml_attribute(
            cls, xml_tree, "prob", undefined_allowed=True
        )
        if probability_str is None:
            probability = None
        else:
            probability = float(probability_str)
            if probability == 0.0:
                warn("Warning: SCXML transition target: Probability is zero.")
        exec_body = execution_body_from_xml(xml_tree, custom_data_types)
        return ScxmlTransitionTarget(target_id, probability, exec_body)

    def __init__(
        self,
        target_id: str,
        probability: Optional[float] = None,
        body: Optional[ScxmlExecutionBody] = None,
    ):
        """
        Generate a new transition target, including its execution body and probability.

        :param target_id: The state transition goes to. Required (unlike in SCXML specifications).
        :param probability: The likelihood of taking this target what the transition is selected.
        :param body: Content that is executed when the transition happens.
        """
        assert (
            isinstance(target_id, str) and len(target_id) > 0
        ), "Error SCXML transition target: target id must be a non-empty string."
        assert probability is None or isinstance(
            probability, float
        ), "Error SCXML transition target: probability must be a float."
        assert valid_execution_body_entry_types(
            body
        ), "Error SCXML transition target: invalid body provided."
        self._target_id = target_id
        self._probability = probability
        self._body = body
        self._cb_type: Optional[CallbackType] = None

    def set_callback_type(self, cb_type: CallbackType):
        """Configure the callback type associated to this transition_target instance."""
        self._cb_type = cb_type

    def get_target_id(self) -> str:
        """Return the ID of the target state of this transition."""
        return self._target_id

    def set_target_id(self, state_id: str):
        """Set the ID of the target state of this transition."""
        self._target_id = state_id

    def get_probability(self) -> Optional[float]:
        """Return the probability of the target state of this transition."""
        return self._probability

    def set_probability(self, probability: float):
        """Set the probability of the target state of this transition."""
        self._probability = probability

    def get_body(self) -> ScxmlExecutionBody:
        """Return the executable content of this transition."""
        return self._body if self._body is not None else []

    def set_body(self, body: ScxmlExecutionBody) -> None:
        """Set the body of this transition."""
        self._body = body

    def has_bt_blackboard_input(self, bt_ports_handler: BtPortsHandler):
        return has_bt_blackboard_input(self._body, bt_ports_handler)

    def instantiate_bt_events(
        self, instance_id: int, children_ids: List[int]
    ) -> "ScxmlTransitionTarget":
        """Instantiate the BT events in the object's body."""
        self._body = instantiate_exec_body_bt_events(self._body, instance_id, children_ids)
        return self

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        """Update the values of potential entries making use of BT ports."""
        if self._body is not None:
            for entry in self._body:
                entry.update_bt_ports_values(bt_ports_handler)

    def append_body_executable_entry(self, exec_entry: ScxmlExecutableEntry):
        if self._body is None:
            self._body = []
        self._body.append(exec_entry)
        assert valid_execution_body_entry_types(
            self._body
        ), "Error SCXML transition: invalid body entry found after extension."

    def check_validity(self) -> bool:
        """Make sure the object content is valid."""
        valid_target = is_non_empty_string(type(self), "target", self._target_id)
        valid_probability = self._probability is None or (
            isinstance(self._probability, float)
            and self._probability > 0.0
            and self._probability <= 1.0
        )
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_target:
            print("Error SCXML transition target: target must be a non-empty string.")
        if not valid_probability:
            print("Error SCXML transition target: invalid probability value.")
        if not valid_body:
            print("Error SCXML transition target: executable content is not valid.")
        return valid_target and valid_probability and valid_body

    def check_valid_ros_instantiations(
        self, ros_declarations: ScxmlRosDeclarationsContainer
    ) -> bool:
        """Check if the ros instantiations have been declared."""
        # For SCXML transitions, ROS interfaces can be found only in the exec body
        return self._body is None or all(
            entry.check_valid_ros_instantiations(ros_declarations) for entry in self._body
        )

    def set_thread_id(self, thread_id: int) -> None:
        """Set the thread ID for the executable entries of this transition."""
        if self._body is not None:
            for entry in self._body:
                if hasattr(entry, "set_thread_id"):
                    entry.set_thread_id(thread_id)

    def is_plain_scxml(self) -> bool:
        """Check if the transition is a plain scxml entry and contains only plain scxml."""
        return is_plain_execution_body(self._body)

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ros_declarations: ScxmlRosDeclarationsContainer,
    ) -> List["ScxmlTransitionTarget"]:
        assert isinstance(
            ros_declarations, ScxmlRosDeclarationsContainer
        ), "Error: SCXML transition target: invalid ROS declarations container."
        assert self.check_valid_ros_instantiations(
            ros_declarations
        ), "Error: SCXML transition target: invalid ROS instantiations in transition body."
        new_body = None
        assert self._cb_type is not None, "Error: SCXML transition target: cb type not assigned."
        if self._body is not None:
            set_execution_body_callback_type(self._body, self._cb_type)
            new_body = []
            for entry in self._body:
                new_body.extend(entry.as_plain_scxml(struct_declarations, ros_declarations))
        return [ScxmlTransitionTarget(self._target_id, self._probability, new_body)]

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "Error: SCXML transition target: invalid."
        xml_target = ET.Element(ScxmlTransitionTarget.get_tag_name(), {"id": self._target_id})
        if self._probability is not None:
            xml_target.set("prob", str(self._probability))
        if self._body is not None:
            for executable_entry in self._body:
                xml_target.append(executable_entry.as_xml())
        return xml_target
