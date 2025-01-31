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

from typing import List, Optional

from lxml import etree as ET

from as2fm.as2fm_common.common import EPSILON
from as2fm.scxml_converter.scxml_entries import (
    ScxmlBase,
    ScxmlExecutionBody,
    ScxmlRosDeclarationsContainer,
    ScxmlTransitionTarget,
)
from as2fm.scxml_converter.scxml_entries.bt_utils import BtPortsHandler, is_bt_event
from as2fm.scxml_converter.scxml_entries.scxml_executable_entries import execution_body_from_xml
from as2fm.scxml_converter.scxml_entries.utils import (
    CallbackType,
    get_plain_expression,
    is_non_empty_string,
)


class ScxmlTransition(ScxmlBase):
    """This class represents a scxml transition."""

    @staticmethod
    def get_tag_name() -> str:
        return "transition"

    @staticmethod
    def contains_transition_target(xml_tree: ET.Element) -> bool:
        """Check if the children of the ScxmlTransition contain ScxmlTransitionTarget tags."""
        return len(xml_tree) > 0 and all(
            entry.tag == ScxmlTransitionTarget.get_tag_name() for entry in xml_tree
        )

    # @staticmethod
    # def _contains_executable_content(xml_tree: ET.Element) -> bool:
    #     """Check if the children of the ScxmlTransition contain executable content."""
    #     return all(valid_execution_body([entry]) for entry in xml_tree)

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlTransition":
        """Create a ScxmlTransition object from an XML tree."""
        assert (
            xml_tree.tag == ScxmlTransition.get_tag_name()
        ), f"Error: SCXML transition: XML root tag name is not {ScxmlTransition.get_tag_name()}."
        target = xml_tree.get("target")
        events_str = xml_tree.get("event")
        events = events_str.split(" ") if events_str is not None else []
        condition = xml_tree.get("cond")

        # Differentiate between children being targets or being executable content
        contains_stt: bool = ScxmlTransition.contains_transition_target(xml_tree)
        # contains_ec: bool = ScxmlTransition._contains_executable_content(xml_tree)
        # Make sure that only one of the two holds true (XOR)
        if contains_stt:
            assert target is None, (
                "Error: SCXML transition: Can have either target attribute or ",
                "(probabilistic) transition targets",
            )
            if len(events) > 0:
                raise NotImplementedError(
                    "events are not supported for probabilistic transition targets right now."
                )  # TODO: Consider enabling this
            if condition is not None:
                raise NotImplementedError(
                    "conditions are not supported for probabilistic transition targets right now."
                )  # TODO: Consider enabling this
            targets = [ScxmlTransitionTarget.from_xml_tree(entry) for entry in xml_tree]
            return ScxmlTransition(targets, events, condition)
        assert target is not None, "Error: SCXML transition: target attribute not found."
        return ScxmlTransition.make_single_target_transition(
            target, events, condition, execution_body_from_xml(xml_tree)
        )

    @staticmethod
    def make_single_target_transition(
        target: str,
        events: Optional[List[str]] = None,
        condition: Optional[str] = None,
        body: Optional[ScxmlExecutionBody] = None,
    ):
        """
        Generate a "traditional" transition with exactly one target.

        :param target: The state transition goes to. Required (unlike in SCXML specifications)
        :param events: The events that trigger this transition.
        :param condition: The condition guard to enable/disable the transition
        :param body: Content that is executed when the transition happens
        """
        targets = [ScxmlTransitionTarget(target, None, body)]
        return ScxmlTransition(targets, events, condition)

    def __init__(
        self,
        targets: List[ScxmlTransitionTarget],
        events: Optional[List[str]] = None,
        condition: Optional[str] = None,
    ):
        """
        Generate a transition with multiple targets.

        :param targets: The various targets that can be reached from this state. At least one!
        :param events: The events that trigger this transition.
        :param condition: The condition guard to enable/disable the transition
        """
        if events is None:
            events = []
        assert isinstance(targets, list) and all(
            isinstance(target, ScxmlTransitionTarget) for target in targets
        ), "Error SCXML transition: no target provided or unexpected type."
        assert condition is None or (
            isinstance(condition, str) and len(condition) > 0
        ), "Error SCXML transition: condition must be a non-empty string."
        self.set_targets(targets)
        self._events: List[str] = events
        self._condition = condition

    def get_targets(self) -> List[ScxmlTransitionTarget]:
        """Return all targets belonging to this transition."""
        return self._targets

    def set_targets(self, new_targets: List[ScxmlTransitionTarget]):
        """
        Set the targets of the transition.

        Additionally, calculates potentially remaining probabilities and checks they sum to one.
        """
        self._targets: List[ScxmlTransitionTarget] = []
        n_targets = len(new_targets)
        assert n_targets > 0, "Error SCXML transition: expected at least one target, found none."
        assert all(
            target.get_probability() is not None for target in new_targets[:-1]
        ), "Error SCXML transition: Only the last target can have no probability."
        if n_targets == 1:
            assert new_targets[0].check_validity()
            single_prob = new_targets[0].get_probability()
            assert single_prob is None or single_prob == 1.0
            self._targets.append(new_targets[0])
        else:
            prob_sum = 0.0
            for target in new_targets:
                assert target.check_validity()
                if target.get_probability() is None:  # This is the last target entry
                    target.set_probability(1.0 - prob_sum)
                self._targets.append(target)
                prob_sum += target.get_probability()
            assert (
                abs(prob_sum - 1.0) < EPSILON
            ), f"The sum of probabilities is {prob_sum}, must be 1.0."

    def get_events(self) -> List[str]:
        """Return the events that trigger this transition (if any)."""
        return self._events

    def get_condition(self) -> Optional[str]:
        """Return the condition required to execute this transition (if any)."""
        return self._condition

    def has_bt_blackboard_input(self, bt_ports_handler: BtPortsHandler):
        """Check if the transition contains references to blackboard inputs."""
        return any(target.has_bt_blackboard_input(bt_ports_handler) for target in self._targets)

    def instantiate_bt_events(
        self, instance_id: int, children_ids: List[int]
    ) -> List["ScxmlTransition"]:
        """Instantiate the BT events of this transition."""
        # Make sure to replace received events only for ScxmlTransition objects.
        if type(self) is ScxmlTransition:
            assert not any(is_bt_event(event) for event in self._events), (
                "Error SCXML transition: BT events should not be found in SCXML transitions.",
                "Use the 'bt_tick' ROS-scxml tag instead.",
            )
        # The body of a transition needs to be replaced on derived classes, too
        for target in self._targets:
            target.instantiate_bt_events(instance_id, children_ids)
        return [self]

    def update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        """Update the values of potential entries making use of BT ports."""
        for target in self._targets:
            target.update_bt_ports_values(bt_ports_handler)

    def add_event(self, event: str):
        self._events.append(event)

    def check_validity(self) -> bool:
        valid_targets = isinstance(self._targets, list) and all(
            (isinstance(t, ScxmlTransitionTarget) and t.check_validity()) for t in self._targets
        )
        valid_condition = self._condition is None or (
            is_non_empty_string(type(self), "condition", self._condition)
        )
        valid_events = self._events is None or (
            isinstance(self._events, list) and all(isinstance(ev, str) for ev in self._events)
        )
        if not valid_targets:
            print("Error: SCXML transition: invalid targets.")
        if not valid_events:
            print("Error: SCXML transition: events are not valid.\nList of events:")
            for event in self._events:
                print(f"\t-'{event}'.")
        return valid_targets and valid_events and valid_condition

    def check_valid_ros_instantiations(
        self, ros_declarations: ScxmlRosDeclarationsContainer
    ) -> bool:
        """Check if the ros instantiations have been declared."""
        # For SCXML transitions, ROS interfaces can be found only in the exec body
        return all(
            target.check_valid_ros_instantiations(ros_declarations) for target in self._targets
        )

    def set_thread_id(self, thread_id: int) -> None:
        """Set the thread ID for the executable entries of this transition."""
        for target in self._targets:
            target.set_thread_id(thread_id)

    def is_plain_scxml(self) -> bool:
        """Check if the transition is a plain scxml entry and contains only plain scxml."""
        return type(self) is ScxmlTransition and all(
            target.is_plain_scxml() for target in self._targets
        )

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> "ScxmlTransition":
        assert isinstance(
            ros_declarations, ScxmlRosDeclarationsContainer
        ), "Error: SCXML transition: invalid ROS declarations container."
        assert self.check_valid_ros_instantiations(
            ros_declarations
        ), "Error: SCXML transition: invalid ROS instantiations in transition body."
        for target in self._targets:
            target.as_plain_scxml(ros_declarations)
        if self._condition is not None:
            self._condition = get_plain_expression(self._condition, CallbackType.TRANSITION)
        return ScxmlTransition(self._targets, self._events, self._condition)

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid transition."
        xml_transition = ET.Element(ScxmlTransition.get_tag_name())
        if len(self._events) > 0:
            xml_transition.set("event", " ".join(self._events))
        if self._condition is not None:
            xml_transition.set("cond", self._condition)
        if len(self._targets) > 1 or self._targets[0].get_probability is not None:
            # Using the custom probability functionalities: add the target children
            for target in self._targets:
                xml_transition.append(target.as_xml())
        else:
            # Only one target and no probability used: use the standard format
            xml_transition.set("target", self._targets[0].get_target_id())
            for executable_entry in self._targets[0].get_body():
                xml_transition.append(executable_entry.as_xml())
        return xml_transition
