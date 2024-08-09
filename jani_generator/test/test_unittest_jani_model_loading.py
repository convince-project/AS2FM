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

""""Test the SCXML data conversion"""

import os
import json
from jani_generator.jani_entries import JaniModel


def test_jani_file_loading():
    jani_file = os.path.join(os.path.dirname(__file__),
                             '_test_data', 'plain_jani_examples', 'example_arrays.jani')
    with open(jani_file, "r", encoding='utf-8') as file:
        convince_jani_json = json.load(file)
    jani_model = JaniModel.from_dict(convince_jani_json)
    assert isinstance(jani_model, JaniModel)
    assert jani_model.get_name() == "example_arrays"
    assert "arrays" in jani_model.get_features()
    assert len(jani_model.get_variables()) == 12
    assert len(jani_model.get_constants()) == 0
    assert len(jani_model.get_automata()) == 14
