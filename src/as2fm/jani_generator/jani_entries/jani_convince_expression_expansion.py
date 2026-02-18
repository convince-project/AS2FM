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
# limitations under the License.from typing import List

"""Expand expressions into jani."""

from copy import deepcopy
from typing import Callable, Dict, List, Union

from as2fm.jani_generator.jani_entries import (
    JaniConstant,
    JaniDistribution,
    JaniExpression,
    JaniExpressionType,
)
from as2fm.jani_generator.jani_entries.jani_expression_generator import (
    abs_operator,
    ceil_operator,
    cos_operator,
    distribution_expression,
    floor_operator,
    log_operator,
    max_operator,
    min_operator,
    not_operator,
    pow_operator,
    sin_operator,
    unary_minus_operator,
)

# Map each operator to the corresponding one in Jani
OPERATORS_TO_JANI_MAP: Dict[str, str] = {
    "-": "-",
    "+": "+",
    "*": "*",
    "/": "/",
    "%": "%",
    "pow": "pow",
    "log": "log",
    "max": "max",
    "min": "min",
    "abs": "abs",
    ">": ">",
    "≥": "≥",
    ">=": "≥",
    "<": "<",
    "≤": "≤",
    "<=": "≤",
    "=": "=",
    "==": "=",
    "≠": "≠",
    "!=": "≠",
    "!": "¬",
    "¬": "¬",
    "sin": "sin",
    "cos": "cos",
    "floor": "floor",
    "ceil": "ceil",
    "∧": "∧",
    "&&": "∧",
    "and": "∧",
    "∨": "∨",
    "||": "∨",
    "or": "∨",
    "ite": "ite",
    "⇒": "⇒",
    "=>": "⇒",
    "aa": "aa",
    "ac": "ac",
    "av": "av",
}


def random_operator() -> JaniDistribution:
    """Function to get a random number between 0 and 1 in the Jani Model."""
    return distribution_expression("Uniform", [0.0, 1.0])


def __substitute_expression_op(expression: JaniExpression) -> JaniExpression:
    assert isinstance(expression, JaniExpression), "The input must be a JaniExpression"
    assert expression.op in OPERATORS_TO_JANI_MAP, f"The operator {expression.op} is not supported"
    expression.op = OPERATORS_TO_JANI_MAP[expression.op]
    return expression


def expand_expression(
    expression: Union[JaniExpression, List[JaniExpression]], jani_constants: Dict[str, JaniConstant]
) -> Union[JaniExpression, List[JaniExpression]]:
    """
    Given an expression (or a list of them), expand all operators to use only plain features.
    """
    # Given a CONVINCE JaniExpression, expand it to a plain JaniExpression
    if isinstance(expression, list):
        assert all(
            isinstance(entry, JaniExpression) for entry in expression
        ), "Expected a list of expressions, found something else."
        expanded_expressions: List[JaniExpression] = []
        for entry in expression:
            expanded_entry = expand_expression(entry, jani_constants)
            if isinstance(expanded_entry, list):
                expanded_expressions.extend(expanded_entry)
            else:
                expanded_expressions.append(expanded_entry)
        return expanded_expressions
    assert isinstance(
        expression, JaniExpression
    ), f"The expression should be a JaniExpression instance, found {type(expression)} instead."
    assert (
        expression.is_valid()
    ), "The expression is not valid: it defines no value, nor variable, nor operation to be done."
    if expression.get_expression_type() == JaniExpressionType.DISTRIBUTION:
        # For now this is fine, since we expect only real values in the args
        return expression
    if expression.op is None:
        # It is either a variable/constant identifier or a value
        return expression
    # If the expressions is neither of the above, we expand the operands and return them
    for key, value in expression.operands.items():
        expression.operands[key] = expand_expression(value, jani_constants)
    # The remaining operators are the basic ones, and they only need the operand to be substituted
    return __substitute_expression_op(expression)


def expand_distribution_expressions(
    expression: JaniExpression, *, n_options
) -> List[JaniExpression]:
    """
    Traverse the expression and substitute each distribution with n expressions.

    This is a workaround, until we can support it in our model checker.

    :param expression: The expression to expand.
    :param n_options: How many options to generate for each encountered distribution.
    :return: One expression, if no distribution is found, n_options^n_distributions expr. otherwise.
    """
    assert isinstance(
        expression, JaniExpression
    ), f"Unexpected expression type: {type(expression)} != (JaniExpression, JaniDistribution)."
    assert expression.is_valid(), f"Invalid expression found: {expression}."
    expr_type = expression.get_expression_type()
    if expr_type == JaniExpressionType.OPERATOR:
        # Generate all possible expressions, if expansion returns many expressions for an operand
        expanded_expressions: List[JaniExpression] = [deepcopy(expression)]
        for key, value in expression.operands.items():
            if isinstance(value, JaniExpression):
                # Normal case, operand value is a JaniExpression
                expanded_operand = expand_distribution_expressions(value, n_options=n_options)
                base_expressions = expanded_expressions
                expanded_expressions = []
                for expr in base_expressions:
                    for key_value in expanded_operand:
                        expr.operands[key] = key_value
                        expanded_expressions.append(deepcopy(expr))
            else:
                assert isinstance(value, list), f"Unexpected value type {type(value)}."
                # Here we expect an array of JaniExpressions
                for value_idx, value_entry in enumerate(value):
                    base_expressions = expanded_expressions
                    expanded_expressions = []
                    expanded_operand_entries = expand_distribution_expressions(
                        value_entry, n_options=n_options
                    )
                    for expr in base_expressions:
                        for expanded_entry in expanded_operand_entries:
                            expr_operand = expr.operands[key]
                            assert isinstance(
                                expr_operand, list
                            ), f"Unexpected type of {expr=} and {key=}: should be a list."
                            expr_operand[value_idx] = expanded_entry
                            expanded_expressions.append(deepcopy(expr))
        return expanded_expressions
    elif expr_type == JaniExpressionType.DISTRIBUTION:
        # Here we need to substitute the distribution with a number of constants
        assert isinstance(expression, JaniDistribution) and expression.is_valid()
        lower_bound = expression.get_dist_args()[0]
        dist_width = expression.get_dist_args()[1] - lower_bound
        # Generate a (constant) JaniExpression for each possible outcome
        return [
            JaniExpression(lower_bound + (x * dist_width / (n_options))) for x in range(n_options)
        ]
    return [expression]


# Map each function name to the corresponding Expression generator
CALLABLE_OPERATORS_MAP: Dict[str, Callable] = {
    "abs": abs_operator,
    "floor": floor_operator,
    "ceil": ceil_operator,
    "cos": cos_operator,
    "sin": sin_operator,
    "log": log_operator,
    "pow": pow_operator,
    "min": min_operator,
    "max": max_operator,
    "random": random_operator,
}

# Map each function name to the corresponding Expression generator
UNARY_OPERATORS_MAP: Dict[str, Callable] = {"-": unary_minus_operator, "!": not_operator}
