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
Representation of ROS timers.
"""

from typing import List, Optional, Tuple

from math import gcd, floor
from as2fm.jani_generator.jani_entries import (
    JaniAssignment, JaniAutomaton, JaniEdge, JaniExpression, JaniGuard,  JaniVariable)
from as2fm.jani_generator.jani_entries.jani_expression_generator import (
    lower_operator, not_operator, modulo_operator, and_operator, equal_operator, plus_operator)
from as2fm.scxml_converter.scxml_entries import (
    ScxmlAssign, ScxmlData, ScxmlDataModel, ScxmlExecutionBody, ScxmlIf, ScxmlRoot, ScxmlSend,
    ScxmlState, ScxmlTransition)


TIME_UNITS = {
    "s": 1,
    "ms": 1e-3,
    "us": 1e-6,
    "ns": 1e-9,
}

GLOBAL_TIMER_NAME = "global_timer"
GLOBAL_TIMER_TICK_ACTION = "global_timer_tick"
ROS_TIMER_RATE_EVENT_PREFIX = "ros_time_rate."


def convert_time_between_units(time: int, from_unit: str, to_unit: str) -> int:
    """Convert time from one unit to another."""
    assert from_unit in TIME_UNITS, f"Unit {from_unit} not supported."
    assert to_unit in TIME_UNITS, f"Unit {to_unit} not supported."
    assert time >= 0, "Time must be positive."
    if from_unit == to_unit:
        return time
    new_time = time * TIME_UNITS[from_unit] / TIME_UNITS[to_unit]
    # make sure we do not lose precision
    assert int(new_time) == new_time, \
        f"Conversion from {from_unit} to {to_unit} is not exact."
    return int(new_time)


def _to_best_int_period(period: float) -> Tuple[int, str, float]:
    """Choose the best time unit for a given period.
    Such that the period is an integer and the unit is the largest possible."""
    for unit, factor in TIME_UNITS.items():
        period_in_unit = period / factor
        int_period_in_unit = floor(period_in_unit)
        if int_period_in_unit == period_in_unit:
            # This period exactly fits into the unit
            return int(period_in_unit), unit, factor
        elif int_period_in_unit > 100:
            # We do not want to have too large numbers
            return int_period_in_unit, unit, factor
    raise ValueError(f"Period {period} cannot be converted to an integer.")


class RosTimer(object):
    def __init__(self, name: str, freq: float) -> None:
        self.name = name
        self.freq = freq
        self.period = 1.0 / freq
        self.period_int, self.unit, self.factor = _to_best_int_period(
            self.period)


def get_common_time_step(timers: List[RosTimer]) -> Tuple[int, str]:
    """
    Get the common time step of a list of ROS timers.

    :param timers: The list of ROS timers.
    :return: The common time step and time unit.
    """
    if len(timers) == 0:
        raise ValueError("At least one timer is required.")
    common_unit = "s"
    for timer in timers:
        if TIME_UNITS[timer.unit] < TIME_UNITS[common_unit]:
            common_unit = timer.unit
    timer_periods = [
        convert_time_between_units(timer.period_int, timer.unit, common_unit) for timer in timers]
    common_period = gcd(*timer_periods)
    return common_period, common_unit


def make_global_timer_automaton(timers: List[RosTimer],
                                max_time_ns: int) -> Optional[JaniAutomaton]:
    """
    Create a global timer automaton from a list of ROS timers.

    :param timers: The list of ROS timers.
    :return: The global timer automaton.
    """
    if len(timers) == 0:
        return None
    global_timer_period, global_timer_period_unit = get_common_time_step(timers)
    timers_map = {
        timer.name: convert_time_between_units(timer.period_int, timer.unit,
                                               global_timer_period_unit)
        for timer in timers
    }
    try:
        max_time = convert_time_between_units(
            max_time_ns, "ns", global_timer_period_unit)
    except AssertionError:
        raise ValueError(
            f"Max time {max_time_ns} cannot be converted to {global_timer_period_unit}. "
            "The max_time must have a unit that is greater or equal to the smallest timer period.")

    # Automaton
    LOC_NAME = "loc"
    timer_automaton = JaniAutomaton()
    timer_automaton.set_name(GLOBAL_TIMER_NAME)
    timer_automaton.add_location(LOC_NAME, is_initial=True)

    # Check iif timers are correctly defined
    assert len(timers) > 0, "At least one timer is required."

    # variables
    variable_names = [f"{timer.name}_needed" for timer in timers]
    timer_automaton.add_variable(
        JaniVariable("t", int, JaniExpression(0)))
    for variable_name in variable_names:
        timer_automaton.add_variable(
            JaniVariable(variable_name, bool, JaniExpression(True)))
        # it is initially true, because everything "x % 0 == 0"

    # edges
    # timer assignments
    timer_assignments = []
    for i, (timer, variable_name) in enumerate(zip(timers, variable_names)):
        period_in_global_unit = timers_map[timer.name]
        timer_assignments.append(JaniAssignment({
            "ref": variable_name,
            # t % {period_in_global_unit} == 0
            "value": equal_operator(modulo_operator("t", period_in_global_unit), 0),
            "index": i+1}))  # 1, because t is at index 0
    # guard for main edge
    # Max time not reached yet
    guard_exp = lower_operator("t", max_time)
    assert len(variable_names) > 0, "At least one timer is required."
    # No unprocessed timer callbacks present
    for variable_name in variable_names:
        unprocessed_timer_exp = not_operator(variable_name)
        # Append this expression to the guard using the and operator
        guard_exp = and_operator(guard_exp, unprocessed_timer_exp)
        # TODO: write test case for this (and switch to not(t1 or t2 or ... or tN) guard)
    assignments = [
        # t = t + global_timer_period
        JaniAssignment({
            "ref": "t",
            "value": plus_operator("t", global_timer_period),
            "index": 0})
    ] + timer_assignments
    iterator_edge = JaniEdge({
        "location": LOC_NAME,
        "guard": JaniGuard(guard_exp),
        "destinations": [{
            "location": LOC_NAME,
            "assignments": assignments
        }],
        "action": GLOBAL_TIMER_TICK_ACTION
    }
    )
    timer_automaton.add_edge(iterator_edge)

    # edges to sync with ROS timers
    for timer in timers:
        guard = JaniGuard(JaniExpression(f"{timer.name}_needed"))
        timer_edge = JaniEdge({
            "location": LOC_NAME,
            "action": f"{ROS_TIMER_RATE_EVENT_PREFIX}{timer.name}_on_receive",
            "guard": guard,
            "destinations": [{
                "location": LOC_NAME,
                "assignments": [
                    JaniAssignment({
                        "ref": f"{timer.name}_needed",
                        "value": JaniExpression(False)
                    })
                ]
            }]
        })
        timer_automaton.add_edge(timer_edge)
    return timer_automaton


def make_global_timer_scxml(timers: List[RosTimer], max_time_ns: int) -> Optional[ScxmlRoot]:
    """
    Create a global timer SCXML from a list of ROS timers.

    :param timers: The list of ROS timers.
    :return: The global timer SCXML.
    """
    """
    Generate an SCXML model containing the timers.
    """
    if len(timers) == 0:
        return None
    global_timer_period, global_timer_period_unit = get_common_time_step(timers)
    timers_map = {
        timer.name: convert_time_between_units(timer.period_int, timer.unit,
                                               global_timer_period_unit)
        for timer in timers
    }
    try:
        max_time = convert_time_between_units(
            max_time_ns, "ns", global_timer_period_unit)
    except AssertionError:
        raise ValueError(
            f"Max time {max_time_ns} cannot be converted to {global_timer_period_unit}. "
            "The max_time must have a unit that is greater or equal to the smallest timer period.")
    scxml_root = ScxmlRoot("global_timer_automata")
    scxml_root.set_data_model(ScxmlDataModel([ScxmlData("current_time", "0", "int64")]))
    idle_state = ScxmlState("idle")
    global_timer_tick_body: ScxmlExecutionBody = []
    global_timer_tick_body.append(ScxmlAssign("current_time",
                                              f"current_time + {global_timer_period}"))
    for timer_name, timer_period in timers_map.items():
        global_timer_tick_body.append(ScxmlIf([(f"(current_time % {timer_period}) == 0",
                                               [ScxmlSend(f"ros_time_rate.{timer_name}")])]))
    timer_step_transition = ScxmlTransition("idle", [], f"current_time < {max_time}",
                                            global_timer_tick_body)
    idle_state.add_transition(timer_step_transition)
    scxml_root.add_state(idle_state, initial=True)
    return scxml_root
