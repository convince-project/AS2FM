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

from typing import List, Optional, Type, Union

import esprima
from esprima.syntax import Syntax
from lxml.etree import _Element as XmlElement

from moco.moco_common.ecmascript_interpretation_functions import (
    get_ast_expression_type,
    get_list_from_array_expr,
)
from moco.moco_common.logging import check_assertion, get_error_msg
from moco.roaml_generator.jani_entries.jani_convince_expression_expansion import (
    CALLABLE_OPERATORS_MAP,
    OPERATORS_TO_JANI_MAP,
    UNARY_OPERATORS_MAP,
)
from moco.roaml_generator.jani_entries.jani_expression import JaniExpression
from moco.roaml_generator.jani_entries.jani_expression_generator import (
    array_access_operator,
    array_value_operator,
)
from moco.roaml_generator.jani_entries.jani_value import JaniValue
from moco.roaml_converter.data_types.type_utils import ARRAY_LENGTH_SUFFIX, ArrayInfo

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
    ecmascript: str,
    elem: Optional[XmlElement],
    target_array_info: Optional[ArrayInfo] = None,
) -> JaniExpression:
    """
    Parse ecmascript to jani expression.

    :param ecmascript: The ecmascript to parse.
    :param elem: The xml element associated to the expression, for error logging.
    :param target_array_info: The array info required by the target variable (if any).

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
        jani_expression = _parse_ecmascript_to_jani_expression(ast, target_array_info)
    except NotImplementedError as e:
        raise RuntimeError(get_error_msg(elem, f"Unsupported ecmascript '{ecmascript}': {e}"))
    except AssertionError as e:
        raise RuntimeError(get_error_msg(elem, f"Assertion from ecmascript '{ecmascript}': {e}"))
    return jani_expression


def _add_padding_to_array(
    in_list: List[Union[int, float, List]], array_info: ArrayInfo
) -> List[Union[int, float, List]]:
    """
    Add elements to the input list, such that the number of elements match the expected size.

    :param in_list: The list that requires padding.
    :array_info: The information required to determine the expected sizes.
    """
    expected_shape: List[int] = array_info.array_max_sizes
    expected_type: Type[Union[int, float]] = array_info.array_type
    return _pad_list_recursive(in_list, expected_shape, expected_type)


def _pad_list_recursive(
    in_list: List[Union[int, float, List]], shape: List[int], entry_type: Type[Union[int, float]]
):
    """The recursive implementation of the padding functionality."""
    curr_size = shape[0]
    assert isinstance(curr_size, int), f"Unexpected array size found: {curr_size} is not an int."
    assert isinstance(in_list, list), f"Unexpected input list: {in_list} is not a list."
    len_padding = curr_size - len(in_list)
    assert len_padding >= 0, "Input list is larger than the expected max. dimension."
    if len(shape) == 1:
        return in_list + [entry_type(0)] * len_padding
    # If here, we have a multi-dimensional array: just append empty lists and fill them afterwards
    padded_list = in_list + [[]] * len_padding
    # Now, extend this list!
    return [_pad_list_recursive(lst_entry, shape[1:], entry_type) for lst_entry in padded_list]


def _parse_ecmascript_to_jani_expression(
    ast: esprima.nodes.Node,
    target_array_info: Optional[ArrayInfo],
) -> JaniExpression:
    """
    Parse ecmascript to jani expression.

    :param ast: The AST expression to convert.
    :param target_array_info: ArrayInfo related to target variable (if defined)
    :return: The jani expression.
    """
    if ast.type == Syntax.ExpressionStatement:
        # This is the highest level for each esprima script
        return _parse_ecmascript_to_jani_expression(ast.expression, target_array_info)
    elif ast.type == Syntax.Literal:
        if isinstance(ast.value, str):
            raise RuntimeError("This should not contain string expressions any more.")
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
            _parse_ecmascript_to_jani_expression(ast.argument, target_array_info)
        )
    elif ast.type == Syntax.BinaryExpression or ast.type == Syntax.LogicalExpression:
        # It is a more complex expression
        assert (
            ast.operator in OPERATORS_TO_JANI_MAP
        ), f"ecmascript to jani expression: unknown operator {ast.operator}"
        return JaniExpression(
            {
                "op": OPERATORS_TO_JANI_MAP[ast.operator],
                "left": _parse_ecmascript_to_jani_expression(ast.left, target_array_info),
                "right": _parse_ecmascript_to_jani_expression(ast.right, target_array_info),
            }
        )
    elif ast.type == Syntax.ArrayExpression:
        # This is an Array literal, will result in an array_value operator
        array_entries_info = get_ast_expression_type(ast, {})
        assert isinstance(array_entries_info, ArrayInfo), "Unexpected type extracted from AST expr."
        assert array_entries_info.array_type in (int, float, None), "Unexpected array type."
        expected_type: Optional[Type[Union[int, float]]] = array_entries_info.array_type
        if target_array_info is not None:
            # If target type is float, we are ok with everything
            # If entries type is int or None, we are OK with everything as well
            assert target_array_info.array_type is float or array_entries_info.array_type in (
                int,
                None,
            ), "The target var and the expr. type are not compatible."
            expected_type = target_array_info.array_type
        extracted_list = get_list_from_array_expr(ast, expected_type)
        if target_array_info is not None:
            extracted_list = _add_padding_to_array(extracted_list, target_array_info)
        return array_value_operator(extracted_list)
    elif ast.type == Syntax.MemberExpression:
        object_expr = _parse_ecmascript_to_jani_expression(ast.object, target_array_info)
        property_expr = _parse_ecmascript_to_jani_expression(ast.property, target_array_info)
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
            expression_args.append(_parse_ecmascript_to_jani_expression(arg, target_array_info))
        return CALLABLE_OPERATORS_MAP[function_name](*expression_args)
    else:
        raise NotImplementedError(f"Unsupported ecmascript type: {ast.type}")
