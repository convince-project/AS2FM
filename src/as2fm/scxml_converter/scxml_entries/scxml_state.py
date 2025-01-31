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

from typing import List, Sequence, Union

from lxml import etree as ET

from as2fm.as2fm_common.common import is_comment
from as2fm.scxml_converter.scxml_entries import (
    ScxmlBase,
    ScxmlExecutableEntry,
    ScxmlExecutionBody,
    ScxmlRosDeclarationsContainer,
    ScxmlSend,
    ScxmlTransition,
)
from as2fm.scxml_converter.scxml_entries.bt_utils import (
    BT_BLACKBOARD_GET,
    BT_BLACKBOARD_REQUEST,
    BtPortsHandler,
)
from as2fm.scxml_converter.scxml_entries.scxml_executable_entries import (
    as_plain_execution_body,
    execution_body_from_xml,
    has_bt_blackboard_input,
    instantiate_exec_body_bt_events,
    is_plain_execution_body,
    set_execution_body_callback_type,
    valid_execution_body,
)
from as2fm.scxml_converter.scxml_entries.utils import CallbackType


class ScxmlState(ScxmlBase):
    """This class represents a single scxml state."""

    @staticmethod
    def get_tag_name() -> str:
        return "state"

    @staticmethod
    def _transitions_from_xml(state_id: str, xml_tree: ET.Element) -> List[ScxmlTransition]:
        from as2fm.scxml_converter.scxml_entries.scxml_ros_base import RosCallback

        transitions: List[ScxmlTransition] = []
        tag_to_cls = {
            cls.get_tag_name(): cls
            for cls in ScxmlTransition.__subclasses__()
            if cls != RosCallback
        }
        tag_to_cls.update({cls.get_tag_name(): cls for cls in RosCallback.__subclasses__()})
        tag_to_cls.update({ScxmlTransition.get_tag_name(): ScxmlTransition})
        for child in xml_tree:
            if is_comment(child):
                continue
            elif child.tag in tag_to_cls:
                transitions.append(tag_to_cls[child.tag].from_xml_tree(child))
            else:
                assert child.tag in (
                    "onentry",
                    "onexit",
                ), f"Error: SCXML state {state_id}: unexpected tag {child.tag}."
        return transitions

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "ScxmlState":
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
            for exec_entry in execution_body_from_xml(on_entry[0]):
                scxml_state.append_on_entry(exec_entry)
        if len(on_exit) > 0:
            for exec_entry in execution_body_from_xml(on_exit[0]):
                scxml_state.append_on_exit(exec_entry)
        # Get the transitions in the state body
        for body_entry in ScxmlState._transitions_from_xml(id_, xml_tree):
            scxml_state.add_transition(body_entry)
        return scxml_state

    def __init__(
        self,
        state_id: str,
        *,
        on_entry: ScxmlExecutionBody = None,
        on_exit: ScxmlExecutionBody = None,
        body: List[ScxmlTransition] = None,
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

    def set_thread_id(self, thread_idx: int):
        """Assign the thread ID to the thread-specific transitions in the body."""
        for entry in self._on_entry + self._on_exit + self._body:
            # Assign the thread only to the entries supporting it
            if hasattr(entry, "set_thread_id"):
                entry.set_thread_id(thread_idx)

    def _generate_blackboard_retrieval(
        self, bt_ports_handler: BtPortsHandler
    ) -> List["ScxmlState"]:
        generated_states: List[ScxmlState] = [self]
        assert not has_bt_blackboard_input(self._on_entry, bt_ports_handler), (
            f"Error: SCXML state {self.get_id()}: reading blackboard variables from onentry. "
            "This isn't yet supported."
        )
        assert not has_bt_blackboard_input(self._on_exit, bt_ports_handler), (
            f"Error: SCXML state {self.get_id()}: reading blackboard variables from onexit. "
            "This isn't yet supported."
        )
        for transition_idx in range(len(self.body)):
            if self._body[transition_idx].has_bt_blackboard_input(bt_ports_handler):
                # For now, make sure this is a transitions with a single target
                assert (
                    len(self._body[transition_idx].get_targets()) == 1
                ), "Blackboard support is not yet compatible with probabilistic transitions."
                # Prepare the new state using the received BT info
                states_count = len(generated_states)
                new_state_id = (
                    f"{self.get_id()}_{self._body[transition_idx].get_tag_name()}_{states_count}"
                )
                new_state = ScxmlState(new_state_id)
                blackboard_transition = ScxmlTransition(
                    self._body[transition_idx].get_targets(), [BT_BLACKBOARD_GET]
                )
                new_state.add_transition(blackboard_transition)
                generated_states.append(new_state)
                # Set the new target and body to the original transition
                trans_events = self._body[transition_idx].get_events()
                trans_cond = self._body[transition_idx].get_condition()
                self._body[transition_idx] = ScxmlTransition.make_single_target_transition(
                    new_state_id, trans_events, trans_cond, [ScxmlSend(BT_BLACKBOARD_REQUEST)]
                )
        return generated_states

    def _substitute_bt_events_and_ports(
        self, instance_id: int, children_ids: List[int], bt_ports_handler: BtPortsHandler
    ) -> None:
        instantiated_transitions: List[ScxmlTransition] = []
        for transition in self._body:
            new_transitions = transition.instantiate_bt_events(instance_id, children_ids)
            assert isinstance(new_transitions, list) and all(
                isinstance(t, ScxmlTransition) for t in new_transitions
            ), f"Error: SCXML state {self._id}: found invalid transition in state body."
            instantiated_transitions.extend(new_transitions)
        self._body = instantiated_transitions
        instantiate_exec_body_bt_events(self._on_entry, instance_id, children_ids)
        instantiate_exec_body_bt_events(self._on_exit, instance_id, children_ids)
        self._update_bt_ports_values(bt_ports_handler)

    def _update_bt_ports_values(self, bt_ports_handler: BtPortsHandler) -> None:
        """Update the values of potential entries making use of BT ports."""
        for transition in self._body:
            transition.update_bt_ports_values(bt_ports_handler)
        for entry in self._on_entry:
            entry.update_bt_ports_values(bt_ports_handler)
        for entry in self._on_exit:
            entry.update_bt_ports_values(bt_ports_handler)

    def instantiate_bt_events(
        self, instance_id: int, children_ids: List[int], bt_ports_handler: BtPortsHandler
    ) -> List["ScxmlState"]:
        """Instantiate the BT events in all entries belonging to a state."""
        generated_states = self._generate_blackboard_retrieval(bt_ports_handler)
        for state in generated_states:
            state._substitute_bt_events_and_ports(instance_id, children_ids, bt_ports_handler)
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

    def check_valid_ros_instantiations(
        self, ros_declarations: ScxmlRosDeclarationsContainer
    ) -> bool:
        """Check if the ros instantiations have been declared."""
        valid_entry = ScxmlState._check_valid_ros_instantiations(self._on_entry, ros_declarations)
        valid_exit = ScxmlState._check_valid_ros_instantiations(self._on_exit, ros_declarations)
        valid_body = ScxmlState._check_valid_ros_instantiations(self._body, ros_declarations)
        if not valid_entry:
            print(f"Error: SCXML state {self._id}: onentry has invalid ROS instantiations.")
        if not valid_exit:
            print(f"Error: SCXML state {self._id}: onexit has invalid ROS instantiations.")
        if not valid_body:
            print(f"Error: SCXML state {self._id}: found invalid transition in state body.")
        return valid_entry and valid_exit and valid_body

    @staticmethod
    def _check_valid_ros_instantiations(
        body: Sequence[Union[ScxmlExecutableEntry, ScxmlTransition]],
        ros_declarations: ScxmlRosDeclarationsContainer,
    ) -> bool:
        """Check if the ros instantiations have been declared in the body."""
        return len(body) == 0 or all(
            entry.check_valid_ros_instantiations(ros_declarations) for entry in body
        )

    def is_plain_scxml(self) -> bool:
        """Check if all SCXML entries in the state are plain scxml."""
        plain_entry = is_plain_execution_body(self._on_entry)
        plain_exit = is_plain_execution_body(self._on_exit)
        plain_body = all(transition.is_plain_scxml() for transition in self._body)
        return plain_entry and plain_exit and plain_body

    def as_plain_scxml(self, ros_declarations: ScxmlRosDeclarationsContainer) -> "ScxmlState":
        """Convert the ROS-specific entries to be plain SCXML"""
        set_execution_body_callback_type(self._on_entry, CallbackType.STATE)
        set_execution_body_callback_type(self._on_exit, CallbackType.STATE)
        plain_entry = as_plain_execution_body(self._on_entry, ros_declarations)
        plain_exit = as_plain_execution_body(self._on_exit, ros_declarations)
        plain_body: List[ScxmlTransition] = []
        for entry in self._body:
            plain_entries = entry.as_plain_scxml(ros_declarations)
            if isinstance(plain_entries, ScxmlTransition):
                plain_body.append(plain_entries)
            elif isinstance(plain_entries, list) and all(
                isinstance(e, ScxmlTransition) for e in plain_entries
            ):
                # Some special entries return multiple transitions
                plain_body.extend(plain_entries)
            else:
                raise ValueError(
                    f"Error: SCXML state {self._id}: found invalid transition in "
                    "state body after conversion to plain SCXML."
                )
        return ScxmlState(self._id, on_entry=plain_entry, on_exit=plain_exit, body=plain_body)

    def as_xml(self) -> ET.Element:
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
