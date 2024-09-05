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
Facilitation conversion between SCXML flavors.

This module provides functionalities to convert the ROS-specific macros
into generic SCXML code.
"""

from typing import Dict, Union

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


# # TODO: Unused, keeping as reference to output types in low level SCXML
# def _check_topic_type(
#         name: str,
#         type_dict: dict,
#         this_topic: str,
#         cb_topic: str,
#         expr: str):
#     """Check if the field type is correct.

#     It matches the expression type with the type declared for the given
#     publisher or subscriber.

#     :param name: The name of the field.
#     :param type_dict: The type dictionary of the topic.
#     :param expr: The ecmascript expression to check.
#     :throws: ConversionStaticAnalysisError if the type is incorrect.
#     """
#     if name not in type_dict:
#         raise ConversionStaticAnalysisError(
#             f"Field {name} not found in the type dictionary {type_dict}")
#     expected_ros_type = type_dict[this_topic][name]
#     expected_python_type = ros_type_name_to_python_type(expected_ros_type)
#     expression_value = interpret_ecma_script_expr(expr)
#     expression_type = type(expression_value)
#     if expression_type != expected_python_type:
#         raise ConversionStaticAnalysisError(
#             f"Field {name} has type {expression_type}, " +
#             f"expected {expected_python_type}")
