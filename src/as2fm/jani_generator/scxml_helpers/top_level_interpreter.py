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
Module reading the top level xml file containing the whole model to check.
"""

import json
import os
from copy import deepcopy
from typing import Dict, List, Optional

from as2fm.jani_generator.jani_entries import JaniModel, JaniProperty
from as2fm.jani_generator.ros_helpers.ros_action_handler import RosActionHandler
from as2fm.jani_generator.ros_helpers.ros_communication_handler import (
    RosCommunicationHandler,
    generate_plain_scxml_from_handlers,
    update_ros_communication_handlers,
)
from as2fm.jani_generator.ros_helpers.ros_service_handler import RosServiceHandler
from as2fm.jani_generator.ros_helpers.ros_timer import RosTimer, make_global_timer_scxml
from as2fm.jani_generator.scxml_helpers.roaml_model import (
    FullModel,
    RoamlDataStructures,
    RoamlMain,
)
from as2fm.jani_generator.scxml_helpers.scxml_to_jani import (
    convert_multiple_scxmls_to_jani,
    preprocess_jani_expressions,
)
from as2fm.scxml_converter.bt_converter import (
    bt_converter,
    generate_blackboard_scxml,
    get_blackboard_variables_from_models,
)
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition
from as2fm.scxml_converter.scxml_entries import (
    EventsToAutomata,
    ScxmlRoot,
    load_scxml_file,
)
from as2fm.scxml_converter.scxml_entries.scxml_data import ScxmlData
from as2fm.scxml_converter.scxml_entries.scxml_executable_entries import ScxmlAssign
from as2fm.scxml_converter.scxml_entries.scxml_transition import ScxmlTransition


def generate_plain_scxml_models_and_timers(model: FullModel) -> List[ScxmlRoot]:
    """Generate all plain SCXML models loaded from the full model dictionary."""
    custom_data_types: Dict[str, StructDefinition] = {}
    for struct_format, path in model.data_declarations:
        struct_definition_class = RoamlDataStructures.AVAILABLE_STRUCT_DEFINITIONS[struct_format]
        loaded_structs = struct_definition_class.from_file(path)
        custom_data_types.update(loaded_structs)

    for custom_struct_instance in custom_data_types.values():
        custom_struct_instance.expand_members(custom_data_types)
    # Load the skills and components scxml files (ROS-SCXML)
    scxml_files_to_convert: list = model.skills + model.components
    ros_scxmls: List[ScxmlRoot] = []
    for fname in scxml_files_to_convert:
        ros_scxmls.append(load_scxml_file(fname, custom_data_types))
    # Convert behavior tree and plugins to ROS-SCXML
    if model.bt is not None:
        ros_scxmls.extend(
            bt_converter(
                model.bt,
                model.plugins,
                model.bt_tick_rate,
                model.bt_tick_when_not_running,
                custom_data_types,
            )
        )
    # Convert the loaded entries to plain SCXML
    plain_scxml_models = []
    all_timers: List[RosTimer] = []
    all_services: Dict[str, RosCommunicationHandler] = {}
    all_actions: Dict[str, RosCommunicationHandler] = {}
    bt_blackboard_vars: Dict[str, str] = get_blackboard_variables_from_models(ros_scxmls)
    for scxml_entry in ros_scxmls:
        plain_scxmls, ros_declarations = scxml_entry.to_plain_scxml_and_declarations()
        for plain_scxml in plain_scxmls:
            plain_scxml.set_xml_origin(scxml_entry.get_xml_origin())
        # Handle ROS timers
        for timer_name, timer_rate in ros_declarations._timers.items():
            assert timer_name not in all_timers, f"Timer {timer_name} already exists."
            all_timers.append(RosTimer(timer_name, timer_rate))
        # Handle ROS Services
        update_ros_communication_handlers(
            scxml_entry.get_name(),
            RosServiceHandler,
            all_services,
            ros_declarations._service_servers,
            ros_declarations._service_clients,
        )
        # Handle ROS Actions
        update_ros_communication_handlers(
            scxml_entry.get_name(),
            RosActionHandler,
            all_actions,
            ros_declarations._action_servers,
            ros_declarations._action_clients,
        )
        plain_scxml_models.extend(plain_scxmls)
    # Generate sync SCXML model for BT Blackboard (if needed)
    if len(bt_blackboard_vars) > 0:
        plain_scxml_models.append(generate_blackboard_scxml(bt_blackboard_vars))
    # Generate sync SCXML models for services and actions
    for plain_scxml in generate_plain_scxml_from_handlers(all_services | all_actions):
        plain_scxml_models.append(plain_scxml)
    assert model.max_time is not None, "Expected model.max_time to be defined here."
    timer_scxml = make_global_timer_scxml(all_timers, model.max_time)
    if timer_scxml is not None:
        timer_scxml.set_custom_data_types(custom_data_types)
        plain_scxmls, _ = timer_scxml.to_plain_scxml_and_declarations()
        plain_scxml_models.extend(plain_scxmls)
    return plain_scxml_models


def export_plain_scxml_models(
    generated_scxml_path: str,
    plain_scxml_models: List[ScxmlRoot],
):
    """Generate the plain SCXML files adding all compatibility entries to fit the SCXML standard."""
    os.makedirs(generated_scxml_path, exist_ok=True)
    models_to_export = deepcopy(plain_scxml_models)
    # Compute the set of target automaton for each event
    event_targets: EventsToAutomata = {}
    for scxml_model in models_to_export:
        for event in scxml_model.get_transition_events():
            if event not in event_targets:
                event_targets[event] = set()
            event_targets[event].add(scxml_model.get_name())
        # Turn transitions with multiple targets and probabilities
        # into (multiple) plain SCXML transitions
        rand_variable_id = "__RAND__"
        rand_variable_declared = False
        for state in scxml_model.get_states():
            plain_scxml_transitions: List[ScxmlTransition] = []
            randomize = False
            for transition in state.get_body():
                probability = 0.0
                for target in transition.get_targets():
                    plain_scxml_condition = transition.get_condition()
                    target_probability = target.get_probability()
                    if target_probability is not None:
                        # Every time a transition has a probability:
                        # - Declare rand variable in datamodel (if not already done)
                        # - Randomize variable on state entry (if not already done)
                        # - Turn probability into a condition on the transition
                        if rand_variable_declared is False:
                            scxml_model.get_data_model().get_data_entries().append(
                                ScxmlData(
                                    id_=rand_variable_id,
                                    expr="0.0",
                                    data_type="float64",
                                )
                            )
                            rand_variable_declared = True
                        if randomize is False:
                            state.append_on_entry(
                                ScxmlAssign(location=rand_variable_id, expr="Math.random()")
                            )
                            randomize = True
                        if plain_scxml_condition is None:
                            plain_scxml_condition = ""
                        else:
                            plain_scxml_condition = plain_scxml_condition + " && "
                        plain_scxml_condition = (
                            plain_scxml_condition + f"{probability} < {rand_variable_id}"
                        )
                        probability += target_probability
                        plain_scxml_condition = (
                            plain_scxml_condition
                            + f" && {rand_variable_id} <= {probability}"
                        )
                    plain_scxml_transitions.append(
                        ScxmlTransition.make_single_target_transition(
                            target=target._target_id,
                            events=transition.get_events(),
                            condition=plain_scxml_condition,
                            body=target.get_body(),
                        )
                    )
            # Replace ASCXML transition with plain SCXML transition
            state._body = plain_scxml_transitions
    # Add the target automaton to each event sent
    for scxml_model in models_to_export:
        scxml_model.add_target_to_event_send(event_targets)
    # Export the models
    for scxml_model in models_to_export:
        with open(
            os.path.join(generated_scxml_path, f"{scxml_model.get_name()}.scxml"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(scxml_model.as_xml_string(data_type_as_attribute=False))


def interpret_top_level_xml(
    xml_path: str, *, jani_file: Optional[str] = None, scxmls_dir: Optional[str] = None
):
    """
    Interpret the top-level XML file as a Jani model. And write it to a file.
    The generated Jani model is written to the same directory as the input XML file under the
    name `main.jani`.

    :param xml_path: The path to the XML file to interpret.
    :param jani_file: The path to the output Jani file.
    :param scxmls_dir: The directory to store the generated plain SCXML files.
    """
    # Complete Model handling
    model_dir = os.path.dirname(xml_path)
    loaded_roaml = RoamlMain(xml_path)
    model = loaded_roaml.get_loaded_model()

    plain_scxml_models = generate_plain_scxml_models_and_timers(model)

    if scxmls_dir is not None:
        plain_scxml_dir = os.path.join(model_dir, scxmls_dir)
        export_plain_scxml_models(plain_scxml_dir, plain_scxml_models)
    if jani_file is not None:
        jani_model: JaniModel = convert_multiple_scxmls_to_jani(
            plain_scxml_models, model.max_array_size
        )
        with open(model.properties[0], "r", encoding="utf-8") as f:
            all_properties = json.load(f)["properties"]
            for property_dict in all_properties:
                jani_model.add_jani_property(JaniProperty.from_dict(property_dict))

        # Preprocess the JANI file, to remove non-standard artifacts
        preprocess_jani_expressions(jani_model)

        output_path = os.path.join(model_dir, jani_file)
        with open(output_path, "w", encoding="utf-8") as f:
            temp_dict = jani_model.as_dict()
            # print(temp_dict)
            json.dump(temp_dict, f, indent=2, ensure_ascii=False)
