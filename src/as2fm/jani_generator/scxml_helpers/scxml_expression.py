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

from dataclasses import dataclass
from typing import List, Optional, Type, Union

import esprima

from as2fm.jani_generator.jani_entries.jani_convince_expression_expansion import (
    CALLABLE_OPERATORS_MAP,
    OPERATORS_TO_JANI_MAP,
)
from as2fm.jani_generator.jani_entries.jani_expression import JaniExpression
from as2fm.jani_generator.jani_entries.jani_expression_generator import (
    array_access_operator,
    array_create_operator,
    array_value_operator,
)
from as2fm.jani_generator.jani_entries.jani_value import JaniValue

JS_CALLABLE_PREFIX = "Math"


@dataclass()
class ArrayInfo:
    array_type: Type[Union[int, float]]
    array_max_size: int


def parse_ecmascript_to_jani_expression(
    ecmascript: str, array_info: Optional[ArrayInfo] = None
) -> JaniExpression:
    """
    Parse ecmascript to jani expression.

    :param ecmascript: The ecmascript to parse.
    :param array_info: The type and max size of the array, if required.
    :return: The jani expression.
    """
    try:
        ast = esprima.parseScript(ecmascript)
    except esprima.error_handler.Error as e:
        raise RuntimeError(f"Failed parsing ecmascript: {ecmascript}. Error: {e}.")
    assert len(ast.body) == 1, "The ecmascript must contain exactly one expression."
    ast = ast.body[0]
    try:
        jani_expression = _parse_ecmascript_to_jani_expression(ast, array_info)
    except NotImplementedError:
        raise RuntimeError(f"Unsupported ecmascript: {ecmascript}")
    except AssertionError:
        raise RuntimeError(f"Assertion from ecmascript: {ecmascript}")
    return jani_expression


def _parse_ecmascript_to_jani_expression(
    ast: esprima.nodes.Script, array_info: Optional[ArrayInfo] = None
) -> JaniExpression:
    """
    Parse ecmascript to jani expression.

    :param ecmascript: The ecmascript to parse.
    :param array_info: The type and max size of the array, if required.
    :return: The jani expression.
    """
    if ast.type == "ExpressionStatement":
        return _parse_ecmascript_to_jani_expression(ast.expression, array_info)
    elif ast.type == "Literal":
        return JaniExpression(JaniValue(ast.value))
    elif ast.type == "Identifier":
        # If it is an identifier, we do not need to expand further
        assert ast.name not in ("True", "False"), (
            f"Boolean {ast.name} mistaken for an identifier. "
            "Did you mean to use 'true' or 'false' instead?"
        )
        return JaniExpression(ast.name)
    elif ast.type == "UnaryExpression":
        assert ast.prefix is True and ast.operator == "-", "Only unary minus is supported."
        return JaniExpression(
            {
                "op": OPERATORS_TO_JANI_MAP[ast.operator],
                "left": JaniValue(0),
                "right": _parse_ecmascript_to_jani_expression(ast.argument, array_info),
            }
        )
    elif ast.type == "BinaryExpression" or ast.type == "LogicalExpression":
        # It is a more complex expression
        assert (
            ast.operator in OPERATORS_TO_JANI_MAP
        ), f"ecmascript to jani expression: unknown operator {ast.operator}"
        return JaniExpression(
            {
                "op": OPERATORS_TO_JANI_MAP[ast.operator],
                "left": _parse_ecmascript_to_jani_expression(ast.left, array_info),
                "right": _parse_ecmascript_to_jani_expression(ast.right, array_info),
            }
        )
    elif ast.type == "ArrayExpression":
        assert array_info is not None, "Array info must be provided for ArrayExpressions."
        entry_type: Type = array_info.array_type
        if len(ast.elements) == 0:
            return array_create_operator(
                "__array_iterator", array_info.array_max_size, entry_type(0)
            )
        else:
            elements_to_add = array_info.array_max_size - len(ast.elements)
            assert (
                elements_to_add >= 0
            ), "Array size must be less than or equal to the recipient max size."
            elements_list = []
            for element in ast.elements:
                assert element.type == "Literal", "Array elements must be literals."
                elements_list.append(entry_type(element.value))
            # Add dummy elements to make sure the full array is assigned
            elements_list.extend([entry_type(0)] * elements_to_add)
            return array_value_operator(elements_list)
    elif ast.type == "MemberExpression":
        object_expr = _parse_ecmascript_to_jani_expression(ast.object, array_info)
        if ast.computed:
            # This is an array access, like array[0]
            array_index = _parse_ecmascript_to_jani_expression(ast.property, array_info)
            return array_access_operator(object_expr, array_index)
        else:
            # Access to the member of an object through dot notation
            # Check the object_expr is an identifier
            object_expr_str = object_expr.as_identifier()
            assert (
                object_expr_str is not None
            ), "Only identifiers can be accessed through dot notation."
            assert (
                ast.property.type == "Identifier"
            ), "Dot notation can be used only to access object's members."
            field_complete_name = f"{object_expr_str}.{ast.property.name}"
            return JaniExpression(field_complete_name)
    elif ast.type == "CallExpression":
        # We expect function calls to be of the form Math.function_name(args) (JavaScript-like)
        # The "." operator is represented as a MemberExpression
        assert (
            ast.callee.type == "MemberExpression"
        ), f"Functions callee is expected to be MemberExpressions, found {ast.callee}."
        assert (
            ast.callee.object.type == "Identifier"
        ), f"Callee object is expected to be an Identifier, found {ast.callee.object}."
        assert (
            ast.callee.property.type == "Identifier"
        ), f"Callee property is expected to be an Identifier, found {ast.callee.property}."
        assert (
            ast.callee.object.name == JS_CALLABLE_PREFIX
        ), f"Function calls prefix is expected to be 'Math', found {ast.callee.object.name}."
        function_name: str = ast.callee.property.name
        assert (
            function_name in CALLABLE_OPERATORS_MAP
        ), f"Unsupported function call {function_name}."
        expression_args: List[JaniExpression] = []
        for arg in ast.arguments:
            expression_args.append(_parse_ecmascript_to_jani_expression(arg, array_info))
        return CALLABLE_OPERATORS_MAP[function_name](*expression_args)
    else:
        raise NotImplementedError(f"Unsupported ecmascript type: {ast.type}")
