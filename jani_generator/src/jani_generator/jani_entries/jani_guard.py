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


from typing import Optional

from jani_generator.jani_entries.jani_expression import JaniExpression


class JaniGuard:
    def __init__(self, expression: Optional[JaniExpression]):
        self.expression = expression

    def as_dict(self, constants: Optional[dict] = None):
        d = {}
        if self.expression:
            exp = self.expression.as_dict()
            if (isinstance(exp, dict) and list(exp.keys()) == ['exp']):
                d['exp'] = exp['exp']
            else:
                d['exp'] = exp
        return d
