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
Generate full expressions in Jani
"""

from typing import MutableSequence, Union

from as2fm.jani_generator.jani_entries import JaniDistribution, JaniExpression
from as2fm.scxml_converter.xml_data_types.type_utils import ArrayInfo


# Math operators
def minus_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "-", "left": left, "right": right})


def unary_minus_operator(exp) -> JaniExpression:
    return JaniExpression({"op": "-", "left": 0, "right": exp})


def plus_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "+", "left": left, "right": right})


def multiply_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "*", "left": left, "right": right})


def divide_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "/", "left": left, "right": right})


def modulo_operator(left, right) -> JaniExpression:
    # Note: The modulo operator in Jani works only on integers
    return JaniExpression({"op": "%", "left": left, "right": right})


def pow_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "pow", "left": left, "right": right})


def log_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "log", "left": left, "right": right})


def abs_operator(exp) -> JaniExpression:
    return JaniExpression({"op": "abs", "exp": exp})


def floor_operator(exp) -> JaniExpression:
    return JaniExpression({"op": "floor", "exp": exp})


def ceil_operator(exp) -> JaniExpression:
    return JaniExpression({"op": "ceil", "exp": exp})


# More numerical operators
def max_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "max", "left": left, "right": right})


def min_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "min", "left": left, "right": right})


def greater_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": ">", "left": left, "right": right})


def greater_equal_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "≥", "left": left, "right": right})


def lower_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "<", "left": left, "right": right})


def lower_equal_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "≤", "left": left, "right": right})


def equal_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "=", "left": left, "right": right})


def not_equal_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "≠", "left": left, "right": right})


# Trigonometry operators
def sin_operator(exp) -> JaniExpression:
    return JaniExpression({"op": "sin", "exp": exp})


def cos_operator(exp) -> JaniExpression:
    return JaniExpression({"op": "cos", "exp": exp})


# Logic operators
def not_operator(exp) -> JaniExpression:
    return JaniExpression({"op": "¬", "exp": exp})


def and_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "∧", "left": left, "right": right})


def or_operator(left, right) -> JaniExpression:
    # Note: The char representing the OR is not a normal v letter (U+0076), but a ∨ symbol (U+2228)
    return JaniExpression({"op": "∨", "left": left, "right": right})


# if operator
def if_operator(condition, true_value, false_value) -> JaniExpression:
    return JaniExpression({"op": "ite", "if": condition, "then": true_value, "else": false_value})


# array operators
def array_create_operator(array_info: ArrayInfo, *, curr_dim: int = 1) -> JaniExpression:
    """
    Generate an empty array based on the provided array_info

    :param array_info: A struct containing all information related to the array to create.
    :param curr_dim: The current dimension under expansion. Used for recursion.
    """
    array_iterator_var = f"__array_iterator_dim_{curr_dim}"
    default_expr = JaniExpression(0)
    if array_info.array_dimensions > 1:
        default_expr = array_create_operator(
            ArrayInfo(
                array_info.array_type,
                array_info.array_dimensions - 1,
                array_info.array_max_sizes[1:],
            ),
            curr_dim=curr_dim + 1,
        )
    return JaniExpression(
        {
            "op": "ac",
            "var": array_iterator_var,
            "length": array_info.array_max_sizes[0],
            "exp": default_expr,
        }
    )


def array_access_operator(exp, index) -> JaniExpression:
    """
    Generate an array access expression

    :param exp: The array variable to access
    :param index: The index to access on exp
    """
    return JaniExpression({"op": "aa", "exp": exp, "index": index})


def array_value_operator(
    elements: MutableSequence[Union[MutableSequence, float, int]],
) -> JaniExpression:
    """
    Generate an array value expression

    :param elements: The elements of the array
    """
    elements_expressions = [
        (
            array_value_operator(array_element)
            if isinstance(array_element, MutableSequence)
            else array_element
        )
        for array_element in elements
    ]
    return JaniExpression({"op": "av", "elements": elements_expressions})


def distribution_expression(distribution: str, arguments: list) -> JaniDistribution:
    """
    Generate a distribution expression

    :param distribution: The statistical distribution to pick from
    :param arguments: The parameters for configuring the statistical distribution
    """
    return JaniDistribution({"distribution": distribution, "args": arguments})
