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

from typing import Dict, List, get_args

from as2fm.as2fm_common.common import is_array_type
from as2fm.jani_generator.jani_entries import JaniModel
from as2fm.jani_generator.jani_entries.jani_automaton import JaniAutomaton
from as2fm.jani_generator.jani_entries.jani_composition import JaniComposition
from as2fm.jani_generator.jani_entries.jani_edge import JaniEdge
from as2fm.jani_generator.jani_entries.jani_expression_generator import \
    array_create_operator
from as2fm.jani_generator.ros_helpers.ros_timer import (
    GLOBAL_TIMER_NAME, GLOBAL_TIMER_TICK_ACTION, ROS_TIMER_RATE_EVENT_PREFIX,
    RosTimer)
from as2fm.jani_generator.scxml_helpers.scxml_event import EventsHolder


def implement_scxml_events_as_jani_syncs(
        events_holder: EventsHolder,
        timers: List[RosTimer],
        max_array_size: int,
        jani_model: JaniModel) -> List[str]:
    """
    Implement the scxml events as jani syncs.

    :param events_holder: The holder of the events.
    :param timers: The timers to add to the jani model.
    :param jani_model: The jani model to add the syncs to.
    :return: The list of events having only senders.
    """
    jc = JaniComposition()
    events_without_receivers = []
    for automaton in jani_model.get_automata():
        jc.add_element(automaton.get_name())
    add_timer_syncs = len(timers) > 0
    if add_timer_syncs:
        # Collect all event automatons that take priority over all kinds of timer actions
        timer_enable_syncs: Dict[str, str] = {}
    for event_name, event in events_holder.get_events().items():
        # Sender and receiver event names
        event_name_on_send = f"{event_name}_on_send"
        event_name_on_receive = f"{event_name}_on_receive"
        # Special case handling for events that must be skipped, e.g. BT responses and timers
        if event.must_be_skipped_in_jani_conversion():
            # if this is a bt or an action event, we have to get rid of all edges receiving it
            if event.is_bt_response_event() or event.is_optional_action_event():
                jani_model.remove_edges_with_action(event_name_on_receive)
            continue
        assert event.has_senders(), f"Event {event_name} must have at least one sender"
        # Prepare the automaton handling the event
        event_automaton = JaniAutomaton()
        event_automaton.set_name(event_name)
        event_automaton.add_location("waiting", is_initial=True)
        if add_timer_syncs:
            # Additional self-loop in the waiting state, allowing the global timer to tick
            # only if all events have been processed
            event_automaton.add_edge(JaniEdge({
                "location": "waiting",
                "destinations": [{
                    "location": "waiting",
                    "probability": {"exp": 1.0},
                    "assignments": []
                }],
                "action": "global_timer_enable"
            }))
            timer_enable_syncs.update({event_name: "global_timer_enable"})
        # Add the event handling automaton
        jc.add_element(event_name)
        if event.has_receivers():
            # Add a "received" state and related transitions
            event_automaton.add_location("received")
            event_automaton.add_edge(JaniEdge({
                "location": "waiting",
                "destinations": [{
                    "location": "received",
                    "probability": {"exp": 1.0},
                    "assignments": []
                }],
                "action": event_name_on_send
            }))
            event_automaton.add_edge(JaniEdge({
                "location": "received",
                "destinations": [{
                    "location": "waiting",
                    "probability": {"exp": 1.0},
                    "assignments": []
                }],
                "action": event_name_on_receive
            }))
        else:
            # Store the events without receivers
            events_without_receivers.append(event_name)
            # If there are no receivers, we add a self-loop
            event_automaton.add_edge(JaniEdge({
                "location": "waiting",
                "destinations": [{
                    "location": "waiting",
                    "probability": {"exp": 1.0},
                    "assignments": []
                }],
                "action": event_name_on_send
            }))
        jani_model.add_jani_automaton(event_automaton)
        # Verify and prepare the receiver syncs
        if event.has_receivers():
            receivers_syncs = {event_name: event_name_on_receive}
            for receiver in event.get_receivers():
                action_name = receiver.edge_action_name
                assert action_name == event_name_on_receive, \
                    f"Action name {action_name} must be {event_name_on_receive}."
                receivers_syncs.update({receiver.automaton_name: action_name})
            jc.add_sync(event_name_on_receive, receivers_syncs)
        # Verify and prepare the sender syncs
        for sender in event.get_senders():
            action_name = sender.edge_action_name
            assert action_name == event_name_on_send, \
                f"Action name {action_name} must be {event_name_on_send}."
            senders_syncs = {
                event_name: action_name,
                sender.automaton_name: action_name}
            jc.add_sync(action_name, senders_syncs)
        # Add the global data, if needed
        for p_name, p_type in event.get_data_structure().items():
            init_value = None
            is_array = is_array_type(p_type)
            if is_array:
                ar_type = get_args(p_type)[0]
                init_value = array_create_operator("__array_iterator", max_array_size, ar_type(0))
            # TODO: Dots are likely to create problems in the future. Consider replacing them
            jani_model.add_variable(
                variable_name=f"{event_name}.{p_name}",
                variable_type=p_type,
                variable_init_expression=init_value
            )
            # In case of arrays, add a variable representing the array size, too
            if is_array:
                jani_model.add_variable(
                    variable_name=f"{event_name}.{p_name}.length",
                    variable_type=int,
                    variable_init_expression=0
                )
        # For each event, we add an extra boolean flag for data validity
        jani_model.add_variable(
            variable_name=f"{event_name}.valid",
            variable_type=bool,
            variable_init_expression=False
        )
    # Add syncs for global timer
    if add_timer_syncs:
        # Add sync action for global timer tick
        jc.add_sync(GLOBAL_TIMER_TICK_ACTION,
                    timer_enable_syncs | {GLOBAL_TIMER_NAME: GLOBAL_TIMER_TICK_ACTION})
    # Add syncs for rate timers
    for timer in timers:
        name = timer.name
        event_name = f"{ROS_TIMER_RATE_EVENT_PREFIX}{name}"
        try:
            event = events_holder.get_event(event_name)
        except KeyError as e:
            raise RuntimeError(
                f"Was expecting an event for timer {name}, with name "
                f"{ROS_TIMER_RATE_EVENT_PREFIX}{name}.") from e
        action_name_receiver = f"{event_name}_on_receive"
        automaton_name = event.get_receivers()[0].automaton_name
        timer_trigger_syncs = {
            GLOBAL_TIMER_NAME: action_name_receiver,
            automaton_name: action_name_receiver
            }
        # Make sure that all other events are processed before starting the timer callback
        timer_trigger_syncs.update(timer_enable_syncs)
        jc.add_sync(action_name_receiver, timer_trigger_syncs)
    jani_model.add_system_sync(jc)
    return events_without_receivers
