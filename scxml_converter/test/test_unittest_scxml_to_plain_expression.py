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

""""Test the SCXML data conversion from all possible declaration types"""

from typing import List
from scxml_converter.scxml_entries.utils import CallbackType, get_plain_expression

import pytest


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
        "_event.data",
        "x + y + z == _msg.data",
        "_action.goal_id == 0",
        "x + y + z == 0 && _event.data == 1"
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
        "_msg.array_entry[_msg.index] == _msg.index"
    ]
    expected_expressions: List[str] = [
        "_event.ros_fields__data == 1",
        "cos(_event.ros_fields__data) == 1.0",
        "some_msg.data + _event.ros_fields__count",
        "_event.ros_fields__x<1 && sin(_event.ros_fields__angle.x+_event.ros_fields__angle.y)>2",
        "_event.ros_fields__array_entry[_event.ros_fields__index] == _event.ros_fields__index"
    ]
    for test_expr, gt_expr in zip(ok_expressions, expected_expressions):
        conv_expr = get_plain_expression(test_expr, CallbackType.ROS_TOPIC)
        assert conv_expr == gt_expr


def test_topic_bad_expressions():
    bad_expressions: List[str] = [
        "_event.data",
        "x + _res.y + z == _msg.data",
        "_action.goal_id == 0",
        "_wrapped_result.code == 1"
    ]
    for expr in bad_expressions:
        with pytest.raises(AssertionError):
            get_plain_expression(expr, CallbackType.ROS_TOPIC)
            print(f"Expression '{expr}' should raise.")
