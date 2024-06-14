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

from xml.etree import ElementTree as ET


class ScxmlSend:
    """This class represents a send action."""
    def __init__(self, event: str, target: str, params: Optional[List[ScxmlParam]] = None):
        self._event = event
        self._target = target
        self._params = params

    def check_validity(self) -> bool:
        valid_event = isinstance(self._event, str) and len(self._event) > 0
        valid_target = isinstance(self._target, str) and len(self._target) > 0
        valid_params = True
        if self._params is not None:
            for param in self._params:
                valid_param = isinstance(param, ScxmlParam) and param.check_validity()
                valid_params = valid_params and valid_param
        if not valid_event:
            print("Error: SCXML send: event is not valid.")
        if not valid_target:
            print("Error: SCXML send: target is not valid.")
        if not valid_params:
            print("Error: SCXML send: one or more param entries are not valid.")
        return valid_event and valid_target and valid_params

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid send object."
        xml_send = ET.Element('send', {"event": self._event, "target": self._target})
        if self._params is not None:
            for param in self._params:
                xml_send.append(param.as_xml())
        return xml_send
