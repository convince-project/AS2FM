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

from as2fm.jani_visualizer.visualizer import PlantUMLAutomata

import os
import json


def test_plantumlautomata():
    for data_prefix in ['demo_manual', 'ros_example_w_bt']:
        test_data_folder = os.path.join(
            os.path.dirname(__file__),
            '_test_data')
        jani_fname = os.path.join(test_data_folder, f'{data_prefix}.jani')

        with open(jani_fname, 'r', encoding='utf-8') as f:
            jani_dict = json.load(f)
        pua = PlantUMLAutomata(jani_dict)
        puml_str = pua.to_plantuml(
            with_assignments=True,  # default
            with_guards=True,  # default
            with_syncs=True  # default
        )

        # Comparing the generated images with the reference images
        output_file = os.path.join(
            test_data_folder, 'expected_output', f'{data_prefix}.plantuml')
        with open(output_file, 'r', encoding='utf-8') as f:
            expected_content = f.read()
        assert puml_str == expected_content, \
            f'The content for {output_file} is not as expected.'
