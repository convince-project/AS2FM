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
from scxml_converter.scxml_entries import (ScxmlExecutionBody, ScxmlExecutableEntries,
                                           valid_execution_body)

from xml.etree import ElementTree as ET


class ScxmlTransition:
    """This class represents a single scxml state."""
    def __init__(self,
                 target: str, events: Optional[List[str]] = None, condition: Optional[str] = None,
                 body: Optional[ScxmlExecutionBody] = None):
        """
        Generate a new transition. Currently, transitions must have a target.

        :param target: The target state of the transition. Unlike in SCXML specifications, this is required
        :param events: The events that trigger this transition.
        :param condition: The condition guard to enable/disable the transition
        :param body: Content that is executed when the transition happens
        """
        assert isinstance(target, str) and len(target) > 0, "Error SCXML transition: target must be a non-empty string."
        assert events is None or (isinstance(events, list) and
                                  all((isinstance(event, str) and len(event) > 0) for event in events)), \
            "Error SCXML transition: events must be a list of non-empty strings."
        assert condition is None or (isinstance(condition, str) and len(condition) > 0), \
            "Error SCXML transition: condition must be a non-empty string."
        assert body is None or valid_execution_body(body), "Error SCXML transition: invalid body provided."
        self._target = target
        self._body = body
        self._events = events
        self._condition = condition

    def add_event(self, event: str):
        if self._events is None:
            self._events = []
        self._events.append(event)

    def append_body_executable_entry(self, exec_entry: ScxmlExecutableEntries):
        if self._body is None:
            self._body = []
        self._body.append(exec_entry)
        assert valid_execution_body(self._body), \
            "Error SCXML transition: invalid body after extension."

    def check_validity(self) -> bool:
        valid_target = isinstance(self._target, str) and len(self._target) > 0
        valid_events = self._events is None or \
            (isinstance(self._events, list) and all(isinstance(event, str) for event in self._events))
        valid_condition = self._condition is None or (isinstance(self._condition, str) and len(self._condition) > 0)
        valid_body = self._body is None or valid_execution_body(self._body)
        if not valid_target:
            print("Error: SCXML transition: target is not valid.")
        if not valid_events:
            print("Error: SCXML transition: events are not valid.\nList of events:")
            for event in self._events:
                print(f"\t-'{event}'.")
        if not valid_condition:
            print("Error: SCXML transition: condition is not valid.")
        if not valid_body:
            print("Error: SCXML transition: executable content is not valid.")
        return valid_target and valid_events and valid_condition and valid_body

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid transition."
        xml_transition = ET.Element('transition', {"target": self._target})
        if self._events is not None:
            xml_transition.set("event", " ".join(self._events))
        if self._condition is not None:
            xml_transition.set("cond", self._condition)
        if self._body is not None:
            for executable_entry in self._body:
                xml_transition.append(executable_entry.as_xml())
        return xml_transition
