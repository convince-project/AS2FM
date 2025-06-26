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
Module for interpreting ecmascript.
"""

from typing import Dict, List, Optional, Union, get_args

import esprima
import js2py
from esprima.syntax import Syntax
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import ValidPlainScxmlTypes
from as2fm.as2fm_common.logging import check_assertion, get_error_msg

BasicJsTypes = Union[int, float, bool, str]


class ArrayAccess:
    """
    Placeholder type for ArrayAccess operator call in expanded Member expression.

    Check the function `split_by_access` for more information.
    """

    pass


class MemberAccessCheckException(Exception):
    """Exception type thrown when there are error expanding a Member expression."""

    pass


def parse_expression_to_ast(expression: str, elem: XmlElement):
    """
    Parse the string using `esprima`. Return the AST of it's main body.

    AST = Abstract Syntax Tree
    """
    try:
        ast = esprima.parseScript(expression)
    except esprima.error_handler.Error as e:
        raise RuntimeError(
            get_error_msg(elem, f"Failed parsing ecmascript: {expression}. Error: {e}.")
        )
    check_assertion(len(ast.body) == 1, elem, "The ecmascript must contain exactly one expression.")
    ast = ast.body[0]
    check_assertion(
        ast.type == "ExpressionStatement",
        elem,
        "The ecmascript must contain exactly one expression.",
    )
    return ast.expression


def _interpret_ecmascript_expr(
    expr: str, variables: Dict[str, ValidPlainScxmlTypes]
) -> Union[ValidPlainScxmlTypes, dict]:
    """
    Process a JS expression and return the resulting value.

    :param expr: The ECMA script expression to evaluate.
    :param variables: A dictionary of variables to be used in the ECMA script context.
    """
    # TODO: This is so hacky that we wanna cry
    current_float = 0.3
    for key in variables:
        if isinstance(variables[key], float):
            # Just a number to ensure we don't end up with an integer
            current_float += 0.01
            variables[key] = current_float
    context = js2py.EvalJs(variables)
    try:
        context.execute("result = " + expr)
    except js2py.base.PyJsException:
        msg_addition = ""
        if expr in ("True", "False"):
            msg_addition = "Did you mean to use 'true' or 'false' instead?"
        raise RuntimeError(
            f"Failed to interpret JS expression using variables {variables}: ",
            f"'result = {expr}'. {msg_addition}",
        )
    expr_result = context.result
    if isinstance(expr_result, get_args(BasicJsTypes)):
        return expr_result
    elif isinstance(expr_result, js2py.base.JsObjectWrapper):
        # This is just to control the 1st operation to execute. All others are done recursively.
        if isinstance(expr_result._obj, js2py.base.PyJsArray):
            return expr_result.to_list()
        else:
            return expr_result.to_dict()
    else:
        raise ValueError(
            f"Expected expr. {expr} to be of type {BasicJsTypes} or "
            f"JsObjectWrapper, got '{type(expr_result)}'"
        )


def interpret_ecma_script_expr(
    expr: str,
    variables: Optional[Dict[str, ValidPlainScxmlTypes]] = None,
    allow_dict_results: bool = False,
) -> Union[ValidPlainScxmlTypes, dict]:
    """
    Interpret the ECMA script expression and return the resulting value.

    :param expr: The ECMA script expression
    :param variables: A dictionary of variables to be used in the ECMA script context
    :param allow_dict_results: Whether the result of the expr. can be an object (encoded by a dict)
    :return: The interpreted object
    """
    if variables is None:
        variables = {}
    expr_result = _interpret_ecmascript_expr(expr, variables)
    if not allow_dict_results and isinstance(expr_result, dict):
        raise ValueError(
            f"Expected expr. {expr} to be of type {BasicJsTypes} or a list, got a dictionary."
        )
    return expr_result


def has_array_access(expr: str, elem: Optional[XmlElement]) -> bool:
    """Evaluate if an ECMAscript expression contains access to an array element.

    Note: This works only if the expression evaluates to a variable (base type, custom struct or
    array).
    """
    ast = parse_expression_to_ast(expr, elem)
    try:
        return _has_member_or_array_access(ast, True)
    except MemberAccessCheckException as e:
        print(get_error_msg(elem, e.args[0]))
        raise e


def has_member_access(expr: str, elem: Optional[XmlElement]) -> bool:
    """Evaluate if an ECMAscript expression contains access to an member element.

    Note: This works only if the expression evaluates to a variable (base type, custom struct or
    array).
    """
    ast = parse_expression_to_ast(expr, elem)
    try:
        return _has_member_or_array_access(ast, False)
    except MemberAccessCheckException as e:
        print(get_error_msg(elem, e.args[0]))
        raise e


def has_operators(expr: str, elem: Optional[XmlElement]) -> bool:
    """
    Evaluate if an ECMAscript expression contains unary, binary, logical or function operators.
    """
    ast = parse_expression_to_ast(expr, elem)
    return _has_operators(ast, elem)


def is_literal(expr: str, elem: Optional[XmlElement]) -> bool:
    """Evaluate if the expression contains only a literal (or an array expression)."""
    ast = parse_expression_to_ast(expr, elem)
    return ast.type in (Syntax.Literal, Syntax.ArrayExpression)


def _has_member_or_array_access(ast: esprima.nodes.Node, array_access: bool) -> bool:
    """Evaluate if an ast node contains access to an array element.

    Note: This works only if the expression evaluates to a variable (base type, custom struct or
    array).

    :param ast: The ecmascript AST node to parse.
    :param array_access: `True` if looking for array index, `False` for member access (computed).
    :return: The jani expression.
    """
    if ast.type == Syntax.Identifier:
        return False
    elif ast.type == Syntax.MemberExpression:
        if ast.computed == array_access:  # The type of access we are interested in.
            return True
        else:  # *Not* the type of access we are interested in.
            return _has_member_or_array_access(ast.object, array_access)
    else:
        raise MemberAccessCheckException(f"Can not evaluate {ast.type} to a variable identifier.")


def _has_operators(ast: esprima.nodes.Node, elem: Optional[XmlElement]) -> bool:
    """Check if we can find a unary, binary, logical or function operator in the AST."""
    if ast.type in (
        Syntax.UnaryExpression,
        Syntax.BinaryExpression,
        Syntax.CallExpression,
        Syntax.LogicalExpression,
    ):
        return True
    elif ast.type in (Syntax.Identifier, Syntax.Literal, Syntax.MemberExpression):
        # We do not care of operators used as array access index
        return False
    else:
        raise NotImplementedError(get_error_msg(elem, f"Unhandled expression type: {ast.type}"))


def split_by_access(expr: str, elem: Optional[XmlElement]) -> List[Union[str, ArrayAccess]]:
    """
    Expand a Member expression into a list, distinguishing between member and array accesses.

    Examples:
    `a.b` => `['a', 'b']
    `a[3].b` => `['a', ArrayAccess, 'b']`
    """
    ast = parse_expression_to_ast(expr, elem)
    try:
        return _split_by_access(ast)
    except MemberAccessCheckException as e:
        print(get_error_msg(elem, e.args[0]))
        raise e


def _split_by_access(ast: esprima.nodes.Node) -> List:
    """Recursive implementation of `split_by_access` functionality."""
    if ast.type == Syntax.Identifier:
        return [ast.name]
    elif ast.type == Syntax.MemberExpression:
        if ast.computed:  # array access
            return _split_by_access(ast.object) + [ArrayAccess]
        else:  # member access
            return _split_by_access(ast.object) + _split_by_access(ast.property)
    else:
        raise MemberAccessCheckException(f"Can not evaluate {ast.type} to a variable identifier.")
