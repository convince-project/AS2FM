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

from typing import List, Optional

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


def interpret_top_level_xml(xml_path: str) -> JaniModel:
    """
    Interpret the top-level XML file as a Jani model.

    :param xml_path: The path to the XML file to interpret.
    :return: The interpreted Jani model.
    """
    folder_of_xml = os.path.dirname(xml_path)
    with open(xml_path, 'r', encoding='utf-8') as f:
        xml = ET.parse(f)
    assert remove_namespace(xml.getroot().tag) == "convince_mc_tc", \
        "The top-level XML element must be convince_mc_tc."

    scxml_files_to_convert = []
    bt: Optional[str] = None  # The path to the Behavior Tree definition

    for first_level in xml.getroot():
        if remove_namespace(first_level.tag) == "mc_parameters":
            for mc_parameter in first_level:
                # if remove_namespace(mc_parameter.tag) == "time_resolution":
                #     time_resolution = _parse_time_element(mc_parameter)
                if remove_namespace(mc_parameter.tag) == "max_time":
                    max_time_ns = _parse_time_element(mc_parameter)
                else:
                    raise ValueError(
                        f"Invalid mc_parameter tag: {mc_parameter.tag}")
        elif remove_namespace(first_level.tag) == "behavior_tree":
            plugins = []
            for child in first_level:
                if remove_namespace(child.tag) == "input":
                    if child.attrib["type"] == "bt.cpp-xml":
                        assert bt is None, "Only one BT is supported."
                        bt = child.attrib["src"]
                    elif child.attrib["type"] == "bt-plugin-ros-scxml":
                        plugins.append(child.attrib["src"])
                    else:
                        raise ValueError(
                            f"Invalid input tag type: {child.attrib['type']}")
                else:
                    raise ValueError(
                        f"Invalid behavior_tree tag: {child.tag}")
            assert bt is not None, "There must be a Behavior Tree defined."
        elif remove_namespace(first_level.tag) == "node_models":
            for node_model in first_level:
                assert remove_namespace(node_model.tag) == "input", \
                    "Only input tags are supported."
                assert node_model.attrib['type'] == "ros-scxml", \
                    "Only ROS-SCXML node models are supported."
                scxml_files_to_convert.append(
                    os.path.join(folder_of_xml, node_model.attrib["src"]))
        elif remove_namespace(first_level.tag) == "properties":
            properties = []
            for property in first_level:
                assert remove_namespace(property.tag) == "input", \
                    "Only input tags are supported."
                assert property.attrib['type'] == "jani", \
                    "Only Jani properties are supported."
                properties.append(property.attrib["src"])
        else:
            raise ValueError(f"Invalid main point tag: {first_level.tag}")

    # Preprocess behavior tree and plugins
    if bt is not None:
        bt_path = os.path.join(folder_of_xml, bt)
        plugin_paths = []
        for plugin in plugins:
            plugin_paths.append(os.path.join(folder_of_xml, plugin))
        output_folder = folder_of_xml  # TODO: Think about better folder structure
        scxml_files = bt_converter(bt_path, plugin_paths, output_folder)
        scxml_files_to_convert.extend(scxml_files)

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

    jani_model = convert_multiple_scxmls_to_jani(
        plain_scxml_models, all_timers, max_time_ns)

    jani_dict = jani_model.as_dict()
    assert len(properties) == 1, "Only one property is supported right now."
    with open(os.path.join(folder_of_xml, properties[0]),
              "r", encoding='utf-8') as f:
        jani_dict["properties"] = json.load(f)["properties"]

    output_path = os.path.join(folder_of_xml, "main.jani")
    with open(output_path, "w", encoding='utf-8') as f:
        json.dump(jani_dict, f, indent=2, ensure_ascii=False)
