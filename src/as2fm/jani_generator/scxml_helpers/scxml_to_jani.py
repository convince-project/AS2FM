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
Module handling the conversion from SCXML to Jani.
"""

from typing import Dict, List

from as2fm.jani_generator.jani_entries import (
    JaniAssignment,
    JaniAutomaton,
    JaniExpression,
    JaniModel,
    JaniVariable,
)
from as2fm.jani_generator.jani_entries.jani_helpers import expand_random_variables_in_jani_model
from as2fm.jani_generator.ros_helpers.ros_communication_handler import (
    remove_empty_self_loops_from_interface_handlers_in_jani,
)
from as2fm.jani_generator.ros_helpers.ros_timer import RosTimer, make_global_timer_automaton
from as2fm.jani_generator.scxml_helpers.scxml_event import EventsHolder
from as2fm.jani_generator.scxml_helpers.scxml_event_processor import (
    implement_scxml_events_as_jani_syncs,
)
from as2fm.jani_generator.scxml_helpers.scxml_tags import BaseTag
from as2fm.scxml_converter.scxml_entries import ScxmlRoot


def convert_scxml_root_to_jani_automaton(
    scxml_root: ScxmlRoot,
    jani_automaton: JaniAutomaton,
    events_holder: EventsHolder,
    max_array_size: int,
) -> None:
    """
    Convert an SCXML element to a Jani automaton.

    :param element: The SCXML element to convert (Must be the root scxml tag of the file).
    :param jani_automaton: The Jani automaton to write the converted element to.
    :param events_holder: The holder for the events to be implemented as Jani syncs.
    :param max_array_size: The max size of the arrays in the model.
    """
    BaseTag.from_element(
        scxml_root, [], (jani_automaton, events_holder), max_array_size
    ).write_model()


def convert_multiple_scxmls_to_jani(
    scxmls: List[ScxmlRoot], timers: List[RosTimer], max_time_ns: int, max_array_size: int
) -> JaniModel:
    """
    Assemble automata from multiple SCXML files into a Jani model.

    :param scxmls: List of SCXML Root objects (or file paths) to be included in the Jani model.
    :param timers: List of ROS timers to be included in the Jani model.
    :param max_time_ns: The maximum time in nanoseconds.
    :param max_array_size: The max size of the arrays in the model.
    :return: The Jani model containing the converted automata.
    """
    base_model = JaniModel()
    base_model.add_feature("arrays")
    base_model.add_feature("trigonometric-functions")
    events_holder = EventsHolder()
    for input_scxml in scxmls:
        assert isinstance(input_scxml, ScxmlRoot)
        scxml_root = input_scxml
        assert (
            scxml_root.is_plain_scxml()
        ), f"Input model {scxml_root.get_name()} does not contain a plain SCXML model."
        automaton = JaniAutomaton()
        convert_scxml_root_to_jani_automaton(scxml_root, automaton, events_holder, max_array_size)
        base_model.add_jani_automaton(automaton)
    timer_automaton = make_global_timer_automaton(timers, max_time_ns)
    if timer_automaton is not None:
        base_model.add_jani_automaton(timer_automaton)
    implement_scxml_events_as_jani_syncs(events_holder, timers, max_array_size, base_model)
    remove_empty_self_loops_from_interface_handlers_in_jani(base_model)
    expand_random_variables_in_jani_model(base_model, n_options=100)
    return base_model


def preprocess_jani_expressions(jani_model: JaniModel):
    """Preprocess JANI expressions in the model to be compatible with the standard JANI format."""
    global_variables = jani_model.get_variables()
    for jani_automaton in jani_model.get_automata():
        context_variables = global_variables | jani_automaton.get_variables()
        for jani_edge in jani_automaton.get_edges():
            for jani_destination in jani_edge.destinations:
                assignments: List[JaniAssignment] = jani_destination["assignments"]
                for assignment in assignments:
                    assignment.set_expression(
                        _preprocess_jani_expression(assignment.get_expression(), context_variables)
                    )
    for property in jani_model.get_properties():
        # TODO
        pass


def _preprocess_jani_expression(
    jani_expression: JaniExpression, context_vars: Dict[str, JaniVariable]
) -> JaniExpression:
    return jani_expression
