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

from typing import Dict, List, Optional, Union

import escodegen
import esprima
from esprima.syntax import Syntax
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.ecmascript_interpretation_functions import (
    ValidECMAScriptTypes,
    get_ast_expression_type,
    get_dict_from_object_expression,
    get_list_from_array_expr,
)
from as2fm.as2fm_common.logging import check_assertion, get_error_msg


class ArrayAccess:
    """
    Placeholder type for ArrayAccess operator call in expanded Member expression.

    Check the function `split_by_access` for more information.
    """

    pass


class MemberAccessCheckException(Exception):
    """Exception type thrown when there are error expanding a Member expression."""

    pass


def parse_expression_to_ast(expression: str, elem: XmlElement) -> esprima.nodes.Node:
    """
    Parse the string using `esprima`. Return the AST of it's main body.

    AST = Abstract Syntax Tree
    """
    assert isinstance(expression, str), f"Provided esprima expr is {type(expression)} != string."

    # Adding a variable, because bare object declarations don't seem to work.
    expression = f"value = {expression}"
    try:
        ast = esprima.parseScript(expression)
    except esprima.error_handler.Error as e:
        raise RuntimeError(
            get_error_msg(elem, f"Failed parsing ecmascript: {expression}. Error: {e}.")
        )

    check_assertion(len(ast.body) == 1, elem, "The ecmascript must contain exactly one expression.")
    ast = ast.body[0]

    # remove the 'value ='-bit' we added above
    check_assertion(
        ast.type == "ExpressionStatement",
        elem,
        "The ecmascript must contain exactly one expression.",
    )
    ast = ast.expression
    check_assertion(
        ast.left.type == "Identifier",
        elem,
        "Assuming an identifier.",
    )
    check_assertion(
        ast.left.name == "value",
        elem,
        "Assuming the identifier to be 'value'.",
    )
    return ast.right


def parse_ecmascript_expr_to_type(
    expr: str, variables: Dict[str, ValidECMAScriptTypes], elem: Optional[XmlElement] = None
):
    """Interpret a string of ecmacript expression and get the type that is evaluates to."""
    ast_node = parse_expression_to_ast(expr, elem)
    return get_ast_expression_type(ast_node, variables)


def make_ast_array_expression(in_array: List) -> esprima.nodes.ArrayExpression:
    """Helper function to generate an empty array expression."""
    return esprima.nodes.ArrayExpression(in_array)


def get_array_expr_as_list(expr: str, elem: Optional[XmlElement] = None) -> List:
    """Reads a string as an EcmaScript expression and returns it as an ArrayExpression."""
    ast_node = parse_expression_to_ast(expr, elem)
    if ast_node.type == Syntax.ArrayExpression:
        # We expect no variable reference in an array expression, hence the '{}'
        return get_list_from_array_expr(ast_node)
    elif ast_node.type == Syntax.Literal:  # a string
        raise ValueError(f"This should not be a string: {expr}")
    else:
        raise ValueError(f"This was expected to be an array expression: {expr}")


def get_object_expression_as_dict(
    expr: str, elem: Optional[XmlElement] = None
) -> Dict[str, Union[Dict, List, esprima.nodes.Node]]:
    """Reads a string as an EcmaScript expression and returns it as a Dict of ast expressions."""
    ast_node = parse_expression_to_ast(expr, elem)
    return get_dict_from_object_expression(ast_node)


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


def ast_expression_to_string(ast_node: esprima.nodes.Node) -> str:
    """Generate a string starting from an AST node"""
    return escodegen.generate(ast_node)
