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
Module to hold scxml even information to convert to jani syncs later.
"""

from typing import Dict, List, Optional

from jani_generator.jani_entries.jani_assignment import JaniAssignment
from scxml_converter.scxml_converter import ROS_TIMER_RATE_EVENT_PREFIX


class EventSender:
    def __init__(self, automaton_name: str,
                 edge_action_name: str,
                 assignments: List[JaniAssignment]):
        """
        Initialize the event sender.

        :param automaton_name: The name of the automaton sending the event.
        :param edge_action_name: The name of the entity sending the event.
            (location_name for ON_ENTRY and ON_EXIT, edge_action_name for EDGE)
        """
        self.automaton_name = automaton_name
        self.edge_action_name = edge_action_name
        self._assignments = assignments

    def get_assignments(self) -> List[JaniAssignment]:
        return self._assignments


class EventReceiver:
    def __init__(self, automaton_name: str, location_name: str, edge_action_name: str):
        self.automaton_name = automaton_name
        self.location_name = location_name
        self.edge_action_name = edge_action_name


class Event:
    def __init__(self,
                 name: str,
                 data_struct: Optional[Dict[str, type]] = None):
        self.name = name
        self.data_struct = data_struct
        self.senders: List[EventSender] = []
        self.receivers: List[EventReceiver] = []

    def add_sender_edge(self, automaton_name: str, edge_action_name: str,
                        assignments: List[JaniAssignment]):
        """Add information about the edge sending the event."""
        self.senders.append(EventSender(automaton_name, edge_action_name, assignments))

    def add_receiver(self, automaton_name: str, location_name: str, edge_action_name: str):
        """Add information about the edges triggered by the event."""
        self.receivers.append(EventReceiver(
            automaton_name, location_name, edge_action_name))

    def get_senders(self) -> List[EventSender]:
        """Get the senders of the event."""
        return self.senders

    def get_receivers(self) -> List[EventReceiver]:
        """Get the receivers of the event."""
        return self.receivers

    def get_data_structure(self) -> Dict[str, type]:
        """Get the data structure of the event."""
        return self.data_struct

    def set_data_structure(self, data_struct: Dict[str, type]):
        """Set the data structure of the event."""
        self.data_struct = data_struct

    def is_valid(self):
        """Check if the event is valid."""
        assert len(self.senders) > 0, f"Event {self.name} must have at least one sender."
        assert len(self.receivers) > 0, f"Event {self.name} must have at least one receiver."

    def must_be_skipped_in_jani_conversion(self):
        """Indicate whether this must be considered in the conversion to jani."""
        return (
            self.name.startswith(ROS_TIMER_RATE_EVENT_PREFIX)
            # If the event is a timer event, there is only a receiver
            # It is the edge that the user declared with the
            # `ros_rate_callback` tag. It will be handled in the
            # `scxml_event_processor` module differently.
            or
            self.is_bt_response_event() and len(self.senders) == 0
        )

    def is_bt_response_event(self):
        """Check if the event is a behavior tree response event (running, success, failure).
        They may have no sender if the plugin does not implement it."""
        return self.name.startswith("bt_") and (
            self.name.endswith("_running") or
            self.name.endswith("_success") or
            self.name.endswith("_failure"))


class EventsHolder:
    """Class to hold all events in the existing automatons."""

    def __init__(self):
        self._events: Dict[str, Event] = {}

    def has_event(self, event_name: str) -> bool:
        return event_name in self._events

    def get_event(self, event_name: str) -> Event:
        return self._events[event_name]

    def get_events(self) -> Dict[str, Event]:
        return self._events

    def add_event(self, event: Event):
        assert event.name not in self._events, f"Event {event.name} must not be added twice."
        self._events[event.name] = event
