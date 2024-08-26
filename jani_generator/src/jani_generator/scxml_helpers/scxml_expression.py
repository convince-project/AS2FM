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

from typing import Optional, Type, Union
from dataclasses import dataclass
import esprima

from jani_generator.jani_entries.jani_convince_expression_expansion import \
    BASIC_EXPRESSIONS_MAPPING
from jani_generator.jani_entries.jani_expression import JaniExpression
from jani_generator.jani_entries.jani_value import JaniValue


@dataclass()
class ArrayInfo:
    array_type: Type[Union[int, float]]
    array_max_size: int


def parse_scxml_identifier(identifier: str) -> JaniExpression:
    """
    Parse an scxml identifier to a jani expression.

    :param identifier: The scxml identifier to parse.
    :return: The jani expression.
    """
    return JaniExpression(parse_ecmascript_to_jani_expression(identifier))


def parse_ecmascript_to_jani_expression(
        ecmascript: str, array_info: Optional[ArrayInfo] = None) -> JaniExpression:
    """
    Parse ecmascript to jani expression.

    :param ecmascript: The ecmascript to parse.
    :param array_info: The type and max size of the array, if required.
    :return: The jani expression.
    """
    ast = esprima.parseScript(ecmascript)
    assert len(ast.body) == 1, "The ecmascript must contain exactly one expression."
    ast = ast.body[0]
    return _parse_ecmascript_to_jani_expression(ast, array_info)


def _parse_ecmascript_to_jani_expression(
        ast: esprima.nodes.Script, array_info: Optional[ArrayInfo] = None) -> JaniExpression:
    """
    Parse ecmascript to jani expression.

    :param ecmascript: The ecmascript to parse.
    :param array_info: The type and max size of the array, if required.
    :return: The jani expression.
    """
    if ast.type == "Literal":
        return JaniExpression(JaniValue(ast.value))
    elif ast.type == "ArrayExpression":
        assert array_info is not None, "Array info must be provided for ArrayExpressions."
        assert len(ast.elements) == 0, "Array expressions with elements are not supported."
        return JaniExpression({
            "op": "ac",  # Array Constructor
            "var": "__array_iterator",
            "length": array_info.array_max_size,
            "exp": JaniValue(array_info.array_type(0))
        })
    elif ast.type == "Identifier":
        # If it is an identifier, we do not need to expand further
        return JaniExpression(ast.name)
    elif ast.type == "MemberExpression":
        if ast.computed:
            # This is an array access, like array[0]
            # For now, prevent nested arrays
            assert ast.object.type == "Identifier", "Nested arrays are not supported."
            array_name = ast.object.name
            array_index = _parse_ecmascript_to_jani_expression(ast.property)
            return JaniExpression({
                "op": "aa",  # Array Access
                "exp": array_name,
                "index": array_index
            })
        else:
            # A identifier in the style of object.property
            name = f'{ast.object.name}.{ast.property.name}'
            return JaniExpression(name)
    elif ast.type == "ExpressionStatement":
        return _parse_ecmascript_to_jani_expression(ast.expression)
    elif ast.type == "BinaryExpression":
        # It is a more complex expression
        assert ast.operator in BASIC_EXPRESSIONS_MAPPING, \
            f"ecmascript to jani expression: unknown operator {ast.operator}"
        return JaniExpression({
            "op": BASIC_EXPRESSIONS_MAPPING[ast.operator],
            "left": _parse_ecmascript_to_jani_expression(ast.left),
            "right": _parse_ecmascript_to_jani_expression(ast.right)
        })
    else:
        raise NotImplementedError(f"Unsupported ecmascript type: {ast.type}")
