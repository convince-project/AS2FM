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
Module to process events from scxml and implement them as syncs between jani automata.
"""

from typing import Dict, List, MutableSequence, Optional, Tuple

from moco.moco_common.array_type import ArrayInfo, is_array_type
from moco.roaml_generator.jani_entries import (
    JaniAutomaton,
    JaniComposition,
    JaniEdge,
    JaniModel,
    JaniVariable,
)
from moco.roaml_generator.jani_entries.jani_expression_generator import array_create_operator
from moco.roaml_generator.ros_helpers.ros_timer import (
    GLOBAL_TIMER_AUTOMATON,
    GLOBAL_TIMER_TICK_ACTION,
    GLOBAL_TIMER_TICK_EVENT,
    ROS_TIMER_RATE_EVENT_PREFIX,
)
from moco.roaml_generator.scxml_helpers.scxml_event import Event, EventsHolder
from moco.roaml_generator.scxml_helpers.scxml_expression import get_array_length_var_name
from moco.roaml_converter.data_types.type_utils import MEMBER_ACCESS_SUBSTITUTION

JANI_TIMER_ENABLE_ACTION = "global_timer_enable"


def _generate_event_action_names(event_obj: Event) -> Tuple[str, str]:
    """Get the action names related to sending and receiving the event."""
    return (f"{event_obj.name}_on_send", f"{event_obj.name}_on_receive")


def _generate_event_edge(source_state: str, target_state: str, action_name: str) -> JaniEdge:
    """Generate a generic edge with one destination and no assignments."""
    return JaniEdge(
        {
            "location": source_state,
            "destinations": [
                {"location": target_state, "probability": {"exp": 1.0}, "assignments": []}
            ],
            "action": action_name,
        }
    )


def _generate_event_automaton(event_obj: Event, add_timer_sync: bool) -> Optional[JaniAutomaton]:
    """Generate a JaniAutomaton out of a (non-timer) event."""
    assert not event_obj.is_timer_event(), "This function cannot be used on timer events."
    if event_obj.must_be_skipped_in_jani_conversion():
        return None
    event_send_action, event_recv_action = _generate_event_action_names(event_obj)
    waiting_str = "waiting"
    received_str = "received"
    assert event_obj.has_senders(), f"Event {event_obj.name} must have at least one sender"
    event_automaton = JaniAutomaton()
    event_automaton.set_name(event_obj.name)
    event_automaton.add_location(waiting_str, is_initial=True)
    if event_obj.has_receivers():
        event_automaton.add_location(received_str)
        event_automaton.add_edge(_generate_event_edge(waiting_str, received_str, event_send_action))
        event_automaton.add_edge(_generate_event_edge(received_str, waiting_str, event_recv_action))
        if add_timer_sync:
            # Additional self-loop in the waiting state
            # used to enable the global timer to tick only if all other events have been processed
            event_automaton.add_edge(
                _generate_event_edge(waiting_str, waiting_str, JANI_TIMER_ENABLE_ACTION)
            )
    else:
        # In this case, we have only a self-loop since no receive sync is needed
        event_automaton.add_edge(_generate_event_edge(waiting_str, waiting_str, event_send_action))
    return event_automaton


def _generate_event_variables(event_obj: Event, max_array_size: int) -> List[JaniVariable]:
    """Generate the variables required for handling a provided event."""
    jani_vars: List[JaniVariable] = []
    jani_vars.append(JaniVariable(f"{event_obj.name}.valid", bool, False))
    for param_name, param_info in event_obj.get_data_structure().items():
        var_name = f"{event_obj.name}{MEMBER_ACCESS_SUBSTITUTION}{param_name}"
        if is_array_type(param_info.p_type):
            ar_type = param_info.p_array_type
            assert ar_type is not None, "None array type found: this is unexpected."
            array_dims = param_info.p_dimensions
            array_info = ArrayInfo(ar_type, array_dims, [max_array_size] * array_dims)
            array_init = array_create_operator(array_info)
            jani_vars.append(
                JaniVariable(var_name, param_info.p_type, array_init, False, array_info)
            )
            for dim in range(array_dims):
                len_var_name = get_array_length_var_name(var_name, dim + 1)
                if dim == 0:
                    jani_vars.append(JaniVariable(len_var_name, int, 0))
                else:
                    len_array_info = ArrayInfo(int, dim, [max_array_size] * dim)
                    len_array_init = array_create_operator(len_array_info)
                    jani_vars.append(
                        JaniVariable(
                            len_var_name, MutableSequence, len_array_init, False, len_array_info
                        )
                    )
        else:
            jani_vars.append(JaniVariable(var_name, param_info.p_type))
    return jani_vars


def _preprocess_global_timer_automaton(timer_automaton: JaniAutomaton):
    """
    Modify the global timer automaton to meet different assumptions.

    - We expect no assignments to timer_name.valid variables.
    - Similarly, no assignments for the {GLOBAL_TIMER_TICK_EVENT}.valid variable.
    - The {GLOBAL_TIMER_TICK_EVENT}_on_send action is treated as a non-sync action.
    - The {GLOBAL_TIMER_TICK_EVENT}_on_receive action the global timer step, and is renamed.
    """
    global_timer_edges = timer_automaton.get_edges()
    for jani_edge in global_timer_edges:
        action_name = jani_edge.get_action()
        if action_name is not None:
            if action_name.startswith(ROS_TIMER_RATE_EVENT_PREFIX):
                assert (
                    len(jani_edge.destinations) == 1
                ), f"Unexpected n. of destination for timer edge '{action_name}'"
                assert (
                    len(jani_edge.destinations[0]["assignments"]) == 1
                ), f"Unexpected n. of assignments for timer edge '{action_name}'"
                # Get rid of the assignment
                jani_edge.destinations[0]["assignments"] = []
            elif action_name == f"{GLOBAL_TIMER_TICK_EVENT}_on_receive":
                jani_edge.set_action(GLOBAL_TIMER_TICK_ACTION)
            elif action_name == f"{GLOBAL_TIMER_TICK_EVENT}_on_send":
                jani_edge.set_action(GLOBAL_TIMER_TICK_EVENT)
                jani_edge.destinations[0]["assignments"] = []

