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

"""Test the ROS timer conversion"""

from typing import List

from as2fm.jani_generator.jani_entries import JaniAutomaton
from as2fm.jani_generator.ros_helpers.ros_timer import (
    GLOBAL_TIMER_TICK_ACTION,
    RosTimer,
    make_global_timer_scxml,
)
from as2fm.jani_generator.scxml_helpers.scxml_event import EventsHolder
from as2fm.jani_generator.scxml_helpers.scxml_event_processor import (
    _preprocess_global_timer_automaton,
)
from as2fm.jani_generator.scxml_helpers.scxml_to_jani import convert_scxml_root_to_jani_automaton


def generic_ros_timer_check(rate_hz: float, expected_unit: str, expected_int_period: int):
    """
    Generic test function for the RosTimer class.

    :param rate_hz: The rate of the timer (in Hz).
    :param expected_unit: The expected unit of the timer period (as a string).
    :param expected_int_period: The expected integer period of the timer (related to the time unit).
    """
    name = "timer"
    ros_timer = RosTimer(name, rate_hz)
    assert ros_timer.name == name
    assert ros_timer.freq == rate_hz
    assert ros_timer.unit == expected_unit
    assert ros_timer.period_int == expected_int_period


def get_time_step_from_timer_automaton(automaton: JaniAutomaton) -> int:
    """
    Get the time step from the global timer automaton.
    """
    global_tick_edge = [
        edge for edge in automaton.get_edges() if edge.get_action() == GLOBAL_TIMER_TICK_ACTION
    ]
    assert (
        len(global_tick_edge) == 2
    ), f"Expected exactly two edges advancing the global timer in >{automaton.get_name()}<"
    edge_dict = global_tick_edge[0].as_dict({})
    return int(edge_dict["destinations"][0]["assignments"][0]["value"]["right"])


def generic_global_timer_check(timer_rates: List[float], expected_time_step: int):
    """
    Generic test function for the global timer automaton generation.
    """
    max_time_ns = int(100 * 1e9)  # 100 seconds in nanoseconds
    timers: List[RosTimer] = []
    for i, rate in enumerate(timer_rates):
        timers.append(RosTimer(f"timer{i}", rate))
    ros_timer_scxml = make_global_timer_scxml(timers, max_time_ns)
    assert ros_timer_scxml is not None
    timer_scxmls, _ = ros_timer_scxml.to_plain_scxml_and_declarations()
    assert len(timer_scxmls) == 1
    events_holder = EventsHolder()
    jani_automaton = convert_scxml_root_to_jani_automaton(timer_scxmls[0], events_holder, 0)
    _preprocess_global_timer_automaton(jani_automaton)
    time_step = get_time_step_from_timer_automaton(jani_automaton)
    assert (
        time_step == expected_time_step
    ), f"Expected the global timer to advance by {expected_time_step} each time."


def test_ros_timer_10hz():
    """
    Test the RosTimer class with a 10 Hz timer.
    """
    generic_ros_timer_check(10.0, "ms", 100)


def test_ros_timer_1mhz():
    """
    Test the RosTimer class with a 1 MHz timer.
    """
    generic_ros_timer_check(1e6, "us", 1)


def test_ros_timer_1hz():
    """
    Test the RosTimer class with a 1 Hz timer.
    """
    generic_ros_timer_check(1.0, "s", 1)


def test_ros_timer_3hz():
    """
    Test the RosTimer class with a 3 Hz timer.
    """
    generic_ros_timer_check(3.0, "ms", 333)


def test_global_timer_generation_1_2_5_hz():
    """
    Test the generation of the global timer automaton with 1, 2, and 5 Hz timers.
    We expect the global period to be 100ms.
    """
    generic_global_timer_check([1.0, 2.0, 5.0], 100)


def test_global_timer_generation_3_9_hz():
    """
    Test the generation of the global timer automaton with 3 and 9 Hz timers.
    We expect the global period to be 111ms.
    """
    generic_global_timer_check([3.0, 9.0], 111)


def test_global_timer_generation_less_1_hz():
    """
    Test the generation of the global timer automaton with 0.5 and 0.1 Hz timers.
    We expect the global period to be 2ms.
    """
    generic_global_timer_check([0.5, 0.1], 2)
