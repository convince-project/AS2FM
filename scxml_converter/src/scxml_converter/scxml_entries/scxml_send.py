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
Container for the SCXML send action, used to send events and data. In XML, it has the tag `send`.
"""

from typing import List, Optional
from scxml_converter.scxml_entries import ScxmlParam


class ScxmlSend:
    """This class represents a send action."""
    def __init__(self, event: str, target: str, params: Optional[List[ScxmlParam]] = None):
        pass

    def check_validity(self) -> bool:
        pass

    def as_xml(self):
        pass
