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

from array import array
from typing import Dict, Optional, Union, get_args

import js2py

from as2fm.as2fm_common.common import ValidScxmlTypes

BasicJsTypes = Union[int, float, bool, str]


def _interpret_ecmascript_expr(
    expr: str, variables: Dict[str, ValidScxmlTypes]
) -> Union[ValidScxmlTypes, js2py.base.JsObjectWrapper]:
    """
    Process a JS expression and return the resulting outcome.

    :param expr: The ECMA script expression to evaluate.
    :param variables: A dictionary of variables to be used in the ECMA script context.
    """
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
        if isinstance(expr_result._obj, js2py.base.PyJsArray):
            res_as_list = expr_result.to_list()
            if all(isinstance(x, int) for x in res_as_list):
                return array("i", res_as_list)
            else:
                return array("d", res_as_list)
        else:
            return expr_result
    elif isinstance(expr_result, array):
        return expr_result
    else:
        raise ValueError(
            f"Expected expr. {expr} to be of type {BasicJsTypes} or "
            f"JsObjectWrapper, got '{type(expr_result)}'"
        )


def interpret_ecma_script_expr(
    expr: str, variables: Optional[Dict[str, ValidScxmlTypes]] = None
) -> ValidScxmlTypes:
    """
    Interpret the ECMA script expression. Return it only if result compatible with plain SCXML.

    :param expr: The ECMA script expression
    :param variables: A dictionary of variables to be used in the ECMA script context
    :return: The interpreted object
    """
    if variables is None:
        variables = {}
    expr_result = _interpret_ecmascript_expr(expr, variables)
    if isinstance(expr_result, js2py.base.JsObjectWrapper):
        raise ValueError(
            f"Expected expr. {expr} to be of type {BasicJsTypes} or "
            f"an array, got '{type(expr_result._obj)}'"
        )
    return expr_result


def interpret_non_base_ecma_script_expr(
    expr: str, variables: Optional[Dict[str, ValidScxmlTypes]] = None
) -> Union[ValidScxmlTypes, js2py.base.JsObjectWrapper]:
    """
    Interpret the ECMA script expression. Returns also complex objects.

    :param expr: The ECMA script expression
    :param variables: A dictionary of variables to be used in the ECMA script context
    :return: The interpreted object
    """
    if variables is None:
        variables = {}
    return _interpret_ecmascript_expr(expr, variables)
