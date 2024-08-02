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

import os
import json

from typing import Any, Dict, List, Tuple

from xml.etree import ElementTree as ET

from as2fm_common.common import remove_namespace
from scxml_converter.bt_converter import bt_converter
from scxml_converter.scxml_entries import ScxmlRoot
from jani_generator.jani_entries import JaniModel
from jani_generator.ros_helpers.ros_timer import RosTimer
from jani_generator.ros_helpers.ros_services import RosServices, RosService
from jani_generator.scxml_helpers.scxml_to_jani import convert_multiple_scxmls_to_jani


def _parse_time_element(time_element: ET.Element) -> int:
    """
    Interpret a time element. Output is in nanoseconds.

    :param time_element: The time element to interpret.
    :return: The interpreted time in nanoseconds.
    """
    TIME_MULTIPLIERS = {
        "s": 1_000_000_000,
        "ms": 1_000_000,
        "us": 1_000,
        "ns": 1
    }
    time_unit = time_element.attrib["unit"]
    assert time_unit in TIME_MULTIPLIERS, f"Invalid time unit: {time_unit}"
    return int(time_element.attrib["value"]) * TIME_MULTIPLIERS[time_unit]


def parse_main_xml(xml_path: str) -> Dict[str, Any]:
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
    with open(xml_path, 'r', encoding='utf-8') as f:
        xml = ET.parse(f)
    assert remove_namespace(xml.getroot().tag) == "convince_mc_tc", \
        "The top-level XML element must be convince_mc_tc."
    main_dict = {
        "max_time": None,
        "bt": None,
        "plugins": [],
        "skills": [],
        "components": [],
        "properties": []
    }
    for first_level in xml.getroot():
        if remove_namespace(first_level.tag) == "mc_parameters":
            for mc_parameter in first_level:
                # if remove_namespace(mc_parameter.tag) == "time_resolution":
                #     time_resolution = _parse_time_element(mc_parameter)
                if remove_namespace(mc_parameter.tag) == "max_time":
                    main_dict["max_time"] = _parse_time_element(mc_parameter)
                else:
                    raise ValueError(
                        f"Invalid mc_parameter tag: {mc_parameter.tag}")
        elif remove_namespace(first_level.tag) == "behavior_tree":
            for child in first_level:
                if remove_namespace(child.tag) == "input":
                    if child.attrib["type"] == "bt.cpp-xml":
                        assert main_dict["bt"] is None, "Only one BT is supported."
                        main_dict["bt"] = os.path.join(folder_of_xml, child.attrib["src"])
                    elif child.attrib["type"] == "bt-plugin-ros-scxml":
                        main_dict["plugins"].append(
                            os.path.join(folder_of_xml, child.attrib["src"]))
                    else:
                        raise ValueError(f"Invalid input type: {child.attrib['type']}")
                else:
                    raise ValueError(
                        f"Invalid behavior_tree tag: {child.tag} != input")
            assert main_dict["bt"] is not None, "There must be a Behavior Tree defined."
        elif remove_namespace(first_level.tag) == "node_models":
            for node_model in first_level:
                assert remove_namespace(node_model.tag) == "input", \
                    "Only input tags are supported."
                assert node_model.attrib["type"] == "ros-scxml", \
                    "Only ROS-SCXML node models are supported."
                main_dict["skills"].append(os.path.join(folder_of_xml, node_model.attrib["src"]))
        elif remove_namespace(first_level.tag) == "properties":
            for property in first_level:
                assert remove_namespace(property.tag) == "input", \
                    "Only input tags are supported."
                assert property.attrib["type"] == "jani", \
                    "Only Jani properties are supported."
                main_dict["properties"].append(os.path.join(folder_of_xml, property.attrib["src"]))
        else:
            raise ValueError(f"Invalid main point tag: {first_level.tag}")
    return main_dict


def generate_plain_scxml_models_and_timers(
        full_model_dict: str) -> Tuple[List[ScxmlRoot], List[RosTimer]]:
    """
    Generate plain SCXML models and ROS timers from the full model dictionary.
    """
    # Convert behavior tree and plugins to ROS-scxml
    scxml_files_to_convert: list = full_model_dict["skills"] + full_model_dict["components"]
    if full_model_dict["bt"] is not None:
        bt_out_dir = os.path.join(os.path.dirname(full_model_dict["bt"]), "generated_bt_scxml")
        os.makedirs(bt_out_dir, exist_ok=True)
        expanded_bt_plugin_scxmls = bt_converter(
            full_model_dict["bt"], full_model_dict["plugins"], bt_out_dir)
        scxml_files_to_convert.extend(expanded_bt_plugin_scxmls)

    # Convert ROS-SCXML FSMs to plain SCXML
    plain_scxml_models = []
    all_timers: List[RosTimer] = []
    all_services: RosServices = {}
    for fname in scxml_files_to_convert:
        plain_scxml, ros_declarations = \
            ScxmlRoot.from_scxml_file(fname).to_plain_scxml_and_declarations()
        # Handle ROS timers
        for timer_name, timer_rate in ros_declarations._timers.items():
            assert timer_name not in all_timers, \
                f"Timer {timer_name} already exists."
            all_timers.append(RosTimer(timer_name, timer_rate))
        # Handle ROS Services
        for service_name, service_type in ros_declarations._service_clients.items():
            if service_name not in all_services:
                all_services[service_name] = RosService()
            all_services[service_name].append_service_client(
                service_name, service_type, plain_scxml.get_name())
        for service_name, service_type in ros_declarations._service_servers.items():
            if service_name not in all_services:
                all_services[service_name] = RosService()
            all_services[service_name].set_service_server(
                service_name, service_type, plain_scxml.get_name())
        plain_scxml_models.append(plain_scxml)
    # Generate service sync SCXML models
    for service_info in all_services.values():
        plain_scxml_models.append(service_info.to_scxml())
    return plain_scxml_models, all_timers


def interpret_top_level_xml(xml_path: str, store_generated_scxmls: bool = False) -> JaniModel:
    """
    Interpret the top-level XML file as a Jani model.

    :param xml_path: The path to the XML file to interpret.
    :return: The interpreted Jani model.
    """
    model_dir = os.path.dirname(xml_path)
    full_model_dict = parse_main_xml(xml_path)
    assert full_model_dict["max_time"] is not None, f"Max time must be defined in {xml_path}."
    plain_scxml_models, all_timers = generate_plain_scxml_models_and_timers(full_model_dict)

    if store_generated_scxmls:
        plain_scxml_dir = os.path.join(model_dir, "generated_plain_scxml")
        os.makedirs(plain_scxml_dir, exist_ok=True)
        for scxml_model in plain_scxml_models:
            with open(os.path.join(plain_scxml_dir, f"{scxml_model.get_name()}.scxml"), "w",
                      encoding='utf-8') as f:
                f.write(scxml_model.as_xml_string())

    jani_model = convert_multiple_scxmls_to_jani(
        plain_scxml_models, all_timers, full_model_dict["max_time"])

    jani_dict = jani_model.as_dict()
    assert len(full_model_dict["properties"]) == 1, "Only one property is supported right now."
    with open(full_model_dict["properties"][0], "r", encoding='utf-8') as f:
        jani_dict["properties"] = json.load(f)["properties"]

    output_path = os.path.join(model_dir, "main.jani")
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(jani_dict, f, indent=2, ensure_ascii=False)
