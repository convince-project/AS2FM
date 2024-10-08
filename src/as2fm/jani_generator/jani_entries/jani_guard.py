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
Guards in Jani
"""


from typing import Optional, Union

from as2fm.jani_generator.jani_entries.jani_expression import JaniExpression


class JaniGuard:

    def __init__(self, guard_exp: Optional[Union["JaniGuard", JaniExpression, dict]]):
        """
        Construct a new JaniGuard object.

        It checks against an expression that can be provided as a dict (with the 'exp' key) or a
        JaniExpression variable.

        :param guard_exp: The expression that must hold for the guard to be ok.
        """
        if guard_exp is None or isinstance(guard_exp, JaniExpression):
            self._expression = guard_exp
        elif isinstance(guard_exp, JaniGuard):
            self._expression = guard_exp._expression
        elif isinstance(guard_exp, dict):
            assert "exp" in guard_exp, "Expected guard expression to be in the 'exp' dict entry"
            self._expression = JaniExpression(guard_exp["exp"])
        else:
            raise ValueError(
                f"Unexpected guard_exp type {type(guard_exp)}. "
                "Should be None, JaniExpression or Dict."
            )

    def get_expression(self) -> Optional[JaniExpression]:
        return self._expression

    def as_dict(self, _: Optional[dict] = None):
        d = {}
        if self._expression:
            exp = self._expression.as_dict()
            if isinstance(exp, dict) and list(exp.keys()) == ["exp"]:
                d["exp"] = exp["exp"]
            else:
                d["exp"] = exp
        return d
