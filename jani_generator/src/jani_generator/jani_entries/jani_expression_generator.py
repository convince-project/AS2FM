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

from jani_generator.jani_entries import JaniExpression


# Math operators
def minus_operator(left, right) -> JaniExpression:
    return JaniExpression({"op": "-", "left": left, "right": right})


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
