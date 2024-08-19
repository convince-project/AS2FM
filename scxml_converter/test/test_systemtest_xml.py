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

from typing import Dict, List, Tuple

from test_utils import canonicalize_xml, remove_empty_lines

from scxml_converter.bt_converter import bt_converter
from scxml_converter.scxml_entries import ScxmlRoot


def get_output_folder(test_folder: str):
    return os.path.join(os.path.dirname(__file__), '_test_data', test_folder, 'output')


def clear_output_folder(test_folder: str):
    output_folder = get_output_folder(test_folder)
    if os.path.exists(output_folder):
        for f in os.listdir(output_folder):
            os.remove(os.path.join(output_folder, f))
    else:
        os.makedirs(output_folder)


def bt_to_scxml_test(
        test_folder: str, bt_file: str, bt_plugins: List[str], store_generated: bool = False):
    """
    Test the conversion of a BT to SCXML.

    :param test_folder: The name of the folder with the files to evaluate.
    :param bt_file: The name to the BT xml file.
    :param bt_plugins: The names of the BT plugins scxml files.
    :param store_generated: If True, the generated SCXML files are stored in the output folder.
    """
    test_data_path = os.path.join(os.path.dirname(__file__), '_test_data', test_folder)
    bt_file = os.path.join(test_data_path, bt_file)
    plugin_files = [os.path.join(test_data_path, f) for f in bt_plugins]
    scxml_objs = bt_converter(bt_file, plugin_files)
    assert len(scxml_objs) == 3, \
        f"Expecting 3 scxml objects, found {len(scxml_objs)}."
    if store_generated:
        clear_output_folder(test_folder)
        for scxml_obj in scxml_objs:
            output_file = os.path.join(
                get_output_folder(test_folder), f'{scxml_obj.get_name()}.scxml')
            with open(output_file, 'w') as f_o:
                f_o.write(scxml_obj.as_xml_string())
    for scxml_root in scxml_objs:
        scxml_name = scxml_root.get_name()
        gt_scxml_path = os.path.join(test_data_path, 'gt_bt_scxml',
                                     f'{scxml_name}.scxml')
        with open(gt_scxml_path, 'r', encoding='utf-8') as f_o:
            gt_xml = remove_empty_lines(canonicalize_xml(f_o.read()))
            scxml_xml = remove_empty_lines(canonicalize_xml(scxml_root.as_xml_string()))

        assert scxml_xml == gt_xml


def ros_to_plain_scxml_test(test_folder: str,
                            scxml_bt_ports: Dict[str, List[Tuple[str, str]]],
                            store_generated: bool = False):
    """Test the conversion of SCXML with ROS-specific macros to plain SCXML."""
    test_data_path = os.path.join(os.path.dirname(__file__), '_test_data', test_folder)
    scxml_files = [file for file in os.listdir(test_data_path) if file.endswith('.scxml')]
    if store_generated:
        clear_output_folder(test_folder)
    for fname in scxml_files:
        input_file = os.path.join(test_data_path, fname)
        gt_file = os.path.join(test_data_path, 'gt_plain_scxml', fname)
        try:
            scxml_obj = ScxmlRoot.from_scxml_file(input_file)
            if fname in scxml_bt_ports:
                scxml_obj.set_bt_ports_values(scxml_bt_ports[fname])
                scxml_obj.update_bt_ports_values()
            plain_scxml, _ = scxml_obj.to_plain_scxml_and_declarations()
            if store_generated:
                output_file = os.path.join(get_output_folder(test_folder), fname)
                with open(output_file, 'w') as f_o:
                    f_o.write(plain_scxml.as_xml_string())
            scxml_str = plain_scxml.as_xml_string()
            with open(gt_file, 'r', encoding='utf-8') as f_o:
                gt_output = f_o.read()
            assert remove_empty_lines(canonicalize_xml(scxml_str)) == \
                remove_empty_lines(canonicalize_xml(gt_output))
        except Exception as e:
            print(f"Error in file {fname}:")
            raise e


def test_bt_to_scxml_battery_drainer():
    bt_to_scxml_test('battery_drainer_w_bt', 'bt.xml',
                     ['bt_topic_action.scxml', 'bt_topic_condition.scxml'], False)


def test_ros_to_plain_scxml_battery_drainer():
    ros_to_plain_scxml_test('battery_drainer_w_bt', {}, True)


def test_bt_to_scxml_bt_ports():
    bt_to_scxml_test('bt_ports_only', 'bt.xml', ['bt_topic_action.scxml'], False)


def test_ros_to_plain_scxml_bt_ports():
    ros_to_plain_scxml_test('bt_ports_only',
                            {'bt_topic_action.scxml': [('name', 'out'), ('data', '123')]},
                            True)


def test_ros_to_plain_scxml_add_int_srv():
    ros_to_plain_scxml_test('add_int_srv_example', {}, True)
