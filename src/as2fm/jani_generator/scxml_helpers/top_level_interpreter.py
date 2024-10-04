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
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from lxml import etree as ET

from as2fm.as2fm_common.common import is_comment, remove_namespace
from as2fm.as2fm_common.logging import AS2FMLogger
from as2fm.jani_generator.ros_helpers.ros_action_handler import RosActionHandler
from as2fm.jani_generator.ros_helpers.ros_communication_handler import (
    RosCommunicationHandler,
    generate_plain_scxml_from_handlers,
    update_ros_communication_handlers,
)
from as2fm.jani_generator.ros_helpers.ros_service_handler import RosServiceHandler
from as2fm.jani_generator.ros_helpers.ros_timer import RosTimer, make_global_timer_scxml
from as2fm.jani_generator.scxml_helpers.scxml_to_jani import convert_multiple_scxmls_to_jani
from as2fm.scxml_converter.bt_converter import bt_converter
from as2fm.scxml_converter.scxml_entries import ScxmlRoot


@dataclass()
class FullModel:
    max_time: Optional[int] = None
    max_array_size: int = field(default=100)
    bt_tick_rate: float = field(default=1.0)
    bt: Optional[str] = None
    plugins: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    properties: List[str] = field(default_factory=list)


def _parse_time_element(time_element: ET.Element) -> int:
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
    Interpret the top-level XML file as a dictionary.

    The returned dictionary contains the following keys:
    - max_time: The maximum time in nanoseconds.
    - bt: The path to the Behavior Tree definition.
    - plugins: A list of paths to the Behavior Tree plugins.
    - skills: A list of paths to SCXML files encoding an FSM.
    - components: Similar to skills, but representing abstract models of existing skills
    - properties: A list of paths to Jani properties.
    """
    # Used to generate absolute paths of scxml models
    folder_of_xml = os.path.dirname(xml_path)
    with open(xml_path, "r", encoding="utf-8") as f:
        xml = ET.parse(f)
    logger = AS2FMLogger(xml_path)
    assert remove_namespace(xml.getroot().tag) == "convince_mc_tc", logger.error(
        xml.getroot(), "The top-level XML element must be convince_mc_tc."
    )
    model = FullModel()
    for first_level in xml.getroot():
        if is_comment(first_level):
            continue
        if remove_namespace(first_level.tag) == "mc_parameters":
            for mc_parameter in first_level:
                if is_comment(mc_parameter):
                    continue
                # if remove_namespace(mc_parameter.tag) == "time_resolution":
                #     time_resolution = _parse_time_element(mc_parameter)
                if remove_namespace(mc_parameter.tag) == "max_time":
                    model.max_time = _parse_time_element(mc_parameter)
                elif remove_namespace(mc_parameter.tag) == "max_array_size":
                    model.max_array_size = int(mc_parameter.attrib["value"])
                elif remove_namespace(mc_parameter.tag) == "bt_tick_rate":
                    model.bt_tick_rate = float(mc_parameter.attrib["value"])
                else:
                    raise ValueError(
                        logger.error(mc_parameter, f"Invalid mc_parameter tag: {mc_parameter.tag}")
                    )
        elif remove_namespace(first_level.tag) == "behavior_tree":
            for child in first_level:
                if is_comment(child):
                    continue
                if remove_namespace(child.tag) == "input":
                    if child.attrib["type"] == "bt.cpp-xml":
                        assert model.bt is None, "Only one Behavior Tree is supported."
                        model.bt = os.path.join(folder_of_xml, child.attrib["src"])
                    elif child.attrib["type"] == "bt-plugin-ros-scxml":
                        model.plugins.append(os.path.join(folder_of_xml, child.attrib["src"]))
                    else:
                        raise ValueError(
                            logger.error(child, f"Invalid input type: {child.attrib['type']}")
                        )
                else:
                    raise ValueError(logger.error(child, f"Invalid behavior_tree tag: {child.tag}"))
            assert model.bt is not None, "A Behavior Tree must be defined."
        elif remove_namespace(first_level.tag) == "node_models":
            for node_model in first_level:
                if is_comment(node_model):
                    continue
                assert remove_namespace(node_model.tag) == "input", logger.error(
                    node_model, "Only input tags are supported."
                )
                assert node_model.attrib["type"] == "ros-scxml", logger.error(
                    node_model, "Only ROS-SCXML models are supported."
                )
                model.skills.append(os.path.join(folder_of_xml, node_model.attrib["src"]))
        elif remove_namespace(first_level.tag) == "properties":
            for prop in first_level:
                if is_comment(prop):
                    continue
                assert remove_namespace(prop.tag) == "input", logger.error(
                    prop, "Only input tags are supported."
                )
                assert prop.attrib["type"] == "jani", logger.error(
                    prop, "Only Jani properties are supported."
                )
                model.properties.append(os.path.join(folder_of_xml, prop.attrib["src"]))
        else:
            raise ValueError(logger.error(first_level, f"Invalid top-level tag: {first_level.tag}"))
    return model


def generate_plain_scxml_models_and_timers(
    model: FullModel,
) -> Tuple[List[ScxmlRoot], List[RosTimer]]:
    """
    Generate plain SCXML models and ROS timers from the full model dictionary.
    """
    # Load the skills and components scxml files (ROS-SCXML)
    scxml_files_to_convert: list = model.skills + model.components
    ros_scxmls: List[ScxmlRoot] = []
    for fname in scxml_files_to_convert:
        ros_scxmls.append(ScxmlRoot.from_scxml_file(fname))
    # Convert behavior tree and plugins to ROS-SCXML
    if model.bt is not None:
        ros_scxmls.extend(bt_converter(model.bt, model.plugins, model.bt_tick_rate))
    # Convert the loaded entries to plain SCXML
    plain_scxml_models = []
    all_timers: List[RosTimer] = []
    all_services: Dict[str, RosCommunicationHandler] = {}
    all_actions: Dict[str, RosCommunicationHandler] = {}
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
    # Generate sync SCXML models for services and actions
    for plain_scxml in generate_plain_scxml_from_handlers(all_services | all_actions):
        plain_scxml_models.append(plain_scxml)
    return plain_scxml_models, all_timers


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
    assert model.max_time is not None, f"Max time must be defined in {xml_path}."
    plain_scxml_models, all_timers = generate_plain_scxml_models_and_timers(model)

    if generated_scxmls_dir is not None:
        plain_scxml_dir = os.path.join(model_dir, generated_scxmls_dir)
        os.makedirs(plain_scxml_dir, exist_ok=True)
        for scxml_model in plain_scxml_models:
            with open(
                os.path.join(plain_scxml_dir, f"{scxml_model.get_name()}.scxml"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(scxml_model.as_xml_string())
        # Additionally, write the timers SCXML model
        global_timer_scxml = make_global_timer_scxml(all_timers, model.max_time)
        if global_timer_scxml is not None:
            with open(
                os.path.join(plain_scxml_dir, global_timer_scxml.get_name() + ".scxml"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write(global_timer_scxml.as_xml_string())

    jani_model = convert_multiple_scxmls_to_jani(
        plain_scxml_models, all_timers, model.max_time, model.max_array_size
    )

    jani_dict = jani_model.as_dict()
    assert len(model.properties) == 1, f"Only one property is supported right now in {xml_path}."
    with open(model.properties[0], "r", encoding="utf-8") as f:
        jani_dict["properties"] = json.load(f)["properties"]

    output_path = os.path.join(model_dir, jani_file)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(jani_dict, f, indent=2, ensure_ascii=False)
