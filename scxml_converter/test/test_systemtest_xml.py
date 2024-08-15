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

import os

from test_utils import canonicalize_xml, remove_empty_lines

from scxml_converter.bt_converter import bt_converter
from scxml_converter.scxml_entries import ScxmlRoot


def get_output_folder():
    return os.path.join(os.path.dirname(__file__), 'output')


def clear_output_folder():
    output_folder = get_output_folder()
    if os.path.exists(output_folder):
        for f in os.listdir(output_folder):
            os.remove(os.path.join(output_folder, f))
    else:
        os.makedirs(output_folder)


def test_ros_scxml_to_plain_scxml():
    """Test the conversion of SCXML with ROS-specific macros to plain SCXML."""
    clear_output_folder()
    scxml_files = [file for file in os.listdir(
        os.path.join(os.path.dirname(__file__), '_test_data', 'input_files')
    ) if file.endswith('.scxml')]
    for fname in scxml_files:
        input_file = os.path.join(os.path.dirname(__file__),
                                  '_test_data', 'input_files', fname)
        output_file = os.path.join(os.path.dirname(__file__),
                                   '_test_data', 'expected_output_ros_to_scxml', fname)
        try:
            scxml, _ = ScxmlRoot.from_scxml_file(input_file).to_plain_scxml_and_declarations()
            scxml_str = scxml.as_xml_string()
            with open(output_file, 'r', encoding='utf-8') as f_o:
                expected_output = f_o.read()
            assert remove_empty_lines(canonicalize_xml(scxml_str)) == \
                remove_empty_lines(canonicalize_xml(expected_output))
        except Exception as e:
            clear_output_folder()
            print(f"Error in file {fname}:")
            raise e
    clear_output_folder()


def test_bt_to_scxml():
    input_file = os.path.join(
        os.path.dirname(__file__), '_test_data', 'input_files', 'bt.xml')
    plugin_paths = [os.path.join(os.path.dirname(__file__), '_test_data', 'input_files', f)
                    for f in ['bt_topic_action.scxml', 'bt_topic_condition.scxml']]
    scxml_objs = bt_converter(input_file, plugin_paths)
    assert len(scxml_objs) == 3, \
        f"Expecting 3 scxml objects, found {len(scxml_objs)}."
    for scxml_root in scxml_objs:
        scxml_name = scxml_root.get_name()
        gt_scxml_path = os.path.join(os.path.dirname(__file__), '_test_data',
                                     'expected_output_bt_and_plugins', f'{scxml_name}.scxml')
        with open(gt_scxml_path, 'r', encoding='utf-8') as f_o:
            gt_xml = remove_empty_lines(canonicalize_xml(f_o.read()))
            scxml_xml = remove_empty_lines(canonicalize_xml(scxml_root.as_xml_string()))

        assert scxml_xml == gt_xml


if __name__ == '__main__':
    test_ros_scxml_to_plain_scxml()
