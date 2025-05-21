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

# TODO: Rename this file to something more meaningful, like ecmascript_to_jani.py

from typing import List, MutableSequence, Optional, Type, Union

import esprima
from esprima.syntax import Syntax
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.array_type import ArrayInfo
from as2fm.as2fm_common.common import convert_string_to_int_array
from as2fm.as2fm_common.logging import check_assertion, get_error_msg
from as2fm.jani_generator.jani_entries.jani_convince_expression_expansion import (
    CALLABLE_OPERATORS_MAP,
    OPERATORS_TO_JANI_MAP,
    UNARY_OPERATORS_MAP,
)
from as2fm.jani_generator.jani_entries.jani_expression import JaniExpression
from as2fm.jani_generator.jani_entries.jani_expression_generator import (
    array_access_operator,
    array_value_operator,
)
from as2fm.jani_generator.jani_entries.jani_value import JaniValue
from as2fm.scxml_converter.scxml_entries.utils import ARRAY_LENGTH_SUFFIX

JS_CALLABLE_PREFIX = "Math"


def get_array_length_var_name(array_name: str, dimension: int) -> str:
    """
    Generate the name of the variable holding the lengths for a specific dimension.

    :param array_name: The name of the array this variable refers to.
    :param dimension: to which dimension the length variable refers to [1-N].
    :return: The variable name
    """
    assert isinstance(array_name, str) and len(array_name) > 0
    assert isinstance(dimension, int) and dimension > 0
    return f"{array_name}.d{dimension}_len"


def convert_array_access_to_length_access(jani_expr: JaniExpression) -> JaniExpression:
    """
    Substitute the array_access ('aa') expression to access the related array dimension variable.
    """
    return __convert_array_access_to_length_access(jani_expr, 1)


def __convert_array_access_to_length_access(
    jani_expr: JaniExpression, dim_level: int
) -> JaniExpression:
    """
    Implementation of the `convert_array_access_to_length_access` function.

    :param jani_expr: The expression to process, must be an `aa` operator.
    :param dim_level: The level of the previous jani_expr.
    :return: The new expression to use for accessing the length.
    """
    jani_operator, jani_operands = jani_expr.as_operator()
    assert jani_operator == "aa", f"Expected JANI operator `aa`, found `{jani_operator}`."
    assert jani_operands is not None, "Expected jani_operands to be not None."
    curr_dim_level = dim_level + 1
    array_expr = jani_operands["exp"]
    index_expr = jani_operands["index"]
    assert isinstance(array_expr, JaniExpression), f"Unexpected value of {array_expr=}."
    array_expr_id = array_expr.as_identifier()
    if array_expr_id is not None:
        array_length_var = get_array_length_var_name(array_expr_id, curr_dim_level)
        return array_access_operator(array_length_var, index_expr)
    return array_access_operator(
        __convert_array_access_to_length_access(array_expr, curr_dim_level), index_expr
    )


def parse_ecmascript_to_jani_expression(
    ecmascript: str, elem: Optional[XmlElement], array_info: Optional[ArrayInfo] = None
) -> JaniExpression:
    """
    Parse ecmascript to jani expression.

    :param ecmascript: The ecmascript to parse.
    :param array_info: The type and max size of the array, if required.
    :return: The jani expression.
    """
    check_assertion(isinstance(ecmascript, str), elem, f"Unexpected type {type(ecmascript)}.")
    try:
        ast = esprima.parseScript(ecmascript)
    except esprima.error_handler.Error as e:
        raise RuntimeError(
            get_error_msg(elem, f"Failed parsing ecmascript: {ecmascript}. Error: {e}.")
        )
    assert len(ast.body) == 1, get_error_msg(
        elem, "The ecmascript must contain exactly one expression."
    )
    ast = ast.body[0]
    try:
        jani_expression = _parse_ecmascript_to_jani_expression(ast, None, array_info)
    except NotImplementedError:
        raise RuntimeError(get_error_msg(elem, f"Unsupported ecmascript: {ecmascript}"))
    except AssertionError:
        raise RuntimeError(get_error_msg(elem, f"Assertion from ecmascript: {ecmascript}"))
    return jani_expression


def _generate_array_expression_for_assignment(
    array_info: ArrayInfo,
    parent_script: Optional[esprima.nodes.Node],
    array_values: MutableSequence,
) -> JaniExpression:
    """
    Make the JaniExpression generating the array_values to be assigned to a variable.

    :param array_info: Type and size of the array we are generating.
    :param parent_script: Reference to ecmascript AST where this is used.
    :param array_values: The values to initialize the array with (for padding).
    """
    assert isinstance(
        array_info, ArrayInfo
    ), f"Unexpected type '{type(array_info)}' for input argument 'array_info'."
    assert isinstance(
        array_values, MutableSequence
    ), f"Unexpected type '{type(array_values)}' for input argument 'array_values'."
    assert isinstance(
        parent_script, esprima.nodes.Node
    ), f"Unexpected type '{type(parent_script)}' for input argument 'parent_script'."
    # Expression for generating array are supported only for assignments (elementary expression)!
    assert parent_script.type in (Syntax.ExpressionStatement, Syntax.ArrayExpression), (
        "Error: array generators can only be used for assignments or in other array expressions "
        "(for multi-dimensional arrays): "
        f"{parent_script.type} not in (ExpressionStatement, ArrayExpression)."
    )

    array_base_type: Type[Union[int, float]] = array_info.array_type
    assert isinstance(array_info.array_max_sizes[0], int), "Unexpected error: undefined size found."
    padding_size = array_info.array_max_sizes[0] - len(array_values)
    assert (
        padding_size >= 0
    ), f"Provided array {array_values} is longer than max value: {array_info.array_max_sizes[0]}."
    padding_sizes = array_info.array_max_sizes.copy()
    padding_sizes[0] = padding_size
    the_padding = _make_padding(array_base_type, padding_sizes)
    array_values.extend(the_padding)
    return array_value_operator(array_values)


def _make_padding(array_base_type: Type[Union[int, float]], sizes: List[int]):
    """
    Recursively generates a nested list structure filled with zero values of the specified type.
    Args:
        array_base_type (Type[Union[int, float]]):
            The data type of the zero values (e.g., int or float).
        sizes (List[int]): A list of integers specifying the dimensions of the nested structure.
    Returns:
        List: A nested list filled with zero values, matching the specified dimensions.
    """
    if len(sizes) == 1:
        return [array_base_type(0)] * sizes[0]
    return [_make_padding(array_base_type, sizes[1:]) for _ in range(sizes[0])]


def _generate_constant_array_expression(
    p_node: esprima.nodes.Node, array_values: MutableSequence[Union[MutableSequence, int, float]]
) -> JaniExpression:
    # If here, we are dealing with a constant array, that can only be used for eq. checks
    assert (
        p_node.type == Syntax.BinaryExpression
    ), f"Constant string parent node is a {p_node.type} != BinaryExpression."
    assert (
        p_node.operator == "=="
    ), f"Constant strings support only the equality operator, found '{p_node.operator}'."
    return array_value_operator(array_values)


def _parse_ecmascript_to_jani_expression(
    ast: esprima.nodes.Node,
    parent_script: Optional[esprima.nodes.Node],
    array_info: Optional[ArrayInfo] = None,
) -> JaniExpression:
    """
    Parse ecmascript to jani expression.

    :param ecmascript: The ecmascript to parse.
    :param array_info: The type and max size of the array, if required.
    :return: The jani expression.
    """
    if ast.type == Syntax.ExpressionStatement:
        # This is the highest level for each esprima script
        return _parse_ecmascript_to_jani_expression(ast.expression, ast, array_info)
    elif ast.type == Syntax.Literal:
        if isinstance(ast.value, str):
            # This needs to be treated as a list (not array) of integers.
            string_as_list = convert_string_to_int_array(ast.value)
            if (
                parent_script.type == Syntax.ExpressionStatement
            ):  # This is an assignment, add padding
                return _generate_array_expression_for_assignment(
                    array_info, parent_script, string_as_list
                )
            return _generate_constant_array_expression(parent_script, string_as_list)
        else:
            return JaniExpression(JaniValue(ast.value))
    elif ast.type == Syntax.Identifier:
        # If it is an identifier, we do not need to expand further
        assert ast.name not in ("True", "False"), (
            f"Boolean {ast.name} mistaken for an identifier. "
            "Did you mean to use 'true' or 'false' instead?"
        )
        return JaniExpression(ast.name)
    elif ast.type == Syntax.UnaryExpression:
        assert ast.prefix is True, "only prefixes are supported"
        assert ast.operator in UNARY_OPERATORS_MAP, (
            f"Operator {ast.operator} is not supported. "
            + f"Only {UNARY_OPERATORS_MAP.keys()} are supported."
        )
        return UNARY_OPERATORS_MAP[ast.operator](
            _parse_ecmascript_to_jani_expression(ast.argument, ast, array_info)
        )
    elif ast.type == Syntax.BinaryExpression or ast.type == Syntax.LogicalExpression:
        # It is a more complex expression
        assert (
            ast.operator in OPERATORS_TO_JANI_MAP
        ), f"ecmascript to jani expression: unknown operator {ast.operator}"
        return JaniExpression(
            {
                "op": OPERATORS_TO_JANI_MAP[ast.operator],
                "left": _parse_ecmascript_to_jani_expression(ast.left, ast, array_info),
                "right": _parse_ecmascript_to_jani_expression(ast.right, ast, array_info),
            }
        )
    elif ast.type == Syntax.ArrayExpression:
        # This is an Array literal, will result in an array_value operator
        assert array_info is not None, "Array info must be provided for ArrayExpressions."
        entry_type: Type = array_info.array_type
        if array_info.array_dimensions == 1:
            assert all(
                element.type == Syntax.Literal for element in ast.elements
            ), "All array elements are expected to be a 'Literal'"
            elements_list = [entry_type(element.value) for element in ast.elements]
            return _generate_array_expression_for_assignment(
                array_info, parent_script, elements_list
            )
        else:  # array_info.array_dimensions > 1
            elem_exprs = []
            for elem in ast.elements:
                elem_array_info = ArrayInfo(
                    array_type=array_info.array_type,
                    array_dimensions=array_info.array_dimensions - 1,
                    array_max_sizes=array_info.array_max_sizes[1:],
                    is_base_type=array_info.is_base_type,
                )
                elem_expr = _parse_ecmascript_to_jani_expression(elem, ast, elem_array_info)
                elem_exprs.append(elem_expr)
            return _generate_array_expression_for_assignment(array_info, parent_script, elem_exprs)
    elif ast.type == Syntax.MemberExpression:
        object_expr = _parse_ecmascript_to_jani_expression(ast.object, ast, array_info)
        property_expr = _parse_ecmascript_to_jani_expression(ast.property, ast, array_info)
        if ast.computed:
            # This is an array access, like `array[0]`
            return array_access_operator(object_expr, property_expr)
        else:
            # Access to the member of an object through dot notation. Two cases:
            # 1: Generic dot notation, like `object.member`
            # 2: Length access, like `array.length` or `array[2].length`
            object_expr_str = object_expr.as_identifier()
            property_expr_str = property_expr.as_identifier()
            assert (
                property_expr_str is not None
            ), f"Unexpected value for property of {ast}. Shall be an Identifier."
            is_array_length = property_expr_str == ARRAY_LENGTH_SUFFIX
            if is_array_length:
                # We are accessing the array length information, some renaming needs to be done
                if object_expr_str is not None:
                    # Accessing array dimension at level 1
                    return JaniExpression(get_array_length_var_name(object_expr_str, 1))
                else:
                    # We need to count how many levels deep we need to go (n. of ArrayAccess)
                    return convert_array_access_to_length_access(object_expr)
            else:
                # We are accessing a generic sub-field, just re-assemble the variable name
                assert (
                    object_expr_str is not None
                ), "Only identifiers can be accessed through dot notation."
                return JaniExpression(f"{object_expr_str}.{property_expr_str}")
    elif ast.type == Syntax.CallExpression:
        # We expect function calls to be of the form Math.function_name(args) (JavaScript-like)
        # The "." operator is represented as a MemberExpression
        assert (
            ast.callee.type == Syntax.MemberExpression
        ), f"Functions callee is expected to be MemberExpressions, found {ast.callee}."
        assert (
            ast.callee.object.type == Syntax.Identifier
        ), f"Callee object is expected to be an Identifier, found {ast.callee.object}."
        assert (
            ast.callee.property.type == Syntax.Identifier
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
            expression_args.append(_parse_ecmascript_to_jani_expression(arg, ast, array_info))
        return CALLABLE_OPERATORS_MAP[function_name](*expression_args)
    else:
        raise NotImplementedError(f"Unsupported ecmascript type: {ast.type}")
