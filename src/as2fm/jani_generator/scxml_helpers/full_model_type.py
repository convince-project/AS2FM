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
Container to store full model
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass()
class FullModel:
    """
    A class to represent the full model.
    """

    max_time: Optional[int] = None
    max_array_size: int = field(default=100)
    bt_tick_rate: float = field(default=1.0)
    bt: Optional[str] = None
    plugins: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    components: List[str] = field(default_factory=list)
    properties: List[str] = field(default_factory=list)
