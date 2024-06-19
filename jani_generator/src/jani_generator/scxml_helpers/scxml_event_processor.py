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

from typing import List

from jani_generator.jani_entries import JaniModel
from jani_generator.jani_entries.jani_automaton import JaniAutomaton
from jani_generator.jani_entries.jani_composition import JaniComposition
from jani_generator.jani_entries.jani_edge import JaniEdge
from jani_generator.jani_entries.jani_expression import JaniExpression
from jani_generator.jani_entries.jani_variable import JaniVariable
from jani_generator.ros_helpers.ros_timer import RosTimer
from jani_generator.scxml_helpers.scxml_event import (Event, EventSenderType,
                                                      EventsHolder)
from scxml_converter.scxml_converter import ROS_TIMER_RATE_EVENT_PREFIX


def implement_scxml_events_as_jani_syncs(
        events_holder: EventsHolder,
        timers: List[RosTimer],
        jani_model: JaniModel):
    """
    Implement the scxml events as jani syncs.

    :param events_holder: The holder of the events.
    :param jani_model: The jani model to add the syncs to.
    """
    jc = JaniComposition()
    event_action_names = []
    for automaton in jani_model.get_automata():
        jc.add_element(automaton.get_name())
    for event_name, event in events_holder.get_events().items():
        if event.must_be_skipped():
            continue
        event.is_valid()
        event_name_on_send = f"{event_name}_on_send"
        event_name_on_receive = f"{event_name}_on_receive"
        # Expand states if needed
        for sender in event.get_senders():
            automaton = jani_model.get_automaton(sender.automaton_name)
            if sender.type == EventSenderType.ON_ENTRY:
                additional_loc_name = f"{sender.location_name}_on_entry"
                automaton.add_location(additional_loc_name)
                for edge in automaton.get_edges():
                    for dest in edge.destinations:
                        if sender.location_name == dest['location']:
                            dest['location'] = additional_loc_name
                event_edge = JaniEdge({
                    'location': additional_loc_name,
                    'destinations': [{
                        'location': sender.location_name,
                        'probability': {'exp': 1.0},
                        'assignments': sender.get_assignments()
                    }],
                    'action': event_name_on_send
                })
                automaton.add_edge(event_edge)
                # If the original state was initial, now the on_entry state is initial
                if sender.location_name in automaton.get_initial_locations():
                    automaton.make_initial(additional_loc_name)
                    automaton.unset_initial(sender.location_name)
            elif sender.type == EventSenderType.ON_EXIT:
                raise NotImplementedError(
                    "For now, we don't know how to handle on_exit events. " +
                    "Because we would have to check if one of the originally " +
                    "outgoing edges can fire.")
                # TODO: The new edge must only be executed if
                # one of the original outgoing edges is taken
                # Especially if the original edge fires on an event
                # then, where do we consume that?
                # Marco: An alternative way would be to keep the on_exit body
                # aside and append it to all transition bodies,when evaluated
                additional_loc_name = f"{sender.location_name}_on_exit"
                automaton.add_location(additional_loc_name)
                for edge in automaton.get_edges():
                    if sender.location_name == edge.location:
                        edge.location = additional_loc_name
                event_edge = JaniEdge({
                    'location': sender.location_name,
                    'destinations': [{
                        'location': additional_loc_name,
                        'probability': {'exp': 1.0},
                        'assignments': sender.get_assignments()
                    }],
                    'action': event_name_on_send
                })
                automaton.add_edge(event_edge)
            else:
                # sending event from edge
                assert sender.type == EventSenderType.EDGE, \
                    "Sender type must be FROM_EDGE."
                event_name_on_send = sender.edge_action_name
        for receivers in event.get_receivers():
            action_name = receivers.edge_action_name
            assert action_name == event_name_on_receive, \
                f"Action name {action_name} must be {event_name_on_receive}."
        # Collect the event action names
        event_action_names.append(event_name_on_send)
        event_action_names.append(event_name_on_receive)
        # Add event automaton
        event_automaton = JaniAutomaton()
        event_automaton.set_name(event_name)
        event_automaton.add_location("waiting", is_initial=True)
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
        jani_model.add_jani_automaton(event_automaton)
        jc.add_element(event_name)
        # Add the global data, if needed
        for p_name, p_type_str in event.get_data_structure().items():
            jani_model.add_variable(
                variable_name=f"{event_name}.{p_name}",
                variable_type=p_type_str
            )
        # For each event, we add an extra boolean flag for data validity
        jani_model.add_variable(
            variable_name=f"{event_name}.valid",
            variable_type=bool,
            variable_init_expression=False
        )
    # Add the syncs
    syncs = {en: {} for en in event_action_names}
    for automaton in jani_model.get_automata():
        for edge in automaton.get_edges():
            if edge.get_action() in event_action_names:
                syncs[edge.get_action()].update(
                    {automaton.get_name(): edge.get_action()})
    for event_action_name, sync in syncs.items():
        jc.add_sync(event_action_name, sync)
    # Add syncs for rate timers
    for timer in timers:
        name = timer.name
        event_name = f"{ROS_TIMER_RATE_EVENT_PREFIX}{name}"
        try:
            event = events_holder.get_event(event_name)
        except KeyError:
            raise RuntimeError(
                f"Was expecting an event for timer {name}, with name {ROS_TIMER_RATE_EVENT_PREFIX}{name}.")
        action_name_receiver = f"{event_name}_on_receive"
        automaton_name = event.get_receivers()[0].automaton_name
        jc.add_sync(action_name_receiver, {
            automaton_name: action_name_receiver,
            'global_timer': action_name_receiver})
    jani_model.add_system_sync(jc)
