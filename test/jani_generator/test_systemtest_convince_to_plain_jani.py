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

"""Test to CONVINCE robotics Jani to plain Jani conversion."""

import os

from as2fm.jani_generator.convince_jani_helpers import convince_jani_parser
from as2fm.jani_generator.jani_entries import JaniModel


def test_convince_to_plain_jani():
    """
    Test the conversion of a CONVINCE robotics Jani model to plain Jani.
    """
    test_file = os.path.join(os.path.dirname(__file__), '_test_data', 'convince_jani',
                             'first-model-mc-version.jani')
    jani_model = JaniModel()
    assert os.path.isfile(test_file), f"File {test_file} does not exist."
    convince_jani_parser(jani_model, test_file)
    plain_dict = jani_model.as_dict()
    assert len(plain_dict) > 0
    assert isinstance(plain_dict["variables"][0]["type"], str)
