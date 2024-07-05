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

"""Collection of various utilities for scxml entries."""

from typing import Dict


def check_topic_type_known(topic_definition: str) -> bool:
    """Check if python can import the provided topic definition."""
    # Check the input type has the expected structure
    if not (isinstance(topic_definition, str) and topic_definition.count("/") == 1):
        return False
    topic_ns, topic_type = topic_definition.split("/")
    if len(topic_ns) == 0 or len(topic_type) == 0:
        return False
    try:
        msg_importer = __import__(topic_ns + '.msg', fromlist=[''])
        _ = getattr(msg_importer, topic_type)
    except (ImportError, AttributeError):
        print(f"Error: SCXML ROS declarations: topic type {topic_definition} not found.")
        return False
    return True


def replace_ros_msg_expression(msg_expr: str) -> str:
    """Convert a ROS message expression (referring to ROS msg entries) to plain SCXML."""
    prefix = "_event." if msg_expr.startswith("_msg.") else ""
    return prefix + msg_expr.removeprefix("_msg.")


class HelperRosDeclarations:
    """Object that contains a description of the ROS declarations in the SCXML root."""

    def __init__(self):
        # Dict of publishers and subscribers: topic name -> type
        self._publishers: Dict[str, str] = {}
        self._subscribers: Dict[str, str] = {}
        self._timers: Dict[str, float] = {}

    def append_publisher(self, topic_name: str, topic_type: str) -> None:
        assert isinstance(topic_name, str) and isinstance(topic_type, str), \
            "Error: ROS declarations: topic name and type must be strings."
        assert topic_name not in self._publishers, \
            f"Error: ROS declarations: topic publisher {topic_name} already declared."
        self._publishers[topic_name] = topic_type

    def append_subscriber(self, topic_name: str, topic_type: str) -> None:
        assert isinstance(topic_name, str) and isinstance(topic_type, str), \
            "Error: ROS declarations: topic name and type must be strings."
        assert topic_name not in self._subscribers, \
            f"Error: ROS declarations: topic subscriber {topic_name} already declared."
        self._subscribers[topic_name] = topic_type

    def append_timer(self, timer_name: str, timer_rate: float) -> None:
        assert isinstance(timer_name, str), "Error: ROS declarations: timer name must be a string."
        assert isinstance(timer_rate, float) and timer_rate > 0, \
            "Error: ROS declarations: timer rate must be a positive number."
        assert timer_name not in self._timers, \
            f"Error: ROS declarations: timer {timer_name} already declared."
        self._timers[timer_name] = timer_rate

    def is_publisher_defined(self, topic_name: str) -> bool:
        return topic_name in self._publishers

    def is_subscriber_defined(self, topic_name: str) -> bool:
        return topic_name in self._subscribers

    def is_timer_defined(self, timer_name: str) -> bool:
        return timer_name in self._timers

    def get_timers(self) -> Dict[str, float]:
        return self._timers
