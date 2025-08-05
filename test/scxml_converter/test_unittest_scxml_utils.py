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

from typing import List, MutableSequence, Tuple

import pytest

from as2fm.scxml_converter.data_types.type_utils import get_data_type_from_string
from as2fm.scxml_converter.data_types.xml_struct_definition import XmlStructDefinition
from as2fm.scxml_converter.scxml_entries import ScxmlData, ScxmlDataModel
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    PLAIN_FIELD_EVENT_PREFIX,
    PLAIN_SCXML_EVENT_DATA_PREFIX,
    CallbackType,
    convert_expression_with_object_arrays,
    convert_expression_with_string_literals,
    get_plain_expression,
)


def test_standard_good_expressions():
    """Test expressions that have no events at all (e.g. from state entries)."""
    test_expressions: List[Tuple[str, str]] = [
        ("1 + 1 == 2", "1 + 1 == 2"),
        ("variable_1 + cos(3.14)", "variable_1 + cos(3.14)"),
        ("sin(x.data) + 1.4", "sin(x__data) + 1.4"),
        ("cos(x+y+z) > 0 && sin(z - y) <= 0", "cos(x + y + z) > 0 && sin(z - y) <= 0"),
    ]
    for in_expr, gt_expr in test_expressions:
        conv_expr = get_plain_expression(in_expr, CallbackType.STATE, None)
        assert conv_expr == gt_expr


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
            get_plain_expression(expr, CallbackType.STATE, None)
            print(f"Expression '{expr}' should raise.")


def test_topic_good_expressions():
    """Test expressions that have events related to topics."""
    test_expressions: List[str] = [
        "_msg.data == 1",
        "cos(_msg.data) == 1.0",
        "some_msg.data + _msg.count",
        "_msg.x<1 && sin(_msg.angle.x+_msg.angle.y)>2",
        "_msg.array_entry[_msg.index] == _msg.index",
    ]
    expected_expressions: List[str] = [
        f"{PLAIN_FIELD_EVENT_PREFIX}data == 1",
        f"cos({PLAIN_FIELD_EVENT_PREFIX}data) == 1",
        f"some_msg__data + {PLAIN_FIELD_EVENT_PREFIX}count",
        f"{PLAIN_FIELD_EVENT_PREFIX}x < 1 && sin({PLAIN_FIELD_EVENT_PREFIX}angle__x + "
        + f"{PLAIN_FIELD_EVENT_PREFIX}angle__y) > 2",
        f"{PLAIN_FIELD_EVENT_PREFIX}array_entry[{PLAIN_FIELD_EVENT_PREFIX}index] == "
        + f"{PLAIN_FIELD_EVENT_PREFIX}index",
    ]
    for test_expr, gt_expr in zip(test_expressions, expected_expressions):
        conv_expr = get_plain_expression(test_expr, CallbackType.ROS_TOPIC, None)
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
            get_plain_expression(expr, CallbackType.ROS_TOPIC, None)
            print(f"Expression '{expr}' should raise.")


def test_action_goal_good_expressions():
    """Test expressions that have events related to actions."""
    ok_expressions: List[str] = ["some_action.goal_id", "_action.goal_id", "_goal.x < 1"]
    expected_expressions: List[str] = [
        "some_action__goal_id",
        f"{PLAIN_SCXML_EVENT_DATA_PREFIX}goal_id",
        f"{PLAIN_FIELD_EVENT_PREFIX}x < 1",
    ]
    for test_expr, gt_expr in zip(ok_expressions, expected_expressions):
        conv_expr = get_plain_expression(test_expr, CallbackType.ROS_ACTION_GOAL, None)
        assert conv_expr == gt_expr


def test_action_feedback_good_expressions():
    """Test expressions that have events related to actions."""
    ok_expressions: List[str] = [
        "cos(_feedback.angle.x) == 1.0",
        "some_action.goal_id",
        "_action.goal_id",
    ]
    expected_expressions: List[str] = [
        f"cos({PLAIN_FIELD_EVENT_PREFIX}angle__x) == 1",
        "some_action__goal_id",
        f"{PLAIN_SCXML_EVENT_DATA_PREFIX}goal_id",
    ]
    for test_expr, gt_expr in zip(ok_expressions, expected_expressions):
        conv_expr = get_plain_expression(test_expr, CallbackType.ROS_ACTION_FEEDBACK, None)
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
        f"cos({PLAIN_FIELD_EVENT_PREFIX}angle) == 0",
        "some_action__goal_id",
        f"{PLAIN_SCXML_EVENT_DATA_PREFIX}goal_id",
    ]
    for test_expr, gt_expr in zip(ok_expressions, expected_expressions):
        conv_expr = get_plain_expression(test_expr, CallbackType.ROS_ACTION_RESULT, None)
        assert conv_expr == gt_expr


def test_convert_expression_with_object_arrays():
    """Test handling of array indexes."""
    # Simple cases
    assert convert_expression_with_object_arrays("x[0]") == "x[0]"
    assert convert_expression_with_object_arrays("x.y") == "x__y"
    assert convert_expression_with_object_arrays("x[0].y") == "x__y[0]"
    assert convert_expression_with_object_arrays("x[c].y") == "x__y[c]"
    assert convert_expression_with_object_arrays("x[c[2]].y") == "x__y[c[2]]"
    # Some function calls
    assert convert_expression_with_object_arrays("Math.sin(x[0].y)") == "Math.sin(x__y[0])"
    assert convert_expression_with_object_arrays("Math.sin(x[0].y)[6]") == "Math.sin(x__y[0])[6]"
    assert convert_expression_with_object_arrays("x.y.z[1].y") == "x__y__z__y[1]"
    assert convert_expression_with_object_arrays("x.y[0].z[1].y") == "x__y__z__y[0][1]"
    assert convert_expression_with_object_arrays("x.y[0].z[1].y + 1") == "x__y__z__y[0][1] + 1"
    assert (
        convert_expression_with_object_arrays("x.y[0].z[1].y**my[l].c")
        == "x__y__z__y[0][1] ** my__c[l]"
    )
    assert convert_expression_with_object_arrays("x[2].b && a") == "x__b[2] && a"

    # also with the length keyword
    assert convert_expression_with_object_arrays("x.length") == "x.length"
    with pytest.raises(AttributeError):
        convert_expression_with_object_arrays("x[0].length")
    with pytest.raises(AttributeError):
        convert_expression_with_object_arrays("x[0][1].length")
    with pytest.raises(AttributeError):
        convert_expression_with_object_arrays("x[1].y.length")
    with pytest.raises(AttributeError):
        convert_expression_with_object_arrays("x[1].y.length*c.length")
    with pytest.raises(AttributeError):
        convert_expression_with_object_arrays("x[0][x[0].length]")
    with pytest.raises(AttributeError):
        convert_expression_with_object_arrays("x[0].y[x[0].y.length]")
    with pytest.raises(AttributeError):
        convert_expression_with_object_arrays("x[x.length].y[x[0].y.length].length + y.length")
    assert convert_expression_with_object_arrays("x[x.length]") == "x[x.length]"
    with pytest.raises(AttributeError):
        convert_expression_with_object_arrays("x.length.length")
    with pytest.raises(AttributeError):
        convert_expression_with_object_arrays("x.length.y.length")
    # This throws an error from the esprima parser already
    with pytest.raises(RuntimeError):
        convert_expression_with_object_arrays("2.length")

    # are necessary brackets kept?
    assert convert_expression_with_object_arrays("!(x.y && x[0])") == "!(x__y && x[0])"
    assert convert_expression_with_object_arrays("!(x[0].y && x[0].u)") == "!(x__y[0] && x__u[0])"
    assert (
        convert_expression_with_object_arrays("(x.y + x[0].u)[x[7].a]")
        == "(x__y + x__u[0])[x__a[7]]"
    )
    assert (
        convert_expression_with_object_arrays("((a+b) * 9) ** a[i].x") == "((a + b) * 9) ** a__x[i]"
    )
    # Special casing for events info...
    assert (
        convert_expression_with_object_arrays("_event.data.param_a.param_b")
        == "_event.data.param_a__param_b"
    )
    # Test length access with custom structs
    # Prepare custom structs definitions
    custom_structs = {
        "Point": XmlStructDefinition("Point", {"x": "float32", "y": "float32"}),
        "Polygon": XmlStructDefinition("Polygon", {"points": "Point[]"}),
        "Polygons": XmlStructDefinition("Polygons", {"polygons": "Polygon[]"}),
    }
    for struct_def in custom_structs.values():
        struct_def.expand_members(custom_structs)
    data_model = ScxmlDataModel(
        [
            ScxmlData("nums", "[1,2,3]", "int32[]"),
            ScxmlData("nums_2d", "[[1,2,3]]", "int32[][]"),
            ScxmlData("points", "[{'x': 0.0, 'y': 1.0}]", "Point[]"),
            ScxmlData(
                "polygon", "{'points': [{'x': 1.0, 'y': 2.0}, {'x': 3.0, 'y': 4.0}]}", "Polygon"
            ),
            ScxmlData(
                "polygons",
                "[{'points': [{'x': 1.0, 'y': 2.0}, {'x': 3.0, 'y': 4.0}]},"
                "{'points': [{'x': 5.0, 'y': 6.0}]}]",
                "Polygons",
            ),
        ]
    )
    data_model.set_custom_data_types(custom_structs)
    for data_entry in data_model.get_data_entries():
        data_entry.set_custom_data_types(custom_structs)
    data_vars_structs = ScxmlStructDeclarationsContainer("test_aut", data_model, custom_structs)
    # Do the testing
    with pytest.raises(KeyError):
        convert_expression_with_object_arrays("no_var[0].length", None, data_vars_structs)
    assert (
        convert_expression_with_object_arrays("nums[0].length", None, data_vars_structs)
        == "nums[0].length"
    )
    assert (
        convert_expression_with_object_arrays("nums_2d[0][1].length", None, data_vars_structs)
        == "nums_2d[0][1].length"
    )
    assert (
        convert_expression_with_object_arrays("points.length", None, data_vars_structs)
        == "points__x.length"
    )
    assert (
        convert_expression_with_object_arrays("polygons.length", None, data_vars_structs)
        == "polygons__polygons__points__x.length"
    )
    assert (
        convert_expression_with_object_arrays(
            "polygons.polygons[2].points.length", None, data_vars_structs
        )
        == "polygons__polygons__points__x[2].length"
    )
    assert (
        convert_expression_with_object_arrays(
            "polygons.polygons[1].points.length * nums.length", None, data_vars_structs
        )
        == "polygons__polygons__points__x[1].length * nums.length"
    )
    assert (
        convert_expression_with_object_arrays(
            "nums_2d[0][nums_2d[0].length]", None, data_vars_structs
        )
        == "nums_2d[0][nums_2d[0].length]"
    )
    assert (
        convert_expression_with_object_arrays(
            "polygons.polygons[2].points[polygons.polygons[2].points.length]",
            None,
            data_vars_structs,
        )
        == "polygons__polygons__points[2][polygons__polygons__points__x[2].length]"
    )


def test_convert_expression_with_string_literals():
    """Test if the functionality works in a number of cases."""
    test_cases = [
        ("'as2fm'", "[97, 115, 50, 102, 109]"),
        ("as2fm_str == 'as2fm'", "as2fm_str == [97, 115, 50, 102, 109]"),
        ("'as2fm' == as2fm_str", "[97, 115, 50, 102, 109] == as2fm_str"),
        ("['as', '2', 'fm']", "[[97, 115], [50], [102, 109]]"),
    ]

    for in_val, gt_out in test_cases:
        out_val = convert_expression_with_string_literals(in_val)
        # Arrays are printed on multiple lines by default: we remove them here.
        out_val = " ".join(s.strip().rstrip() for s in out_val.splitlines())
        # Remove extra-spaces in array brackets
        out_val = out_val.replace("[ ", "[").replace(" ]", "]")
        assert out_val == gt_out, f"Failed converting `{in_val}`: `{out_val}` != `{gt_out}`"


def test_type_string_conversion():
    """Test the various types string are converted to the expected value."""
    # Test expected array types
    type_strings_ok = [
        ("float64", float),
        ("int32", int),
        ("bool", bool),
        ("float64[]", MutableSequence),
        ("int32[]", MutableSequence),
        ("int8[]", MutableSequence),
        ("float64[4]", MutableSequence),
        ("int32[10]", MutableSequence),
        ("int8[01]", MutableSequence),
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
