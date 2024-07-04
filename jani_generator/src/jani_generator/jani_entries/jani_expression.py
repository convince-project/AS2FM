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

from typing import Union
from jani_generator.jani_entries import JaniValue

SupportedExp = Union[str, int, float, bool, dict]


class JaniExpression:
    def __init__(self, expression):
        self.identifier: str = None
        self.value: JaniValue = None
        self.op = None
        self.operands = None
        if isinstance(expression, JaniExpression):
            self.identifier = expression.identifier
            self.value = expression.value
            self.op = expression.op
            self.operands = expression.operands
        elif isinstance(expression, JaniValue):
            self.value = expression
        else:
            assert isinstance(expression, SupportedExp), \
                f"Unexpected expression type: {type(expression)} should be a dict or a base type."
            if isinstance(expression, str):
                # If it is a reference to a constant or variable, we do not need to expand further
                self.identifier = expression
            elif JaniValue(expression).is_valid():
                # If it is a value, then we don't need to expand further
                self.value = JaniValue(expression)
            else:
                # If it isn't a value or an identifier, it must be a dictionary providing op and related operands
                # Operands need to be expanded further, until we encounter a value expression
                assert isinstance(expression, dict), "Expected a dictionary"
                assert "op" in expression, "Expected either a value or an operator"
                self.op = expression["op"]
                self.operands = self._get_operands(expression)

    def _get_operands(self, expression_dict: dict):
        if (self.op in ("intersect", "distance")):
            # intersect: returns a value in [0.0, 1.0], indicating where on the robot trajectory the intersection occurs.
            #            0.0 means no intersection occurs (destination reached), 1.0 means the intersection occurs at the start
            # distance: returns the distance between the robot and the barrier
            return {
                "robot": JaniExpression(expression_dict["robot"]),
                "barrier": JaniExpression(expression_dict["barrier"])}
        if (self.op in ("distance_to_point")):
            # distance between robot outer radius and point x-y coords
            return {
                "robot": JaniExpression(expression_dict["robot"]),
                "x": JaniExpression(expression_dict["x"]),
                "y": JaniExpression(expression_dict["y"])}
        if (self.op in (
                "&&", "||", "and", "or", "∨", "∧",
                "⇒", "=>", "=", "≠", "!=", "+", "-", "*", "%",
                "pow", "log", "/", "min", "max",
                "<", "≤", ">", "≥", "<=", ">=")):
            return {
                "left": JaniExpression(expression_dict["left"]),
                "right": JaniExpression(expression_dict["right"])}
        if (self.op in ("!", "¬", "sin", "cos", "floor", "ceil", "abs", "to_cm", "to_m", "to_deg", "to_rad")):
            return {
                "exp": JaniExpression(expression_dict["exp"])}
        if (self.op in ("ite")):
            return {
                "if": JaniExpression(expression_dict["if"]),
                "then": JaniExpression(expression_dict["then"]),
                "else": JaniExpression(expression_dict["else"])}
        if (self.op in ("norm2d")):
            return {
                "x": JaniExpression(expression_dict["x"]),
                "y": JaniExpression(expression_dict["y"])}
        if (self.op in ("dot2d", "cross2d")):
            return {
                "x1": JaniExpression(expression_dict["x1"]),
                "y1": JaniExpression(expression_dict["y1"]),
                "x2": JaniExpression(expression_dict["x2"]),
                "y2": JaniExpression(expression_dict["y2"])}
        assert False, f"Unknown operator \"{self.op}\" found."

    def replace_event(self, replacement):
        """Replace `_event` with `replacement`.

        Within a transitions, scxml can access data of events from the `_event` variable. We
        have to replace this by the global variable where we stored the data from the received
        event.

        :param replacement: The string to replace `_event` with.
        :return self: for the convenience of chain-ability
        """
        if replacement is None:
            # No replacement needed!
            return self
        if self.identifier is not None:
            self.identifier = self.identifier.replace("_event", replacement)
            return self
        if self.value is not None:
            return self
        for operand in self.operands.values():
            operand.replace_event(replacement)
        return self

    def is_valid(self) -> bool:
        return self.identifier is not None or self.value is not None or self.op is not None

    def as_dict(self) -> Union[str, int, float, bool, dict]:
        assert hasattr(self, "identifier"), f"Identifier not set for {self.__dict__}"
        if self.identifier is not None:
            return self.identifier
        if self.value is not None:
            return self.value.as_dict()
        op_dict = {
            "op": self.op,
        }
        for op_key, op_value in self.operands.items():
            assert isinstance(op_value, JaniExpression), f"Expected an expression, found {type(op_value)} for {op_key}"
            assert hasattr(op_value, "identifier"), f"Identifier not set for {op_key}"
            op_dict.update({op_key: op_value.as_dict()})
        return op_dict
