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
A single transition in SCXML. In XML, it has the tag `transition`.
"""

import warnings
from typing import List, Optional

from lxml import etree as ET

from as2fm.scxml_converter.scxml_entries import (
    ScxmlBase,
    ScxmlExecutableEntry,
    ScxmlExecutionBody,
    ScxmlRosDeclarationsContainer,
)
from as2fm.scxml_converter.scxml_entries.bt_utils import BtPortsHandler, is_bt_event
from as2fm.scxml_converter.scxml_entries.scxml_executable_entries import (
    execution_body_from_xml,
    instantiate_exec_body_bt_events,
    set_execution_body_callback_type,
    valid_execution_body,
    valid_execution_body_entry_types,
)
from as2fm.scxml_converter.scxml_entries.utils import (
    CallbackType,
    get_plain_expression,
    is_non_empty_string,
)


class ScxmlTransition(ScxmlBase):
    """This class represents a single scxml state."""

    @staticmethod
    def get_tag_name() -> str:
        return "transition"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlTransition":
        """Create a ScxmlTransition object from an XML tree."""
        assert (
            xml_tree.tag == ScxmlTransition.get_tag_name()
        ), f"Error: SCXML transition: XML root tag name is not {ScxmlTransition.get_tag_name()}."
        target = xml_tree.get("target")
        assert target is not None, "Error: SCXML transition: target attribute not found."
        events_str = xml_tree.get("event")
        events = events_str.split(" ") if events_str is not None else []
        condition = xml_tree.get("cond")
        exec_body = execution_body_from_xml(xml_tree)
        exec_body = exec_body if exec_body is not None else None
        return ScxmlTransition(target, events, condition, exec_body)

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
        if events is None:
            events = []
        if body is None:
            body = []
        assert (
            isinstance(target, str) and len(target) > 0
        ), "Error SCXML transition: target must be a non-empty string."
        assert isinstance(events, list) and all(
            (isinstance(ev, str) and len(ev) > 0) for ev in events
        ), f"Error SCXML transition: events must be a list of filled strings. Found {events}."
        assert condition is None or (
            isinstance(condition, str) and len(condition) > 0
        ), "Error SCXML transition: condition must be a non-empty string."
        assert valid_execution_body_entry_types(
            body
        ), "Error SCXML transition: invalid body provided."
        self._target: str = target
        self._body: ScxmlExecutionBody = body
        self._events: List[str] = events
        self._condition = condition

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

    def instantiate_bt_events(
        self, instance_id: int, children_ids: List[int]
    ) -> List["ScxmlTransition"]:
        """Instantiate the BT events of this transition."""
        # Old handling of BT events is deprecated: remove this if block after support removed
        from as2fm.scxml_converter.scxml_entries.scxml_bt_ticks import BtTick

        # Make sure to replace received events only for ScxmlTransition objects.
        if type(self) is ScxmlTransition:
            for event_str in self._events:
                # Those are expected to be only ticks
                if is_bt_event(event_str):
                    warnings.warn(
                        "Deprecation warning: BT events should not be found in SCXML transitions. "
                        "Use the 'bt_tick' ROS-scxml tag instead.",
                        DeprecationWarning,
                    )
                    assert (
                        len(self._events) == 1 and event_str == "bt_tick"
                    ), f"Unexpected BT event '{event_str}' in SCXML transition."
                    return BtTick(self._target, self._condition, self._body).instantiate_bt_events(
                        instance_id, children_ids
                    )
        # The body of a transition needs to be replaced on derived classes, too
        instantiate_exec_body_bt_events(self._body, instance_id, children_ids)
        return [self]

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

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> "ScxmlTransition":
        assert isinstance(
            ros_declarations, ScxmlRosDeclarationsContainer
        ), "Error: SCXML transition: invalid ROS declarations container."
        assert self.check_valid_ros_instantiations(
            ros_declarations
        ), "Error: SCXML transition: invalid ROS instantiations in transition body."
        new_body = None
        set_execution_body_callback_type(self._body, CallbackType.TRANSITION)
        if self._body is not None:
            new_body = [entry.as_plain_scxml(ros_declarations) for entry in self._body]
        if self._condition is not None:
            self._condition = get_plain_expression(self._condition, CallbackType.TRANSITION)
        return ScxmlTransition(self._target, self._events, self._condition, new_body)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid transition."
        xml_transition = ET.Element(ScxmlTransition.get_tag_name(), {"target": self._target})
        if len(self._events) > 0:
            xml_transition.set("event", " ".join(self._events))
        if self._condition is not None:
            xml_transition.set("cond", self._condition)
        if self._body is not None:
            for executable_entry in self._body:
                xml_transition.append(executable_entry.as_xml())
        return xml_transition
