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
Expressions in Jani
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union, get_args

from as2fm.as2fm_common.common import is_valid_variable_name
from as2fm.jani_generator.jani_entries import JaniValue
from as2fm.scxml_converter.scxml_entries.utils import (
    MEMBER_ACCESS_SUBSTITUTION,
    PLAIN_SCXML_EVENT_DATA_PREFIX,
)

SupportedExp = Union[str, int, float, bool, dict]

JaniExprOrList = Union["JaniExpression", List["JaniExpression"]]


class JaniExpressionType(Enum):
    """Enumeration of the different types of Jani expressions."""

    IDENTIFIER = 1  # Reference to a constant or variable id
    LITERAL = 2  # Reference to a literal value
    OPERATOR = 3  # Reference to an operator (a composition of expressions)
    DISTRIBUTION = 4  # A random number from a distribution


class JaniExpression:
    """
    Jani Expression class.

    Content of an instance of this class can be:
    - identifier: a string representing a reference to a constant or variable
    or
    - value: a JaniValue object (literal expression)
    or
    - op: a string representing an operator
    - operands: a dictionary of operands, related to the specified operator
    """

    def __init__(self, expression: Union[SupportedExp, "JaniExpression", JaniValue]):
        self.identifier: Optional[str] = None
        self.value: Optional[JaniValue] = None
        self.op: Optional[str] = None
        self.operands: Dict[str, JaniExprOrList] = {}
        self.comment: Optional[str] = None
        if isinstance(expression, JaniExpression):
            self.reset(expression)
        elif isinstance(expression, JaniValue):
            self.value = expression
        else:
            assert isinstance(
                expression, get_args(SupportedExp)
            ), f"Unexpected expression type: {type(expression)} should be a dict or a base type."
            if isinstance(expression, str):
                # self._init_expression_from_string(expression)
                assert is_valid_variable_name(
                    expression
                ), f"Expression string {expression} is not a valid variable name."
                # If it is a reference to a constant or variable, we do not need to expand further
                self.identifier = expression
            elif JaniValue(expression).is_valid():
                # If it is a value, then we don't need to expand further
                self.value = JaniValue(expression)
            else:
                # If it isn't a value or an identifier, it must be a dictionary providing op and
                # related operands
                # Operands need to be expanded further, until we encounter a value expression
                assert isinstance(expression, dict), "Expected a dictionary"
                assert "op" in expression, "Expected either a value or an operator"
                self.comment = expression.get("comment")
                self.op = expression["op"]
                self.operands = self._get_operands(expression)

    def reset(self, new_expr: "JaniExpression"):
        """Replace the current expression instance with the provided one."""
        assert (
            new_expr.get_expression_type() != JaniExpressionType.DISTRIBUTION
        ), "Cannot convert a JaniDistribution to a JaniExpression explicitly."
        self.identifier = new_expr.identifier
        self.value = new_expr.value
        self.op = new_expr.op
        self.operands = new_expr.operands
        self.comment = new_expr.comment

    def _get_operands(
        self, expression_dict: dict
    ) -> Dict[str, Union["JaniExpression", List["JaniExpression"]]]:
        """Generate the expressions operands from a raw dictionary, after validating  it."""
        assert self.op is not None, "Operator not set"
        if self.op in ("intersect", "distance"):
            # intersect: returns a value in [0.0, 1.0], indicating where on the robot trajectory
            # the intersection occurs.
            #            0.0 means no intersection occurs (destination reached), 1.0 means the
            # intersection occurs at the start distance: returns the distance between the robot and
            # the barrier.
            return {
                "robot": generate_jani_expression(expression_dict["robot"]),
                "barrier": generate_jani_expression(expression_dict["barrier"]),
            }
        if self.op in ("distance_to_point"):
            # distance between robot outer radius and point x-y coords
            return {
                "robot": generate_jani_expression(expression_dict["robot"]),
                "x": generate_jani_expression(expression_dict["x"]),
                "y": generate_jani_expression(expression_dict["y"]),
            }
        if self.op in (
            "&&",
            "||",
            "and",
            "or",
            "∨",
            "∧",
            "⇒",
            "=>",
            "=",
            "≠",
            "!=",
            "+",
            "-",
            "*",
            "%",
            "pow",
            "log",
            "/",
            "min",
            "max",
            "<",
            "≤",
            ">",
            "≥",
            "<=",
            ">=",
            "==",
        ):
            return {
                "left": generate_jani_expression(expression_dict["left"]),
                "right": generate_jani_expression(expression_dict["right"]),
            }
        if self.op in (
            "!",
            "¬",
            "sin",
            "cos",
            "floor",
            "ceil",
            "abs",
            "to_cm",
            "to_m",
            "to_deg",
            "to_rad",
        ):
            return {"exp": generate_jani_expression(expression_dict["exp"])}
        if self.op in ("ite"):
            return {
                "if": generate_jani_expression(expression_dict["if"]),
                "then": generate_jani_expression(expression_dict["then"]),
                "else": generate_jani_expression(expression_dict["else"]),
            }
        # Array-specific expressions
        if self.op == "ac":
            return {
                "var": generate_jani_expression(expression_dict["var"]),
                "length": generate_jani_expression(expression_dict["length"]),
                "exp": generate_jani_expression(expression_dict["exp"]),
            }
        if self.op == "aa":
            return {
                "exp": generate_jani_expression(expression_dict["exp"]),
                "index": generate_jani_expression(expression_dict["index"]),
            }
        if self.op == "av":
            return {"elements": generate_jani_expression(expression_dict["elements"])}
        # Convince specific expressions
        if self.op in ("norm2d"):
            return {
                "x": generate_jani_expression(expression_dict["x"]),
                "y": generate_jani_expression(expression_dict["y"]),
            }
        if self.op in ("dot2d", "cross2d"):
            return {
                "x1": generate_jani_expression(expression_dict["x1"]),
                "y1": generate_jani_expression(expression_dict["y1"]),
                "x2": generate_jani_expression(expression_dict["x2"]),
                "y2": generate_jani_expression(expression_dict["y2"]),
            }
        assert False, f'Unknown operator "{self.op}" found.'

    def get_expression_type(self) -> JaniExpressionType:
        """Get the type of the expression."""
        assert self.is_valid(), "Expression is not valid"
        if self.identifier is not None:
            return JaniExpressionType.IDENTIFIER
        if self.value is not None:
            return JaniExpressionType.LITERAL
        if self.op is not None:
            return JaniExpressionType.OPERATOR
        raise RuntimeError("Unknown expression type")

    def replace_event(self, replacement: Optional[str]) -> "JaniExpression":
        """Replace the default SCXML event prefix with the provided replacement.

        Within a transitions, scxml can access to the event's parameters using a specific prefix.
        We have to replace this by the global variable where we stored the data from the received
        event.

        :param replacement: The string to replace `PLAIN_SCXML_EVENT_DATA_PREFIX` with.
        :return self: for the convenience of chain-ability
        """
        if replacement is None:
            # No replacement needed!
            return self
        if self.identifier is not None and self.identifier.startswith(
            PLAIN_SCXML_EVENT_DATA_PREFIX
        ):
            self.identifier = (
                f"{replacement}{MEMBER_ACCESS_SUBSTITUTION}"
                + f"{self.identifier.removeprefix(PLAIN_SCXML_EVENT_DATA_PREFIX)}"
            )
            return self
        if self.value is not None:
            return self
        for operand in self.operands.values():
            if isinstance(operand, JaniExpression):
                operand.replace_event(replacement)
        return self

    def is_valid(self) -> bool:
        """Expression validity check."""
        return self.identifier is not None or self.value is not None or self.op is not None

    def as_literal(self) -> Optional[JaniValue]:
        """Provide the expression as a literal (JaniValue), if possible. None otherwise."""
        assert self.is_valid(), "Expression is not valid"
        return self.value

    def as_identifier(self) -> Optional[str]:
        """Provide the expression as an identifier, if possible. None otherwise."""
        assert self.is_valid(), "Expression is not valid"
        return self.identifier

    def as_operator(self) -> Tuple[Optional[str], Optional[Dict[str, JaniExprOrList]]]:
        """Provide the expression as an operator, if possible. (None, None) otherwise."""
        assert self.is_valid(), "Expression is not valid"
        if self.op is None:
            return (None, None)
        return (self.op, self.operands)

    def as_dict(self) -> Union[str, int, float, bool, dict]:
        """Convert the expression to a dictionary, ready to be converted to JSON."""
        assert hasattr(self, "identifier"), f"Identifier not set for {self.__dict__}"
        if self.identifier is not None:
            return self.identifier
        if self.value is not None:
            return self.value.as_dict()
        op_dict: Dict[str, Any] = {}
        if self.comment is not None:
            op_dict.update({"comment": self.comment})
        op_dict.update({"op": self.op})
        for op_key, op_value in self.operands.items():
            if isinstance(op_value, JaniExpression):
                op_dict.update({op_key: op_value.as_dict()})
            elif isinstance(op_value, list):
                list_of_dicts = [single_val.as_dict() for single_val in op_value]
                op_dict.update({op_key: list_of_dicts})
            else:
                raise TypeError(f"Unexpected operand {op_key} value type {type(op_value)}.")
        return op_dict

    def __eq__(self, value):
        """Equality operator between two JaniExpressions."""
        assert isinstance(value, JaniExpression)
        return self.as_dict() == value.as_dict()

    def __str__(self):
        return f"JaniExpression({self.as_dict()})"


class JaniDistribution(JaniExpression):
    """
    A class representing a Jani Distribution (a random variable).

    At the moment, this is only meant to support Uniform distributions between 0.0 and 1.0
    """

    def __init__(self, expression: dict):
        self._distribution = expression.get("distribution")
        self._args = expression.get("args")
        assert (
            self._distribution == "Uniform"
        ), f"Expected distribution to be Uniform, found {self._distribution}."
        assert (
            isinstance(self._args, list) and len(self._args) == 2
        ), f"Unexpected arguments for Uniform distribution expression: {self._args}."
        assert self.is_valid(), "Invalid arguments provided: expected args[0] <= args[1]."

    def is_valid(self):
        """Distribution validity check."""
        # All other checks are carried out in the constructor
        return all(isinstance(argument, (int, float)) for argument in self._args) and (
            self._args[0] <= self._args[1]
        )

    def get_expression_type(self) -> JaniExpressionType:
        """Get the type of the expression."""
        assert self.is_valid(), "Expression is not valid"
        return JaniExpressionType.DISTRIBUTION

    def replace_event(self, _: Optional[str]) -> "JaniDistribution":
        """Replace the default SCXML event prefix with the provided replacement."""
        return self

    def as_literal(self) -> None:
        """Provide the expression as a literal (JaniValue), if possible. None otherwise."""
        return None

    def as_identifier(self) -> None:
        """Provide the expression as an identifier, if possible. None otherwise."""
        return None

    def as_operator(self) -> Tuple[None, None]:
        """Provide the expression as an operator, if possible. None otherwise."""
        return (None, None)

    def get_dist_type(self) -> str:
        """Return the distribution type set in the object."""
        return self._distribution

    def get_dist_args(self) -> List[Union[int, float]]:
        """Return the config. arguments of the distribution."""
        return self._args

    def as_dict(self) -> Dict[str, Any]:
        """Convert the distribution to a dictionary, ready to be converted to JSON."""
        assert self.is_valid(), "Expected distribution to be valid."
        return {"distribution": self._distribution, "args": self._args}


def generate_jani_expression(expr: SupportedExp) -> JaniExprOrList:
    """Generate a JaniExpression, a list of them or a JaniDistribution, based on the input."""
    if isinstance(expr, JaniExpression):
        return expr
    if isinstance(expr, (str, JaniValue)) or JaniValue(expr).is_valid():
        return JaniExpression(expr)
    if isinstance(expr, list):
        # list of jani expressions
        new_list: List[JaniExpression] = [generate_jani_expression(x) for x in expr]
        assert all(
            new_expr.is_valid() for new_expr in new_list
        ), "Error generating list of JaniExpressions."
        return new_list
    assert isinstance(expr, dict), f"Unsupported expression provided: {expr}."
    if "distribution" in expr:
        return JaniDistribution(expr)
    return JaniExpression(expr)
