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
A single state in SCXML. In XML, it has the tag `state`.
"""

from typing import List, Optional

from scxml_converter.scxml_entries import ScxmlExecutableEntries, ScxmlTransition


class ScxmlState:
    """This class represents a single scxml state."""
    def __init__(self, *,
                 on_entry: Optional[List[ScxmlExecutableEntries]] = None,
                 on_exit: Optional[List[ScxmlExecutableEntries]] = None,
                 body: Optional[List[ScxmlTransition]] = None):
        self._on_entry = on_entry
        self._on_exit = on_exit
        self._body = body

    def check_validity(self) -> bool:
        pass

    def as_xml(self):
        pass
