# Copyright (c) 2025 - for information on the respective copyright owner
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

from typing import Optional

import pytest

from as2fm.jani_generator.jani_entries import JaniExpression
from as2fm.jani_generator.jani_entries.jani_expression_generator import (
    array_create_operator,
    max_operator,
    plus_operator,
    sin_operator,
)
from as2fm.jani_generator.scxml_helpers.scxml_expression import (
    ArrayInfo,
    parse_ecmascript_to_jani_expression,
)


def check_ecmascript_matches_gt_expression(
    ecmascript: str, gt_expr: JaniExpression, array_info: Optional[ArrayInfo] = None
):
    ecmascript_expr = parse_ecmascript_to_jani_expression(ecmascript, None, array_info)
    assert ecmascript_expr == gt_expr, f"{ecmascript_expr} is not matching with {gt_expr}"


def test_parse_ecmascript_to_jani_expression_basic():
    ecmascript_expr = "x + y"
    expected_jani_expr = plus_operator("x", "y")
    check_ecmascript_matches_gt_expression(ecmascript_expr, expected_jani_expr)


def test_parse_ecmascript_to_jani_expression_with_function():
    ecmascript_expr = "Math.max(a, b)"
    expected_jani_expr = max_operator("a", "b")
    check_ecmascript_matches_gt_expression(ecmascript_expr, expected_jani_expr)


@pytest.mark.skip(reason="PI is not yet supported in our ecmascript converter.")
def test_parse_ecmascript_to_jani_expression_with_constants():
    ecmascript_expr = "Math.PI"
    expected_jani_expr = JaniExpression({"constant": "π"})
    check_ecmascript_matches_gt_expression(ecmascript_expr, expected_jani_expr)


def test_parse_ecmascript_to_jani_expression_with_complex_expression():
    ecmascript_expr = "Math.sin(x+y)"
    expected_jani_expr = sin_operator(plus_operator("x", "y"))
    check_ecmascript_matches_gt_expression(ecmascript_expr, expected_jani_expr)


def test_parse_ecmascript_to_jani_expression_with_array():
    ecmascript_expr = "[]"
    expected_jani_expr = array_create_operator("__array_iterator", 10, 0)
    array_info = ArrayInfo(int, 10)
    check_ecmascript_matches_gt_expression(ecmascript_expr, expected_jani_expr, array_info)


def test_parse_ecmascript_to_jani_expression_with_string():
    ecmascript_expr = "''"
    expected_jani_expr = array_create_operator("__array_iterator", 10, 0)
    array_info = ArrayInfo(int, 10)
    check_ecmascript_matches_gt_expression(ecmascript_expr, expected_jani_expr, array_info)
