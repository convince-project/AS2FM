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
The main entry point of an SCXML Model. In XML, it has the tag `scxml`.
"""

from typing import List
from scxml_converter.scxml_entries import ScxmlState, ScxmlDataModel

from xml.etree import ElementTree as ET


class ScxmlRoot:
    """This class represents a whole scxml model, that is used to define specific skills."""
    def __init__(self, name: str):
        self._name = name
        self._version = "1.0"  # This is the only version mentioned in the official documentation
        self._initial_state: str = None
        self._states: List[ScxmlState] = []
        self._data_model: ScxmlDataModel = None

    def add_state(self, state: ScxmlState, initial: bool = False):
        self._states.append(state)

    def set_data_model(self, data_model: ScxmlDataModel):
        assert self._data_model is None, "Data model already set"
        self._data_model = data_model

    def check_validity(self) -> bool:
        valid_name = isinstance(self._name, str) and len(self._name) > 0
        valid_initial_state = self._initial_state is not None
        valid_states = isinstance(self._states, list) and len(self._states) > 0
        if valid_states:
            for state in self._states:
                valid_states = isinstance(state, ScxmlState) and state.check_validity()
                if not valid_states:
                    break
        valid_data_model = self._data_model is None or self._data_model.check_validity()
        if not valid_name:
            print("Error: SCXML root: name is not valid.")
        if not valid_initial_state:
            print("Error: SCXML root: no initial state set.")
        if not valid_states:
            print("Error: SCXML root: states are not valid.")
        if not valid_data_model:
            print("Error: SCXML root: datamodel is not valid.")
        return valid_name and valid_initial_state and valid_states and valid_data_model

    def as_xml(self) -> ET.Element:
        assert self.check_validity(), "SCXML: found invalid root object."
        xml_root = ET.Element("scxml", {
            "name": self._name,
            "version": self._version,
            "model_src": "",
            "initial": self._initial_state,
            "xmlns": "http://www.w3.org/2005/07/scxml"
        })
        if self._data_model is not None:
            xml_root.append(self._data_model.as_xml())
        for state in self._states:
            xml_root.append(state.as_xml())
        return xml_root
