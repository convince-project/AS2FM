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
Module producing jani expressions from ecmascript.
"""

from typing import Union

import esprima

from jani_generator.jani_entries.jani_expression import JaniExpression
from jani_generator.jani_entries.jani_value import JaniValue
from jani_generator.jani_entries.jani_convince_expression_expansion import BASIC_EXPRESSIONS_MAPPING


def parse_ecmascript_to_jani_expression(ecmascript: str) -> Union[JaniValue, JaniExpression]:
    """
    Parse ecmascript to jani expression.

    :param ecmascript: The ecmascript to parse.
    :return: The jani expression.
    """
    ast = esprima.parseScript(ecmascript)
    assert len(ast.body) == 1, "The ecmascript must contain exactly one expression."
    ast = ast.body[0]
    return _parse_ecmascript_to_jani_expression(ast)


def _parse_ecmascript_to_jani_expression(ast: esprima.nodes.Script
                                         ) -> Union[JaniValue, JaniExpression]:
    """
    Parse ecmascript to jani expression.

    :param ecmascript: The ecmascript to parse.
    :return: The jani expression.
    """
    if ast.type == "Literal":
        return JaniValue(ast.value)
    elif ast.type == "Identifier":
        # If it is an identifier, we do not need to expand further
        return JaniExpression(ast.name)
    elif ast.type == "MemberExpression":
        # A identifier in the style of object.property
        name = f'{ast.object.name}.{ast.property.name}'
        return JaniExpression(name)
    elif ast.type == "ExpressionStatement":
        return _parse_ecmascript_to_jani_expression(ast.expression)
    else:
        # It is a more complex expression
        if ast.type == "BinaryExpression":
            if ast.operator in BASIC_EXPRESSIONS_MAPPING:
                operator = BASIC_EXPRESSIONS_MAPPING[ast.operator]
            else:
                operator = ast.operator
            return JaniExpression({
                "op": operator,
                "left": _parse_ecmascript_to_jani_expression(ast.left),
                "right": _parse_ecmascript_to_jani_expression(ast.right)
            })
        else:
            raise NotImplementedError(f"Unsupported ecmascript type: {ast.type}")