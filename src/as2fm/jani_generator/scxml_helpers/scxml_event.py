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

import re
from typing import Dict, List, Optional

from as2fm.jani_generator.ros_helpers.ros_timer import ROS_TIMER_RATE_EVENT_PREFIX
from as2fm.scxml_converter.scxml_entries.bt_utils import is_bt_response_event, is_bt_tick_event
from as2fm.scxml_converter.scxml_entries.ros_utils import is_action_event, is_srv_event


class EventSender:
    def __init__(self, automaton_name: str, edge_action_name: str):
        """
        Initialize the event sender.

        :param automaton_name: The name of the automaton sending the event.
        :param edge_action_name: The name of the entity sending the event.
            (location_name for ON_ENTRY and ON_EXIT, edge_action_name for EDGE)
        """
        self.automaton_name = automaton_name
        self.edge_action_name = edge_action_name


class EventReceiver:
    def __init__(self, automaton_name: str, edge_action_name: str):
        self.automaton_name = automaton_name
        self.edge_action_name = edge_action_name


class Event:
    def __init__(self, name: str, data_struct: Optional[Dict[str, type]] = None):
        self.name = name
        self.data_struct = data_struct
        # Map automaton -> event name
        # TODO: EventSender and EventReceiver are only containers for the automaton-action name pair
        # In the future, this could be a Dict[str, str] or even a Set, if we assume the action name
        # always matches with the event name.
        self.senders: Dict[str, EventSender] = {}
        self.receivers: Dict[str, EventReceiver] = {}

    def add_sender_edge(self, automaton_name: str, edge_action_name: str):
        """Add information about the edge sending the event."""
        self.senders.update({automaton_name: EventSender(automaton_name, edge_action_name)})

    def add_receiver(self, automaton_name: str, edge_action_name: str):
        """Add information about the edges triggered by the event."""
        self.receivers.update({automaton_name: EventReceiver(automaton_name, edge_action_name)})

    def get_senders(self) -> List[EventSender]:
        """Get the senders of the event."""
        return [sender for sender in self.senders.values()]

    def get_receivers(self) -> List[EventReceiver]:
        """Get the receivers of the event."""
        return [receiver for receiver in self.receivers.values()]

    def get_data_structure(self) -> Dict[str, type]:
        """Get the data structure of the event."""
        if self.data_struct is None:
            return {}
        return self.data_struct

    def set_data_structure(self, data_struct: Dict[str, type]):
        """Set the data structure of the event."""
        self.data_struct = data_struct

    def has_senders(self) -> bool:
        """Check if the event has one or more senders."""
        return len(self.senders) > 0

    def has_receivers(self) -> bool:
        """Check if the event has one or more receivers."""
        return len(self.receivers) > 0

    def must_be_skipped_in_jani_conversion(self):
        """Indicate whether this must be considered in the conversion to jani."""
        return (
            self.name.startswith(ROS_TIMER_RATE_EVENT_PREFIX)
            or
            # If the event is a timer event, there is only a receiver
            # It is the edge that the user declared with the
            # `ros_rate_callback` tag. It will be handled in the
            # `scxml_event_processor` module differently.
            self.is_bt_response_event()
            and len(self.senders) == 0
            or self.is_optional_action_event()
            and len(self.senders) == 0
        )

    def is_bt_response_event(self):
        """Check if the event is a behavior tree response event (running, success, failure).
        They may have no sender if the plugin does not implement it."""
        # TODO: Remove it when deprecated support for running, success, failure BT events is removed
        return self.name.startswith("bt_") and (
            self.name.endswith("_running")
            or self.name.endswith("_success")
            or self.name.endswith("_failure")
        )

    def is_optional_action_event(self):
        return self.is_action_feedback_event() or self.is_action_rejected_event()

    def is_action_feedback_event(self):
        """Check if the event is an action feedback event."""
        return re.match(r"^action_.*_feedback$", self.name) is not None

    def is_action_rejected_event(self):
        """Check if the event is an action rejected event."""
        return re.match(r"^action_.*_goal_rejected$", self.name) is not None


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


def is_event_synched(event_name: str) -> bool:
    """
    Check if the event is synched, hence there should not be autogenerated self loops.

    :param event_name: The name of the event to evaluate.
    """
    return (
        is_bt_tick_event(event_name)
        or is_bt_response_event(event_name)
        or is_action_event(event_name)
        or is_srv_event(event_name)
    )
