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
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import lxml.etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import remove_namespace, string_as_bool
from as2fm.as2fm_common.logging import get_error_msg, set_filepath_for_all_elements
from as2fm.jani_generator.jani_entries import JaniModel, JaniProperty
from as2fm.jani_generator.ros_helpers.ros_action_handler import RosActionHandler
from as2fm.jani_generator.ros_helpers.ros_communication_handler import (
    RosCommunicationHandler,
    generate_plain_scxml_from_handlers,
    update_ros_communication_handlers,
)
from as2fm.jani_generator.ros_helpers.ros_service_handler import RosServiceHandler
from as2fm.jani_generator.ros_helpers.ros_timer import RosTimer, make_global_timer_scxml
from as2fm.jani_generator.scxml_helpers.scxml_to_jani import (
    convert_multiple_scxmls_to_jani,
    preprocess_jani_expressions,
)
from as2fm.scxml_converter.bt_converter import (
    bt_converter,
    generate_blackboard_scxml,
    get_blackboard_variables_from_models,
)
from as2fm.scxml_converter.scxml_entries import EventsToAutomata, ScxmlRoot
from as2fm.scxml_converter.xml_data_types.xml_struct_definition import XmlStructDefinition
from as2fm.scxml_converter.xml_data_types.xml_types import read_types_file


@dataclass()
class FullModel:
    # The maximum time the model is allowed to run, in nanoseconds
    max_time: Optional[int] = None
    # Max size of "dynamic" arrays defined in the SCXML models
    max_array_size: int = field(default=100)
    # Tick rate for the loaded BT in Hz
    bt_tick_rate: float = field(default=1.0)
    # Whether to keep ticking the BT after it returns SUCCESS / FAILURE
    bt_tick_when_not_running: bool = field(default=False)
    # Paths to custom data declarations
    data_declarations: List[str] = field(default_factory=list)
    # Path to the behavior tree loaded in the model
    bt: Optional[str] = None
    # Paths to the SCXML models of the BT nodes used in the model
    plugins: List[str] = field(default_factory=list)
    # Paths to the SCXML models of the non-BT nodes in the model
    skills: List[str] = field(default_factory=list)
    # Similar to the skills, currently unused
    components: List[str] = field(default_factory=list)
    # Path to the properties definition, currently in JANI
    properties: List[str] = field(default_factory=list)


def _parse_time_element(time_element: XmlElement) -> int:
    """
    Interpret a time element. Output is in nanoseconds.

    :param time_element: The time element to interpret.
    :return: The interpreted time in nanoseconds.
    """
    TIME_MULTIPLIERS = {"s": 1_000_000_000, "ms": 1_000_000, "us": 1_000, "ns": 1}
    time_unit = time_element.attrib["unit"]
    assert time_unit in TIME_MULTIPLIERS, f"Invalid time unit: {time_unit}"
    return int(time_element.attrib["value"]) * TIME_MULTIPLIERS[time_unit]


def parse_main_xml(xml_path: str) -> FullModel:
    """
    Interpret the top-level XML file and return it as a FullModel object.
    """
    # Used to generate absolute paths of scxml models
    folder_of_xml = os.path.dirname(xml_path)
    parser_wo_comments = ET.XMLParser(remove_comments=True)
    with open(xml_path, "r", encoding="utf-8") as f:
        xml = ET.parse(f, parser=parser_wo_comments)
    set_filepath_for_all_elements(xml.getroot(), xml_path)
    assert remove_namespace(xml.getroot().tag) == "convince_mc_tc", get_error_msg(
        xml.getroot(), "The top-level XML element must be convince_mc_tc."
    )
    model = FullModel()
    for first_level in xml.getroot():
        if remove_namespace(first_level.tag) == "mc_parameters":
            for mc_parameter in first_level:
                # if remove_namespace(mc_parameter.tag) == "time_resolution":
                #     time_resolution = _parse_time_element(mc_parameter)
                if remove_namespace(mc_parameter.tag) == "max_time":
                    model.max_time = _parse_time_element(mc_parameter)
                elif remove_namespace(mc_parameter.tag) == "max_array_size":
                    model.max_array_size = int(mc_parameter.attrib["value"])
                elif remove_namespace(mc_parameter.tag) == "bt_tick_rate":
                    model.bt_tick_rate = float(mc_parameter.attrib["value"])
                elif remove_namespace(mc_parameter.tag) == "bt_tick_if_not_running":
                    model.bt_tick_when_not_running = string_as_bool(mc_parameter.attrib["value"])
                else:
                    raise ValueError(
                        get_error_msg(mc_parameter, f"Invalid mc_parameter tag: {mc_parameter.tag}")
                    )
            assert model.max_time is not None, get_error_msg(
                first_level, "`max_time` must be defined."
            )
        elif remove_namespace(first_level.tag) == "data_declarations":
            for child in first_level:
                if remove_namespace(child.tag) == "input":
                    if child.attrib["type"] != "type-declarations":
                        raise ValueError(
                            get_error_msg(
                                child,
                                "Only `type-declarations` are supported under the "
                                + "`data_declarations` tag.",
                            )
                        )
                    model.data_declarations.append(os.path.join(folder_of_xml, child.attrib["src"]))
                else:
                    raise ValueError(
                        get_error_msg(child, f"Invalid data_declarations tag: {child.tag} != input")
                    )
        elif remove_namespace(first_level.tag) == "behavior_tree":
            for child in first_level:
                if remove_namespace(child.tag) == "input":
                    if child.attrib["type"] == "bt.cpp-xml":
                        assert model.bt is None, "Only one Behavior Tree is supported."
                        model.bt = os.path.join(folder_of_xml, child.attrib["src"])
                    elif child.attrib["type"] == "bt-plugin-ros-scxml":
                        model.plugins.append(os.path.join(folder_of_xml, child.attrib["src"]))
                    else:
                        raise ValueError(
                            get_error_msg(child, f"Invalid input type: {child.attrib['type']}")
                        )
                else:
                    raise ValueError(
                        get_error_msg(child, f"Invalid behavior_tree tag: {child.tag} != input")
                    )
            assert model.bt is not None, get_error_msg(
                first_level, "A Behavior Tree must be defined."
            )
        elif remove_namespace(first_level.tag) == "node_models":
            for node_model in first_level:
                assert remove_namespace(node_model.tag) == "input", get_error_msg(
                    node_model, "Only input tags are supported."
                )
                assert node_model.attrib["type"] == "ros-scxml", get_error_msg(
                    node_model, "Only ROS-SCXML node models are supported."
                )
                model.skills.append(os.path.join(folder_of_xml, node_model.attrib["src"]))
        elif remove_namespace(first_level.tag) == "properties":
            for jani_property in first_level:
                assert remove_namespace(jani_property.tag) == "input", get_error_msg(
                    jani_property, "Only input tags are supported."
                )
                assert jani_property.attrib["type"] == "jani", get_error_msg(
                    jani_property,
                    "Only Jani properties are supported, not {jani_property.attrib['type']}.",
                )
                model.properties.append(os.path.join(folder_of_xml, jani_property.attrib["src"]))
            assert len(model.properties) == 1, get_error_msg(
                first_level, "Only exactly one Jani property is supported."
            )
        else:
            raise ValueError(
                get_error_msg(first_level, f"Invalid main point tag: {first_level.tag}")
            )
    return model


def generate_plain_scxml_models_and_timers(
    model: FullModel, custom_data_types: Dict[str, XmlStructDefinition]
) -> List[ScxmlRoot]:
    """Generate all plain SCXML models loaded from the full model dictionary."""
    # Load the skills and components scxml files (ROS-SCXML)
    scxml_files_to_convert: list = model.skills + model.components
    ros_scxmls: List[ScxmlRoot] = []
    for fname in scxml_files_to_convert:
        ros_scxmls.append(ScxmlRoot.from_scxml_file(fname, custom_data_types))
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
    # Add the target automaton to each event sent
    for scxml_model in models_to_export:
        scxml_model.add_targets_to_scxml_sends(event_targets)
    # Export the models
    for scxml_model in models_to_export:
        with open(
            os.path.join(generated_scxml_path, f"{scxml_model.get_name()}.scxml"),
            "w",
            encoding="utf-8",
        ) as f:
            f.write(scxml_model.as_xml_string(data_type_as_attribute=False))


def interpret_top_level_xml(
    xml_path: str, jani_file: str, generated_scxmls_dir: Optional[str] = None
):
    """
    Interpret the top-level XML file as a Jani model. And write it to a file.
    The generated Jani model is written to the same directory as the input XML file under the
    name `main.jani`.

    :param xml_path: The path to the XML file to interpret.
    :param jani_file: The path to the output Jani file.
    :param generated_scxmls_dir: The directory to store the generated plain SCXML files.
    """
    model_dir = os.path.dirname(xml_path)
    model = parse_main_xml(xml_path)

    custom_data_types: Dict[str, XmlStructDefinition] = {}
    for path in model.data_declarations:
        loaded_structs = read_types_file(path)
        loaded_structs_dict = {
            single_struct.get_name(): single_struct for single_struct in loaded_structs
        }
        custom_data_types.update(loaded_structs_dict)

    for custom_struct_instance in custom_data_types.values():
        custom_struct_instance.expand_members(custom_data_types)

    plain_scxml_models = generate_plain_scxml_models_and_timers(model, custom_data_types)

    if generated_scxmls_dir is not None:
        plain_scxml_dir = os.path.join(model_dir, generated_scxmls_dir)
        export_plain_scxml_models(plain_scxml_dir, plain_scxml_models)

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
        json.dump(jani_model.as_dict(), f, indent=2, ensure_ascii=False)
