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
A single transition in SCXML. In XML, it has the tag `transition`.
"""

from typing import List, Optional

from scxml_converter.scxml_entries import ScxmlExecutableEntries


class ScxmlTransition:
    """This class represents a single scxml state."""
    def __init__(self,
                 target: str, events: Optional[List[str]] = None,
                 condition: Optional[str] = None,
                 body: Optional[List[ScxmlExecutableEntries]] = None):
        """
        Generate a new transition. Currently, transitions must have a target.

        :param target: The target state of the transition. Unlike in SCXML specifications, this is required
        :param events: The events that trigger this transition.
        :param condition: The condition guard to enable/disable the transition
        :param body: Content that is executed when the transition happens
        """
        self._target = target
        self._body = body
        self._events = events
        self._condition = condition

    def check_validity(self) -> bool:
        pass

    def as_xml(self):
        pass
