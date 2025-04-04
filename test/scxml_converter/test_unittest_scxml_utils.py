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

"""Test the SCXML data conversion from all possible declaration types"""

from typing import List, MutableSequence

import pytest

from as2fm.scxml_converter.scxml_entries.utils import (
    PLAIN_FIELD_EVENT_PREFIX,
    PLAIN_SCXML_EVENT_DATA_PREFIX,
    CallbackType,
    get_plain_expression,
)
from as2fm.scxml_converter.xml_data_types.type_utils import get_data_type_from_string


def test_standard_good_expressions():
    """Test expressions that have no events at all (e.g. from state entries)."""
    ok_expressions: List[str] = [
        "1 + 1 == 2",
        "variable_1 + cos(3.14)",
        "sin(x.data) + 1.4",
        "cos(x+y+z) > 0 && sin(z - y) <= 0",
    ]
    for expr in ok_expressions:
        conv_expr = get_plain_expression(expr, CallbackType.STATE)
        assert conv_expr == expr


def test_standard_bad_expressions():
    """Test expressions that have events in them, which are not allowed in state entries."""
    bad_expressions: List[str] = [
        f"{PLAIN_SCXML_EVENT_DATA_PREFIX}data",
        "x + y + z == _msg.data",
        "_action.goal_id == 0",
        f"x + y + z == 0 && {PLAIN_SCXML_EVENT_DATA_PREFIX}data == 1",
    ]
    for expr in bad_expressions:
        with pytest.raises(AssertionError):
            get_plain_expression(expr, CallbackType.STATE)
            print(f"Expression '{expr}' should raise.")


def test_topic_good_expressions():
    """Test expressions that have events related to topics."""
    ok_expressions: List[str] = [
        "_msg.data == 1",
        "cos(_msg.data) == 1.0",
        "some_msg.data + _msg.count",
        "_msg.x<1 && sin(_msg.angle.x+_msg.angle.y)>2",
        "_msg.array_entry[_msg.index] == _msg.index",
    ]
    expected_expressions: List[str] = [
        f"{PLAIN_FIELD_EVENT_PREFIX}data == 1",
        f"cos({PLAIN_FIELD_EVENT_PREFIX}data) == 1.0",
        f"some_msg.data + {PLAIN_FIELD_EVENT_PREFIX}count",
        f"{PLAIN_FIELD_EVENT_PREFIX}x<1 && sin({PLAIN_FIELD_EVENT_PREFIX}angle.x+"
        + f"{PLAIN_FIELD_EVENT_PREFIX}angle.y)>2",
        f"{PLAIN_FIELD_EVENT_PREFIX}array_entry[{PLAIN_FIELD_EVENT_PREFIX}index] == "
        + f"{PLAIN_FIELD_EVENT_PREFIX}index",
    ]
    for test_expr, gt_expr in zip(ok_expressions, expected_expressions):
        conv_expr = get_plain_expression(test_expr, CallbackType.ROS_TOPIC)
        assert conv_expr == gt_expr


def test_topic_bad_expressions():
    """Test expressions that have events in them, which are not allowed in topic entries."""
    bad_expressions: List[str] = [
        f"{PLAIN_SCXML_EVENT_DATA_PREFIX}data",
        "x + _res.y + z == _msg.data",
        "_action.goal_id == 0",
        "_wrapped_result.code == 1",
    ]
    for expr in bad_expressions:
        with pytest.raises(AssertionError):
            get_plain_expression(expr, CallbackType.ROS_TOPIC)
            print(f"Expression '{expr}' should raise.")


def test_action_goal_good_expressions():
    """Test expressions that have events related to actions."""
    ok_expressions: List[str] = ["some_action.goal_id", "_action.goal_id", "_goal.x < 1"]
    expected_expressions: List[str] = [
        "some_action.goal_id",
        f"{PLAIN_SCXML_EVENT_DATA_PREFIX}goal_id",
        f"{PLAIN_FIELD_EVENT_PREFIX}x < 1",
    ]
    for test_expr, gt_expr in zip(ok_expressions, expected_expressions):
        conv_expr = get_plain_expression(test_expr, CallbackType.ROS_ACTION_GOAL)
        assert conv_expr == gt_expr


def test_action_feedback_good_expressions():
    """Test expressions that have events related to actions."""
    ok_expressions: List[str] = [
        "cos(_feedback.angle.x) == 1.0",
        "some_action.goal_id",
        "_action.goal_id",
    ]
    expected_expressions: List[str] = [
        f"cos({PLAIN_FIELD_EVENT_PREFIX}angle.x) == 1.0",
        "some_action.goal_id",
        f"{PLAIN_SCXML_EVENT_DATA_PREFIX}goal_id",
    ]
    for test_expr, gt_expr in zip(ok_expressions, expected_expressions):
        conv_expr = get_plain_expression(test_expr, CallbackType.ROS_ACTION_FEEDBACK)
        assert conv_expr == gt_expr


def test_action_result_good_expressions():
    """Test expressions that have events related to actions."""
    ok_expressions: List[str] = [
        "_wrapped_result.code == 1",
        "cos(_wrapped_result.result.angle) == 0.0",
        "some_action.goal_id",
        "_action.goal_id",
    ]
    expected_expressions: List[str] = [
        f"{PLAIN_SCXML_EVENT_DATA_PREFIX}code == 1",
        f"cos({PLAIN_FIELD_EVENT_PREFIX}angle) == 0.0",
        "some_action.goal_id",
        f"{PLAIN_SCXML_EVENT_DATA_PREFIX}goal_id",
    ]
    for test_expr, gt_expr in zip(ok_expressions, expected_expressions):
        conv_expr = get_plain_expression(test_expr, CallbackType.ROS_ACTION_RESULT)
        assert conv_expr == gt_expr


def test_type_string_conversion():
    """Test the various types string are converted to the expected value."""
    # Test expected array types
    type_strings_ok = [
        ("float64", float),
        ("int32", int),
        ("bool", bool),
        ("float64[]", MutableSequence[float]),
        ("int32[]", MutableSequence[int]),
        ("int8[]", MutableSequence[int]),
        ("float64[4]", MutableSequence[float]),
        ("int32[10]", MutableSequence[int]),
        ("int8[01]", MutableSequence[int]),
    ]
    for type_str, gt_type in type_strings_ok:
        conv_type = get_data_type_from_string(type_str)
        assert conv_type == gt_type
    # Test unexpected array types
    type_strings_fail = [
        "float64[-4]",
    ]
    for type_str in type_strings_fail:
        with pytest.raises(KeyError):
            get_data_type_from_string(type_str)
