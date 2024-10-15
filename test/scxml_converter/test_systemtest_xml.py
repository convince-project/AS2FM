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

from test_utils import canonicalize_xml, remove_empty_lines, to_snake_case

from as2fm.scxml_converter.bt_converter import bt_converter
from as2fm.scxml_converter.scxml_entries import ScxmlRoot


def get_output_folder(test_folder: str):
    """Get the output folder for the test."""
    return os.path.join(os.path.dirname(__file__), "_test_data", test_folder, "output")


def clear_output_folder(test_folder: str):
    """Clear the output folder. If it does not exist, create it."""
    output_folder = get_output_folder(test_folder)
    if os.path.exists(output_folder):
        for f in os.listdir(output_folder):
            os.remove(os.path.join(output_folder, f))
    else:
        os.makedirs(output_folder)


def bt_to_scxml_test(
    test_folder: str, bt_file: str, bt_plugins: List[str], store_generated: bool = False
):
    """
    Test the conversion of a BT to SCXML.

    :param test_folder: The name of the folder with the files to evaluate.
    :param bt_file: The name to the BT xml file.
    :param bt_plugins: The names of the BT plugins scxml files.
    :param store_generated: If True, the generated SCXML files are stored in the output folder.
    """
    test_data_path = os.path.join(os.path.dirname(__file__), "_test_data", test_folder)
    bt_file = os.path.join(test_data_path, bt_file)
    plugin_files = [os.path.join(test_data_path, f) for f in bt_plugins]
    scxml_objs = bt_converter(bt_file, plugin_files, 1.0)
    assert len(scxml_objs) == 4, f"Expecting 4 scxml objects, found {len(scxml_objs)}."
    if store_generated:
        clear_output_folder(test_folder)
        for scxml_obj in scxml_objs:
            output_file = os.path.join(
                get_output_folder(test_folder), f"{scxml_obj.get_name()}.scxml"
            )
            with open(output_file, "w", encoding="utf-8") as f_o:
                f_o.write(scxml_obj.as_xml_string())
    for scxml_root in scxml_objs:
        scxml_name = scxml_root.get_name()
        gt_scxml_path = os.path.join(test_data_path, "gt_bt_scxml", f"{scxml_name}.scxml")
        with open(gt_scxml_path, "r", encoding="utf-8") as f_o:
            gt_xml = remove_empty_lines(canonicalize_xml(f_o.read()))
            scxml_xml = remove_empty_lines(canonicalize_xml(scxml_root.as_xml_string()))
        assert scxml_xml == gt_xml


def ros_to_plain_scxml_test(
    test_folder: str,
    scxml_bt_ports: Dict[str, List[Tuple[str, str]]],
    expected_scxmls: Dict[str, List[str]],
    store_generated: bool = False,
):
    """
    Test the conversion of SCXML with ROS-specific macros to plain SCXML.

    :param test_folder: The path of the folder with the files to evaluate.
    :param scxml_bt_ports: The BT ports to set to the specified SCXML file.
    :param expected_scxmls: The SCXML object names expected from the specified input files.
    :param store_generated: If True, the generated SCXML files are stored in the output folder.
    """
    # pylint: disable=too-many-locals
    test_data_path = os.path.join(os.path.dirname(__file__), "_test_data", test_folder)
    scxml_files = [file for file in os.listdir(test_data_path) if file.endswith(".scxml")]
    if store_generated:
        clear_output_folder(test_folder)
    bt_index = 1000
    for fname in scxml_files:
        input_file = os.path.join(test_data_path, fname)
        # gt_file = os.path.join(test_data_path, 'gt_plain_scxml', fname)
        try:
            scxml_obj = ScxmlRoot.from_scxml_file(input_file)
            if fname in scxml_bt_ports:
                bt_index += 1
                scxml_obj.set_bt_plugin_id(bt_index)
                scxml_obj.set_bt_ports_values(scxml_bt_ports[fname])
                scxml_obj.instantiate_bt_information()
            plain_scxmls, _ = scxml_obj.to_plain_scxml_and_declarations()
            if store_generated:
                for generated_scxml in plain_scxmls:
                    output_file = os.path.join(
                        get_output_folder(test_folder), f"{generated_scxml.get_name()}.scxml"
                    )
                    with open(output_file, "w", encoding="utf-8") as f_o:
                        f_o.write(generated_scxml.as_xml_string())
            if fname not in expected_scxmls:
                gt_files: List[str] = [fname.removesuffix(".scxml")]
            else:
                gt_files: List[str] = expected_scxmls[fname]
            assert len(plain_scxmls) == len(
                gt_files
            ), f"Expecting {len(gt_files)} scxml objects, found {len(plain_scxmls)}."
            for generated_scxml in plain_scxmls:
                # Make sure the comparison uses snake case
                scxml_object_name = to_snake_case(generated_scxml.get_name())
                assert (
                    scxml_object_name in gt_files
                ), f"Generated SCXML {scxml_object_name} not in gt SCXMLs {gt_files}."
                gt_file_path = os.path.join(
                    test_data_path, "gt_plain_scxml", f"{scxml_object_name}.scxml"
                )
                with open(gt_file_path, "r", encoding="utf-8") as f_o:
                    gt_output = f_o.read()
                assert remove_empty_lines(
                    canonicalize_xml(generated_scxml.as_xml_string())
                ) == remove_empty_lines(canonicalize_xml(gt_output))
        except Exception as e:
            print(f"Error in file {fname}:")
            raise e


def test_bt_to_scxml_battery_drainer():
    """Test the conversion of the battery drainer with BT to SCXML."""
    bt_to_scxml_test(
        "battery_drainer_w_bt",
        "bt.xml",
        ["bt_topic_action.scxml", "bt_topic_condition.scxml"],
        False,
    )


def test_ros_to_plain_scxml_battery_drainer():
    """Test the conversion of the battery drainer with ROS macros to plain SCXML."""
    ros_to_plain_scxml_test("battery_drainer_w_bt", {}, {}, True)


def test_bt_to_scxml_bt_ports():
    """Test the conversion of the BT with ports to SCXML."""
    bt_to_scxml_test("bt_ports_only", "bt.xml", ["bt_topic_action.scxml"], False)


def test_ros_to_plain_scxml_bt_ports():
    """Test the conversion of the BT with ports to plain SCXML."""
    ros_to_plain_scxml_test(
        "bt_ports_only", {"bt_topic_action.scxml": [("name", "out"), ("data", "123")]}, {}, True
    )


def test_ros_to_plain_scxml_add_int_srv():
    """Test the conversion of the add_int_srv_example with ROS macros to plain
    SCXML."""
    ros_to_plain_scxml_test("add_int_srv_example", {}, {}, True)


def test_ros_to_plain_scxml_fibonacci_action():
    """Test the conversion of the fibonacci_action_example with ROS macros to plain
    SCXML."""
    ros_to_plain_scxml_test(
        "fibonacci_action_example",
        {},
        {"server.scxml": ["server", "fibonacci_thread_0", "fibonacci_thread_1"]},
        True,
    )
