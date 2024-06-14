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


class ScxmlRoot:
    """This class represents a whole scxml model, that is used to define specific skills."""
    def __init__(self, name, initial_state):
        self._name = name
        self._version = "1.0"  # This is the only version mentioned in the official documentation
        self._initial_state = initial_state
        self._states = []
        self._data_model = None

    def check_validity(self) -> bool:
        pass

    def add_state(self, state):
        self._states.append(state)

    def set_data_model(self, data_model):
        assert self._data_model is None, "Data model already set"
        self._data_model = data_model

    def as_xml(self):
        pass
