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

from typing import Dict, List, Optional, Tuple, Type

from lxml import etree as ET
from lxml.etree import _Element as XmlElement
from typing_extensions import Self

from as2fm.as2fm_common.common import EPSILON, is_comment
from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import (
    ScxmlBase,
    ScxmlExecutionBody,
    ScxmlTransitionTarget,
)
from as2fm.scxml_converter.scxml_entries.scxml_executable_entry import (
    EventsToAutomata,
    ScxmlExecutableEntry,
    add_targets_to_scxml_sends,
    execution_body_from_xml,
    get_config_entries_request_receive_events,
)
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    CallbackType,
    convert_expression_with_string_literals,
    get_plain_expression,
    is_non_empty_string,
)
from as2fm.scxml_converter.scxml_entries.xml_utils import get_xml_attribute


class ScxmlTransition(ScxmlBase):
    """This class represents a scxml transition."""

    @staticmethod
    def get_tag_name() -> str:
        return "transition"

    @staticmethod
    def contains_transition_target(xml_tree: XmlElement) -> bool:
        """Check if the children of the ScxmlTransition contain ScxmlTransitionTarget tags."""
        targets_found = False
        for entry in xml_tree:
            if is_comment(entry):
                pass  # Do nothing
            elif entry.tag == ScxmlTransitionTarget.get_tag_name():
                targets_found = True
            else:
                return False  # Found an entry that isn't a target: return
        return targets_found

    @classmethod
    def load_transition_targets_from_xml(
        cls: Type["ScxmlTransition"],
        xml_tree: XmlElement,
        custom_data_types: Dict[str, StructDefinition],
    ) -> List[ScxmlTransitionTarget]:
        """Loads all transition targets contained in the transition-like tags."""
        target = get_xml_attribute(cls, xml_tree, "target", undefined_allowed=True)
        has_targets_children = cls.contains_transition_target(xml_tree)
        assert (target is not None) != has_targets_children, (
            f"Error: SCXML {cls.get_tag_name()}: target must can be either "
            "an attribute or a child."
        )
        target_children: List[ScxmlTransitionTarget] = []
        if has_targets_children:
            target_children.extend(
                [
                    ScxmlTransitionTarget.from_xml_tree(entry, custom_data_types)
                    for entry in xml_tree
                    if not is_comment(entry)
                ]
            )
        else:
            assert target is not None and is_non_empty_string(cls, "target", target)  # MyPy check
            target_children.append(
                ScxmlTransitionTarget(
                    target, body=execution_body_from_xml(xml_tree, custom_data_types)
                )
            )
        return target_children

    @classmethod
    def from_xml_tree_impl(
        cls, xml_tree: XmlElement, custom_data_types: Dict[str, StructDefinition]
    ) -> "ScxmlTransition":
        """Create a ScxmlTransition object from an XML tree."""
        assert (
            xml_tree.tag == ScxmlTransition.get_tag_name()
        ), f"Error: SCXML transition: XML root tag name is not {ScxmlTransition.get_tag_name()}."
        events_str = get_xml_attribute(ScxmlTransition, xml_tree, "event", undefined_allowed=True)
        events = events_str.split(" ") if events_str is not None else []
        condition = get_xml_attribute(ScxmlTransition, xml_tree, "cond", undefined_allowed=True)
        transition_targets = ScxmlTransition.load_transition_targets_from_xml(
            xml_tree, custom_data_types
        )
        return ScxmlTransition(transition_targets, events, condition)

    @classmethod
    def make_single_target_transition(
        cls: Type[Self],
        target: str,
        events: Optional[List[str]] = None,
        condition: Optional[str] = None,
        body: Optional[ScxmlExecutionBody] = None,
    ) -> Self:
        """
        Generate a "traditional" transition with exactly one target.

        :param target: The state transition goes to. Required (unlike in SCXML specifications)
        :param events: The events that trigger this transition.
        :param condition: The condition guard to enable/disable the transition
        :param body: Content that is executed when the transition happens
        """
        targets = [ScxmlTransitionTarget(target, None, body)]
        return cls(targets, events, condition)

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

    def get_config_request_receive_events(self) -> List[Tuple[str, str]]:
        """Get all events for requesting and receiving the updated configurable values."""
        all_events: List[Tuple[str, str]] = []
        for target in self._targets:
            temp_events = get_config_entries_request_receive_events(target.get_body())
            for ev in temp_events:
                if ev not in all_events:
                    all_events.append(ev)
        return all_events

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
            # Skip validity check, since we need to substitute BT ports values first
            single_prob = new_targets[0].get_probability()
            assert single_prob is None or single_prob == 1.0
            self._targets.append(new_targets[0])
        else:
            prob_sum = 0.0
            for target in new_targets:
                # Skip validity check, since we need to substitute BT ports values first
                if target.get_probability() is None:  # This is the last target entry
                    target.set_probability(1.0 - prob_sum)
                self._targets.append(target)
                target_probability = target.get_probability()
                assert target_probability is not None  # MyPy check
                prob_sum += target_probability
            assert (
                abs(prob_sum - 1.0) < EPSILON
            ), f"The sum of probabilities is {prob_sum}, must be 1.0."

    def get_events(self) -> List[str]:
        """Return the events that trigger this transition (if any)."""
        return self._events

    def get_condition(self) -> Optional[str]:
        """Return the condition required to execute this transition (if any)."""
        return self._condition

    def add_event(self, event: str):
        self._events.append(event)

    def append_body_executable_entry(self, exec_entry: ScxmlExecutableEntry):
        """Append a executable body entry if this has only one target.

        If this transition has not exactly one target, this will raise an AssertionError."""
        assert len(self._targets) == 1, (
            "Error SCXML transition: Can only assign executable content to transition if there is"
            + f" exactly one target. But there are {len(self._targets)}."
        )
        self._targets[0].append_body_executable_entry(exec_entry)

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
        if valid_targets and len(self._targets) > 1 and self._condition is not None:
            print(
                "Error: SCXML transition: No support for conditional transitions "
                "with multiple targets."
            )
            valid_targets = False
        return valid_targets and valid_events and valid_condition

    def update_exec_body_configurable_values(self, ascxml_declarations: List[AscxmlDeclaration]):
        for target in self._targets:
            target.update_exec_body_configurable_values(ascxml_declarations)

    def is_plain_scxml(self) -> bool:
        """Check if the transition is a plain scxml entry and contains only plain scxml."""
        return type(self) is ScxmlTransition and all(
            target.is_plain_scxml() for target in self._targets
        )

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        plain_targets: List[ScxmlTransitionTarget] = []
        for target in self._targets:
            target.set_callback_type(CallbackType.TRANSITION)
            plain_targets.extend(
                target.as_plain_scxml(struct_declarations, ascxml_declarations, **kwargs)
            )
        if self._condition is not None:
            self._condition = get_plain_expression(
                self._condition, CallbackType.TRANSITION, struct_declarations
            )
        return [ScxmlTransition(plain_targets, self._events, self._condition)]

    def add_targets_to_scxml_sends(self, events_to_targets: EventsToAutomata):
        """
        For each "ScxmlSend" entry in the transition body, add the automata receiving the event.
        """
        for transition_target in self._targets:
            transition_target.set_body(
                add_targets_to_scxml_sends(transition_target.get_body(), events_to_targets)
            )

    def replace_strings_types_with_integer_arrays(self) -> None:
        """
        Replace the string literals in the transition condition and the different targets.
        """
        if self._condition is not None:
            self._condition = convert_expression_with_string_literals(
                self._condition, self.get_xml_origin()
            )
        for target in self._targets:
            target.replace_strings_types_with_integer_arrays()

    def as_xml(self) -> XmlElement:
        assert self.check_validity(), "SCXML: found invalid transition."
        xml_transition = ET.Element(self.get_tag_name())
        if len(self._events) > 0:
            xml_transition.set("event", " ".join(self._events))
        if self._condition is not None:
            xml_transition.set("cond", self._condition)
        if len(self._targets) > 1 or self._targets[0].get_probability() is not None:
            # Using the custom probability functionalities: add the target children
            for target in self._targets:
                xml_transition.append(target.as_xml())
        else:
            # Only one target and no probability used: use the standard format
            xml_transition.set("target", self._targets[0].get_target_id())
            for executable_entry in self._targets[0].get_body():
                xml_transition.append(executable_entry.as_xml())
        return xml_transition
