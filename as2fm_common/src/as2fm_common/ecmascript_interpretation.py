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

from typing import Dict, Optional, Union

import js2py

from as2fm_common.common import ValidTypes


BASIC_JS_TYPES = Union[int, float, str, bool]


def interpret_ecma_script_expr(
        expr: str, variables: Optional[Dict[str, ValidTypes]] = None) -> object:
    """
    Interpret the ECMA script expression.

    :param expr: The ECMA script expression
    :return: The interpreted object
    """
    if variables is None:
        variables = {}
    context = js2py.EvalJs(variables)
    context.execute("result = " + expr)
    expr_result = context.result
    if isinstance(expr_result, BASIC_JS_TYPES):
        return expr_result
    assert isinstance(expr_result, js2py.base.JsObjectWrapper), \
        f"Expected expr. {expr} to be of type {BASIC_JS_TYPES} or JsObjectWrapper, " \
        f"got '{type(expr_result)}'"
    # For now, we expect everything that is not a base type to be a list
    return expr_result.to_list()
