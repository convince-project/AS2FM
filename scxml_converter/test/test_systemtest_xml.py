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
from scxml_converter.scxml_converter import ros_to_scxml_converter


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
            with open(input_file, 'r', encoding='utf-8') as f_i:
                input_data = f_i.read()
            scxml, _ = ros_to_scxml_converter(input_data)
            with open(output_file, 'r', encoding='utf-8') as f_o:
                expected_output = f_o.read()
            assert remove_empty_lines(canonicalize_xml(scxml)) == \
                remove_empty_lines(canonicalize_xml(expected_output))
        except Exception as e:
            clear_output_folder()
            print(f"Error in file {fname}:")
            raise e
    clear_output_folder()


def test_bt_to_scxml():
    clear_output_folder()
    input_file = os.path.join(
        os.path.dirname(__file__), '_test_data', 'input_files', 'bt.xml')
    output_file_bt = os.path.join(get_output_folder(), 'bt.scxml')
    plugins = [os.path.join(os.path.dirname(__file__),
                            '_test_data', 'input_files', f)
               for f in ['bt_topic_action.scxml', 'bt_topic_condition.scxml']]
    bt_converter(input_file, plugins, get_output_folder())
    files = os.listdir(get_output_folder())
    assert len(files) == 3, \
        f"Expecting 3 files, found {len(files)}"
    # 1 for the main BT and 2 for the plugins
    assert os.path.exists(output_file_bt), \
        f"Expecting {output_file_bt} to exist, but it does not."
    for fname in files:
        with open(os.path.join(get_output_folder(), fname), 'r', encoding='utf-8') as f_o:
            output = f_o.read()
        with open(os.path.join(
            os.path.dirname(__file__), '_test_data', 'expected_output_bt_and_plugins', fname
        ), 'r', encoding='utf-8') as f_o:
            expected_output = f_o.read()
        assert remove_empty_lines(canonicalize_xml(output)) == \
            remove_empty_lines(canonicalize_xml(expected_output))
    clear_output_folder()


if __name__ == '__main__':
    test_ros_scxml_to_plain_scxml()
