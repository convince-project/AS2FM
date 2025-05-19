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

from typing import Any, Dict, List, Optional, Union, get_args

import esprima
import STPyV8
from esprima.syntax import Syntax
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.common import ValidScxmlTypes
from as2fm.as2fm_common.logging import check_assertion, get_error_msg

BasicJsTypes = Union[int, float, bool, str]


class ArrayAccess:
    """
    Placeholder type for ArrayAccess operator call in expanded Member expression.

    Check the function 'split_by_access' for more information.
    """

    pass


class MemberAccessCheckException(Exception):
    """Exception type thrown when there are error expanding a Member expression."""

    pass


def __evaluate_js_variable_content(js_variable: Any) -> Any:
    """Extract the result from the JS Context variable"""
    if isinstance(js_variable, get_args(BasicJsTypes)):
        return js_variable
    # Here consider both STPyV8.JSArray and list, since the type depends on the context variables.
    if isinstance(js_variable, (STPyV8.JSArray, list)):
        return __evaluate_js_var_as_list(js_variable)
    if isinstance(js_variable, STPyV8.JSObject):
        return __evaluate_js_var_as_dict(js_variable)
    raise ValueError(f"Cannot evaluate input JS var. {js_variable}")


def __evaluate_js_var_as_list(js_variable: Any) -> List[Any]:
    assert isinstance(js_variable, (STPyV8.JSArray, list))
    return [__evaluate_js_variable_content(x) for x in js_variable]


def __evaluate_js_var_as_dict(js_variable: Any) -> Dict[str, Any]:
    assert isinstance(js_variable, STPyV8.JSObject)
    obj_keys = js_variable.keys()
    return {k: __evaluate_js_variable_content(js_variable[k]) for k in obj_keys}


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
    expr: str, variables: Dict[str, ValidScxmlTypes]
) -> Union[ValidScxmlTypes, dict]:
    """
    Process a JS expression and return the resulting value.

    :param expr: The ECMA script expression to evaluate.
    :param variables: A dictionary of variables to be used in the ECMA script context.
    """
    with STPyV8.JSContext(variables) as context:
        try:
            context.eval(f"result = {expr}")
        except Exception:
            msg_addition = ""
            if expr in ("True", "False"):
                msg_addition = "Did you mean to use 'true' or 'false' instead?"
            raise RuntimeError(
                f"Failed to interpret JS expression using variables {variables}: ",
                f"'result = {expr}'. {msg_addition}",
            )
        return __evaluate_js_variable_content(context.locals.result)


def interpret_ecma_script_expr(
    expr: str,
    variables: Optional[Dict[str, ValidScxmlTypes]] = None,
    allow_dict_results: bool = False,
) -> Union[ValidScxmlTypes, dict]:
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
    `a[3].b` => `['a', ArrayAccess, 'b']
    """
    ast = parse_expression_to_ast(expr, elem)
    try:
        return _split_by_access(ast)
    except MemberAccessCheckException as e:
        print(get_error_msg(elem, e.args[0]))
        raise e


def _split_by_access(ast: esprima.nodes.Node) -> List:
    """Recursive implementation of 'split_by_access' functionality."""
    if ast.type == Syntax.Identifier:
        return [ast.name]
    elif ast.type == Syntax.MemberExpression:
        if ast.computed:  # array access
            return _split_by_access(ast.object) + [ArrayAccess]
        else:  # member access
            return _split_by_access(ast.object) + _split_by_access(ast.property)
    else:
        raise MemberAccessCheckException(f"Can not evaluate {ast.type} to a variable identifier.")
