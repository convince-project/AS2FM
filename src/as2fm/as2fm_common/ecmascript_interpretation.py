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

from typing import Dict, List, Optional, Type, Union, get_args

import esprima
from esprima.syntax import Syntax
from lxml.etree import _Element as XmlElement

from as2fm.as2fm_common.array_type import ArrayInfo, array_value_to_type_info
from as2fm.as2fm_common.common import (
    ValidPlainScxmlTypes,
)
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
    assert isinstance(expression, str), f"Provided esprima expr is {type(expression)} != string."
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


def __get_ast_literal_type(ast: esprima.nodes.Node) -> Union[Type[ValidPlainScxmlTypes], ArrayInfo]:
    """Extract the type of a literal node. Special handling for floats."""
    assert ast.type == Syntax.Literal
    extracted_type = type(ast.value)
    if extracted_type not in (int, float, bool, str):
        raise ValueError(f"Unexpected literal type {extracted_type}.")
    if extracted_type is str:
        return ArrayInfo(int, 1, [None])
    n_dots = ast.raw.count(".")
    if extracted_type is int and n_dots > 0:
        assert n_dots == 1, f"Unexpected literal's raw string {ast.raw}."
        return float
    return extracted_type


def __get_list_from_array_expr_type(ast: esprima.nodes.Node) -> List:
    ret_list = []
    for elem in ast.elements:
        if elem.type == Syntax.Literal:
            lit_type = __get_ast_literal_type(elem)
            assert lit_type in (
                int,
                float,
            ), f"Found entry of type {lit_type}. Only arrays of int and floats are supported."
            ret_list.append(lit_type(elem.value))
        elif elem.type == Syntax.ArrayExpression:
            ret_list.append(__get_list_from_array_expr_type(elem))
    return ret_list


def __get_ast_array_expr_type(ast: esprima.nodes.Node) -> ArrayInfo:
    assert ast.type == Syntax.ArrayExpression
    converted_array = __get_list_from_array_expr_type(ast)
    return array_value_to_type_info(converted_array)


def __get_member_access_name(ast: esprima.nodes.Node) -> str:
    """Compute the name resulting from a non-computed MemberExpression."""
    assert ast.type == Syntax.MemberExpression and not ast.computed
    member_obj_name: str = ""
    if ast.object.type == Syntax.Identifier:
        member_obj_name = ast.object.name
    else:
        member_obj_name = __get_member_access_name(ast.object)
    member_prop_name: str = ""
    if ast.property.type == Syntax.Identifier:
        member_prop_name = ast.property.name
    else:
        member_prop_name = __get_member_access_name(ast.property)
    return f"{member_obj_name}.{member_prop_name}"


def __get_member_access_array(
    ast: esprima.nodes.Node, variables: Dict[str, Union[Type[ValidPlainScxmlTypes], ArrayInfo]]
) -> Union[Type[ValidPlainScxmlTypes], ArrayInfo]:
    """
    Compute the type resulting from an array access operator.

    Note: In this functions, we assume that all array access operators are at the end.
    E.g. obj.some_array[0][1][2] and not obj_array[0].something[1].x[2]
    """
    assert ast.type == Syntax.MemberExpression and ast.computed
    depth = 1
    curr_ast = ast.object
    while curr_ast.type != Syntax.Identifier:
        assert curr_ast.type == Syntax.MemberExpression and curr_ast.computed
        curr_ast = curr_ast.object
        depth += 1
    var_type = variables[curr_ast.name]
    assert isinstance(var_type, ArrayInfo), f"{var_type=} != ArrayInfo."
    if depth == var_type.array_dimensions:
        return var_type.array_type
    elif depth < var_type.array_dimensions:
        return ArrayInfo(
            var_type.array_type, var_type.array_dimensions - depth, var_type.array_max_sizes[depth:]
        )
    raise RuntimeError(
        f"Invalid array access: trying to access the {depth}-th dim. "
        f"of a {var_type.array_dimensions}-dim array."
    )


def __get_call_expr_type(
    ast: esprima.nodes.Node, variables: Dict[str, Union[Type[ValidPlainScxmlTypes], ArrayInfo]]
) -> Type[ValidPlainScxmlTypes]:
    assert ast.type == Syntax.CallExpression
    callee_str: str = ""
    if ast.callee.type == Syntax.Identifier:
        callee_str = ast.callee.name
    else:
        callee_str = __get_member_access_name(ast.callee)
    if callee_str in ("Math.cos", "Math.sin", "Math.log", "Math.pow", "Math.random"):
        return float
    elif callee_str in ("Math.floor", "Math.ceil"):
        return int
    elif callee_str in ("Math.abs", "Math.min", "Math.max"):
        found_type: Optional[Union[Type[int], Type[float]]] = None
        for callee_arg in ast.arguments:
            arg_type = __get_ast_expression_type(callee_arg, variables)
            assert arg_type in (int, float)
            if found_type is not float:
                found_type = arg_type
        assert found_type is not None
        return found_type
    raise RuntimeError(f"Unknown function in expression: {callee_str}.")


def __get_unary_expr_type(
    ast: esprima.nodes.Node, variables: Dict[str, Union[Type[ValidPlainScxmlTypes], ArrayInfo]]
) -> Type[ValidPlainScxmlTypes]:
    assert ast.type == Syntax.UnaryExpression
    assert ast.prefix is True
    op_arg_type = __get_ast_expression_type(ast.argument, variables)
    op = ast.operator
    if op == "-":
        assert op_arg_type in (int, float)
        return op_arg_type
    elif op == "!":
        assert op_arg_type is bool
        return op_arg_type
    raise RuntimeError(f"Unexpected unary operator. '{op}' not in ('-', '!').")


def __get_binary_expr_type(
    ast: esprima.nodes.Node, variables: Dict[str, Union[Type[ValidPlainScxmlTypes], ArrayInfo]]
) -> Type[ValidPlainScxmlTypes]:
    assert ast.type == Syntax.BinaryExpression
    left_type = __get_ast_expression_type(ast.left, variables)
    right_type = __get_ast_expression_type(ast.right, variables)
    op = ast.operator

    # Arithmetic operators
    if op in ("+", "-", "*", "/", "%", "**"):
        # If either side is float, result is float
        if float in (left_type, right_type):
            return float
        # Both int
        return int

    # Comparison operator
    if op in (">", ">=", "<", "<=", "==", "!="):
        return bool

    raise ValueError(f"Unknown binary operator: {op}")


def __get_ast_expression_type(
    ast: esprima.nodes.Node, variables: Dict[str, Union[Type[ValidPlainScxmlTypes], ArrayInfo]]
) -> Union[Type[ValidPlainScxmlTypes], ArrayInfo]:
    if ast.type == Syntax.Literal:
        return __get_ast_literal_type(ast)
    elif ast.type == Syntax.Identifier:
        return variables[ast.name]
    elif ast.type == Syntax.ArrayExpression:
        return __get_ast_array_expr_type(ast)
    elif ast.type == Syntax.MemberExpression:
        if ast.computed:
            # Array Access Operator
            return __get_member_access_array(ast, variables)
        else:
            # Member access operator, treat it like an identifier
            return variables[__get_member_access_name(ast)]
    elif ast.type == Syntax.CallExpression:
        return __get_call_expr_type(ast, variables)
    elif ast.type == Syntax.LogicalExpression:
        assert __get_ast_expression_type(ast.left, variables) is bool
        assert __get_ast_expression_type(ast.right, variables) is bool
        return bool
    elif ast.type == Syntax.BinaryExpression:
        return __get_binary_expr_type(ast, variables)
    elif ast.type == Syntax.UnaryExpression:
        return __get_unary_expr_type(ast, variables)
    else:
        raise ValueError(f"Unknown ast type {ast.type}")


# TODO: Turn the variables into a name->type map, instead of name->instance.
def get_ast_expression_type(
    ast: esprima.nodes.Node, variables: Dict[str, ValidPlainScxmlTypes]
) -> Union[Type[ValidPlainScxmlTypes], ArrayInfo]:
    """TODO"""
    # var_to_type = {
    #     var_name: __extract_type_from_instance(var_value)
    #     for var_name, var_value in variables.items()
    # }
    return __get_ast_expression_type(ast, variables)


def parse_ecmascript_expr_to_type(
    expr: str, variables: Dict[str, ValidPlainScxmlTypes], elem: Optional[XmlElement] = None
):
    """Interpret a string of ecmacript expression and get the type that is evaluates to."""
    ast_node = parse_expression_to_ast(expr, elem)
    return get_ast_expression_type(ast_node, variables)


def get_array_expr_as_list(expr: str, elem: Optional[XmlElement] = None) -> List:
    """Reads a string as a, EcmaScript expression and returns it as an ArrayExpression."""
    ast_node = parse_expression_to_ast(expr, elem)
    if ast_node.type == Syntax.ArrayExpression:
        return __get_list_from_array_expr_type(ast_node)
    elif ast_node.type == Syntax.Literal:  # a string
        raise ValueError(f"This should not be a string: {expr}")
    else:
        raise ValueError(f"This was expected to be an array expression: {expr}")


def _get_variable_instances(variables):
    out_d = {}
    for name, type in variables.items():
        if type in get_args(ValidPlainScxmlTypes):
            out_d[name] = type()
        elif isinstance(type, dict):
            out_d[name] = _get_variable_instances(type)
        else:
            raise RuntimeError(f"Unsupported type {type}.")
    return out_d


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
