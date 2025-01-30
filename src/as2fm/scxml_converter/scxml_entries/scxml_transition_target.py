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

from typing import List, Optional

from lxml import etree as ET

from as2fm.scxml_converter.scxml_entries import (
    ScxmlBase,
    ScxmlExecutableEntry,
    ScxmlExecutionBody,
    ScxmlRosDeclarationsContainer,
)
from as2fm.scxml_converter.scxml_entries.bt_utils import BtPortsHandler
from as2fm.scxml_converter.scxml_entries.scxml_executable_entries import (
    has_bt_blackboard_input,
    valid_execution_body,
    valid_execution_body_entry_types,
)
from as2fm.scxml_converter.scxml_entries.utils import is_non_empty_string


class ScxmlTransitionTarget(ScxmlBase):
    """This class represents a single scxml state."""

    @staticmethod
    def get_tag_name() -> str:
        return "target"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlTransitionTarget":
        """Create a ScxmlTransition object from an XML tree."""
        pass

    def __init__(
        self,
        target: str,
        events: Optional[List[str]] = None,
        condition: Optional[str] = None,
        body: Optional[ScxmlExecutionBody] = None,
    ):
        """
        Generate a new transition. Currently, transitions must have a target.

        :param target: The state transition goes to. Required (unlike in SCXML specifications)
        :param events: The events that trigger this transition.
        :param condition: The condition guard to enable/disable the transition
        :param body: Content that is executed when the transition happens
        """
        pass

    def get_target_state_id(self) -> str:
        """Return the ID of the target state of this transition."""
        return self._target

    def set_target_state_id(self, state_id: str):
        self._target = state_id

    def get_events(self) -> List[str]:
        """Return the events that trigger this transition (if any)."""
        return self._events

    def get_condition(self) -> Optional[str]:
        """Return the condition required to execute this transition (if any)."""
        return self._condition

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
    ) -> List["ScxmlTransitionTarget"]:
        """Instantiate the BT events of this transition."""
        pass

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        """Update the values of potential entries making use of BT ports."""
        for entry in self._body:
            entry.update_bt_ports_values(bt_ports_handler)

    def add_event(self, event: str):
        self._events.append(event)

    def append_body_executable_entry(self, exec_entry: ScxmlExecutableEntry):
        if self._body is None:
            self._body = []
        self._body.append(exec_entry)
        assert valid_execution_body_entry_types(
            self._body
        ), "Error SCXML transition: invalid body entry found after extension."

    def check_validity(self) -> bool:
        valid_target = is_non_empty_string(type(self), "target", self._target)
        valid_condition = self._condition is None or (
            is_non_empty_string(type(self), "condition", self._condition)
        )
        valid_events = self._events is None or (
            isinstance(self._events, list) and all(isinstance(ev, str) for ev in self._events)
        )
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_events:
            print("Error: SCXML transition: events are not valid.\nList of events:")
            for event in self._events:
                print(f"\t-'{event}'.")
        if not valid_body:
            print("Error: SCXML transition: executable content is not valid.")
        return valid_target and valid_events and valid_condition and valid_body

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
        pass

    def as_plain_scxml(
        self, ros_declarations: ScxmlRosDeclarationsContainer
    ) -> "ScxmlTransitionTarget":
        pass

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid transition."
        pass
