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
Facilitation conversion between ScXML flavors.

This module provides functionalities to convert the ROS-specific macros
into generic ScXML code.
"""

import xml.etree.ElementTree as ET
from copy import deepcopy
from typing import Dict, List, Tuple, Union

from mc_toolchain_jani_common.common import (ValidTypes, remove_namespace,
                                          ros_type_name_to_python_type)
from mc_toolchain_jani_common.ecmascript_interpretation import \
    interpret_ecma_script_expr

BASIC_FIELD_TYPES = ['boolean', 'int32', 'int16', 'float', 'double']

ROS_TIMER_RATE_EVENT_PREFIX = 'ros_time_rate.'


class ConversionStaticAnalysisError(Exception):
    """Error raised when a static analysis fails."""
    pass


def _is_basic_field_type(field_name: str) -> bool:
    """Check if a field type is a basic ROS field type.

    :param field_name: The field type to check.
    :return: True if the field type is a basic ROS field type.
    """
    return field_name in BASIC_FIELD_TYPES


def _ros_type_fields(type_str: str) -> Dict[str, Union[str, dict]]:
    """Get the fields of a ROS message type.

    This function imports the message type and returns a dictionary
    containing the fields and their types.

    :param type_str: The ROS message type string. (e.g. std_msgs/String)
    :return: A dictionary containing the fields and their types.
    """
    pkg_and_msg_list = type_str.split('/')
    pkg_name = pkg_and_msg_list[0]
    msg_type = pkg_and_msg_list[1]
    pkg_msgs = __import__(pkg_name + '.msg', fromlist=[msg_type])
    msg_fields = getattr(pkg_msgs, msg_type).get_fields_and_field_types()
    msg_fields_names = list(msg_fields.keys())
    for key in msg_fields_names:
        field_type = msg_fields[key]
        if not _is_basic_field_type(field_type):
            msg_subfields = _ros_type_fields(field_type)
            for subfield_name, subfield_type in msg_subfields.items():
                msg_fields[key + '.' + subfield_name] = subfield_type
            del msg_fields[key]
    return msg_fields


def _check_topic_type(
        name: str,
        type_dict: dict,
        this_topic: str,
        cb_topic: str,
        expr: str):
    """Check if the field type is correct.

    It matches the expression type with the type declared for the given
    publisher or subscriber.

    :param name: The name of the field.
    :param type_dict: The type dictionary of the topic.
    :param expr: The ecmascript expression to check.
    :throws: ConversionStaticAnalysisError if the type is incorrect.
    """
    if name not in type_dict:
        raise ConversionStaticAnalysisError(
            f"Field {name} not found in the type dictionary {type_dict}")
    expected_ros_type = type_dict[this_topic][name]
    expected_python_type = ros_type_name_to_python_type(expected_ros_type)
    expression_value = interpret_ecma_script_expr(expr)
    expression_type = type(expression_value)
    if expression_type != expected_python_type:
        raise ConversionStaticAnalysisError(
            f"Field {name} has type {expression_type}, " +
            f"expected {expected_python_type}")


def convert_elem(elem: ET.Element,
                 parent_map: Dict[ET.Element, ET.Element],
                 type_per_topic: Dict[str, dict],
                 subscribed_topics: list,
                 published_topics: list,
                 timers: Dict[str, float],
                 timer_count: Dict[str, int]
                 ) -> bool:
    """Convert an element from the ScXML file.

    This takes ROS-specific elements and converts them into generic ScXML
    elements.

    :param elem: The element to convert.
    :param parent_map: The parent map of the element.
    :param type_per_topic: The types of the topics.
    :param subscribed_topics: The list of subscribed topics.
    :param published_topics: The list of published topics.
    :param timers: The list of timers.
    :return: True if the element should be deleted.
    """
    tag_wo_ns = remove_namespace(elem.tag)

    # Declaration of publisher and subscriber #################################
    if tag_wo_ns == 'ros_topic_publisher':
        imported_type = _ros_type_fields(elem.attrib['type'])
        type_per_topic[elem.attrib['topic']] = imported_type
        published_topics.append(elem.attrib['topic'])
        # TODO
        return True
    if tag_wo_ns == 'ros_topic_subscriber':
        imported_type = _ros_type_fields(elem.attrib['type'])
        type_per_topic[elem.attrib['topic']] = imported_type
        subscribed_topics.append(elem.attrib['topic'])
        # TODO
        return True

    # Publish #################################################################
    if tag_wo_ns == 'ros_publish':
        assert elem.attrib['topic'] in type_per_topic
        assert elem.attrib['topic'] in published_topics
        elem.tag = 'send'
        event_name = f"ros_topic.{elem.attrib['topic']}"
        elem.attrib.pop('topic')
        elem.attrib['event'] = event_name
        return False
    if tag_wo_ns == 'field':
        topic = parent_map[elem].attrib['event'].replace('ros_topic.', '')
        try:
            cb_topic = parent_map[parent_map[elem]].attrib['topic']
        except KeyError:
            cb_topic = None
        assert topic in type_per_topic
        assert topic in published_topics
        # TODO: IMPLEMENT:
        # _check_topic_type(
        #     elem.attrib['name'],
        #     type_per_topic,
        #     topic,
        #     cb_topic,
        #     elem.attrib['expr'])
        elem.tag = 'param'
        expr_attr = elem.attrib['expr']
        elem.attrib['expr'] = expr_attr.replace('_msg', '_event')
        return False

    # Callback ################################################################
    if tag_wo_ns == 'ros_callback':
        assert elem.attrib['topic'] in type_per_topic
        assert elem.attrib['topic'] in subscribed_topics
        elem.tag = 'transition'
        event_name = f"ros_topic.{elem.attrib['topic']}"
        elem.attrib.pop('topic')
        elem.attrib['event'] = event_name
        # check children for assignments that may need to change _msg to _event
        for child in elem:
            if remove_namespace(child.tag) == 'assign':
                if 'expr' not in child.attrib:
                    continue
                expr_attr = child.attrib['expr']
                child.attrib['expr'] = expr_attr.replace('_msg', '_event')
            # TODO: are there other tags that need to be checked?
        return False

    # Timer ###################################################################
    if tag_wo_ns == 'ros_time_rate':
        name = elem.attrib['name']
        assert name not in timers, f"Timer {name} already exists."
        timers[name] = float(elem.attrib['rate_hz'])
        assert name not in timer_count, f"Timer {name} already exists."
        timer_count[name] = 0
        return True
    if tag_wo_ns == 'ros_rate_callback':
        elem.tag = 'transition'
        assert elem.attrib['name'] in timers
        assert elem.attrib['name'] in timer_count
        timer_count[elem.attrib['name']] += 1
        event_name = f"{ROS_TIMER_RATE_EVENT_PREFIX}{elem.attrib['name']}"
        elem.attrib.pop('name')
        elem.attrib['event'] = event_name
        return False

    return False


def scxml_converter(input_xml: str) -> Tuple[str, List[Tuple[str, float]]]:
    """Convert one ScXML file that contains ROS-specific tags.

    :param input_file: The input ScXML file.
    :return: The converted ScXML and the timers as a list of tuples.
             Each tuple contains the timer name and the rate in Hz.
    """
    ET.register_namespace('', 'http://www.w3.org/2005/07/scxml')
    try:
        tree = ET.fromstring(input_xml)
    except ET.ParseError as e:
        print(">>>>")
        print(input_xml)
        print(">>>>")
        raise ValueError(f"Error parsing XML: {e}")    
    type_per_topic = {}
    subscribed_topics = []
    published_topics = []
    timers = {}
    timer_count = {}
    parent_map = {child: parent
                  for parent in tree.iter() for child in parent}
    for elem in list(tree.iter()):
        delete = convert_elem(
            elem,
            parent_map,
            type_per_topic,
            subscribed_topics,
            published_topics,
            timers,
            timer_count,
        )
        if delete:
            tree.remove(elem)
    return ET.tostring(tree, encoding='unicode'), timers.items()
