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

from jani_generator.jani_entries.jani_assignment import JaniAssignment
from jani_generator.jani_entries.jani_automaton import JaniAutomaton
from jani_generator.jani_entries.jani_edge import JaniEdge
from jani_generator.jani_entries.jani_expression import JaniExpression
from jani_generator.jani_entries.jani_guard import JaniGuard
from jani_generator.jani_entries.jani_variable import JaniVariable
from scxml_converter.scxml_converter import ROS_TIMER_RATE_EVENT_PREFIX

TIME_UNITS = {
    "s": 1,
    "ms": 1e-3,
    "us": 1e-6,
    "ns": 1e-9,
}


def _convert_time_between_units(time: int, from_unit: str, to_unit: str) -> int:
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
        if int(period / factor) == period / factor:
            period_int = int(period / factor)
            return period_int, unit, factor
    raise ValueError(f"Period {period} cannot be converted to an integer.")


class RosTimer(object):
    def __init__(self, name: str, freq: float) -> None:
        self.name = name
        self.freq = freq
        self.period = 1.0 / freq
        self.period_int, self.unit, self.factor = _to_best_int_period(
            self.period)


def make_global_timer_automaton(timers: List[RosTimer],
                                max_time_ns: int) -> Optional[JaniAutomaton]:
    """
    Create a global timer automaton from a list of ROS timers.

    :param timers: The list of ROS timers.
    :return: The global timer automaton.
    """
    if len(timers) == 0:
        return None
    # Calculate the period of the global timer
    smallest_unit: str = "s"
    for timer in timers:
        if TIME_UNITS[timer.unit] < TIME_UNITS[smallest_unit]:
            smallest_unit = timer.unit
    timer_periods_in_smallest_unit = {
        timer.name: _convert_time_between_units(
            timer.period_int, timer.unit, smallest_unit)
        for timer in timers
    }
    # TODO: Should be greatest-common-divisor instead
    global_timer_period = min(timer_periods_in_smallest_unit.values())
    global_timer_period_unit = smallest_unit

    try:
        max_time = _convert_time_between_units(
            max_time_ns, "ns", global_timer_period_unit)
    except AssertionError:
        raise ValueError(
            f"Max time {max_time_ns} cannot be converted to {global_timer_period_unit}. "
            "The max_time must have a unit that is greater or equal to the smallest timer period.")

    # Automaton
    LOC_NAME = "loc"
    timer_automaton = JaniAutomaton()
    timer_automaton.set_name("global_timer")
    timer_automaton.add_location(LOC_NAME, is_initial=True)

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
        period_in_gloabl_unit = timer_periods_in_smallest_unit[timer.name]
        timer_assignments.append(JaniAssignment({
            "ref": variable_name,
            # t % {period_in_gloabl_unit} == 0
            "value": JaniExpression({
                "op": "=",
                "left": JaniExpression({
                    "op": "%",
                    "left": JaniExpression("t"),
                    "right": JaniExpression(period_in_gloabl_unit)
                }),
                "right": JaniExpression(0)
            }),
            "index": i+1}))  # 1, because t is at index 0
    # guard for main edge
    guard_exp = JaniExpression({
        "op": "<",
        "left": JaniExpression("t"),
        "right": JaniExpression(max_time)
    })
    assert len(variable_names) > 0, "At least one timer is required."
    for variable_name in variable_names:
        singular_exp = JaniExpression({
            "op": "¬",
            "exp": JaniExpression(variable_name)
        })
        guard_exp = JaniExpression({
            "op": "∧",
            "left": guard_exp,
            "right": singular_exp
        })  # TODO: write test case for this
    assignments = [
        # t = t + global_timer_period
        JaniAssignment({
            "ref": "t",
            "value": JaniExpression({
                "op": "+",
                "left": JaniExpression("t"),
                "right": JaniExpression(global_timer_period)
            }),
            "index": 0})
    ] + timer_assignments
    iterator_edge = JaniEdge({
        "location": LOC_NAME,
        "guard": JaniGuard(guard_exp),
        "destinations": [{
            "location": LOC_NAME,
            "assignments": assignments
        }],
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
