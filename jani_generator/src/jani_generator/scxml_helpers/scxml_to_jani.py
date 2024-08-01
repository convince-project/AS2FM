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

from typing import List, Union

from scxml_converter.scxml_entries import ScxmlRoot

from jani_generator.jani_entries.jani_automaton import JaniAutomaton
from jani_generator.jani_entries.jani_model import JaniModel
from jani_generator.ros_helpers.ros_timer import (RosTimer,
                                                  make_global_timer_automaton)
from jani_generator.scxml_helpers.scxml_event import EventsHolder
from jani_generator.scxml_helpers.scxml_event_processor import \
    implement_scxml_events_as_jani_syncs
from jani_generator.scxml_helpers.scxml_tags import BaseTag


def convert_scxml_root_to_jani_automaton(
        scxml_root: ScxmlRoot, jani_automaton: JaniAutomaton, events_holder: EventsHolder
) -> None:
    """
    Convert an SCXML element to a Jani automaton.

    :param element: The SCXML element to convert (Must be the root scxml tag of the file).
    :param jani_automaton: The Jani automaton to write the converted element to.
    :param events_holder: The holder for the events to be implemented as Jani syncs.
    """
    BaseTag.from_element(scxml_root, [], (jani_automaton,
                         events_holder)).write_model()


def convert_multiple_scxmls_to_jani(
        scxmls: List[Union[str, ScxmlRoot]],
        timers: List[RosTimer],
        max_time_ns: int
) -> JaniModel:
    """
    Assemble automata from multiple SCXML files into a Jani model.

    :param scxml_paths: The paths to the SCXML files to convert.
    :return: The Jani model containing the converted automata.
    """
    base_model = JaniModel()
    events_holder = EventsHolder()
    for input_scxml in scxmls:
        if isinstance(input_scxml, str):
            scxml_root = ScxmlRoot.from_scxml_file(input_scxml)
        else:
            assert isinstance(input_scxml, ScxmlRoot)
            scxml_root = input_scxml
        assert scxml_root.is_plain_scxml(), \
            f"Input model {scxml_root.get_name()} does not contain a plain SCXML model."
        automaton = JaniAutomaton()
        convert_scxml_root_to_jani_automaton(scxml_root, automaton, events_holder)
        base_model.add_jani_automaton(automaton)
    timer_automaton = make_global_timer_automaton(timers, max_time_ns)
    if timer_automaton is not None:
        base_model.add_jani_automaton(timer_automaton)
    implement_scxml_events_as_jani_syncs(events_holder, timers, base_model)

    return base_model
