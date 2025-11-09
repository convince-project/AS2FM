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
Complete Jani Model
"""


from typing import Dict, List, Optional, Type, Union

from moco.moco_common.array_type import ArrayInfo
from moco.roaml_generator.jani_entries import (
    JaniAutomaton,
    JaniComposition,
    JaniConstant,
    JaniExpression,
    JaniProperty,
    JaniValue,
    JaniVariable,
)

ValidValue = Union[int, float, bool, dict, JaniExpression]

