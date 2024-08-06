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

from scxml_converter.scxml_entries import (ScxmlAssign, ScxmlData, ScxmlDataModel, ScxmlParam,
                                           ScxmlRoot, ScxmlSend, ScxmlState, ScxmlTransition,
                                           RosTimeRate, RosTopicPublisher, RosTopicSubscriber,
                                           RosRateCallback, RosTopicPublish, RosTopicCallback,
                                           RosField)
from test_utils import canonicalize_xml, remove_empty_lines


def test_battery_drainer_from_code():
    """
    Test for scxml_entries generation and conversion to xml.

    It should support the following xml tree:
    - scxml
        - state
            - onentry
                - {executable content}
            - onexit
                - {executable content}
            - transition
                - {executable content}
        - datamodel
            - data

        Executable content consists of the following entries:
        - send
            - param
        - if / elseif / else
        - assign
"""
    battery_drainer_scxml = ScxmlRoot("BatteryDrainer")
    battery_drainer_scxml.set_data_model(ScxmlDataModel([
        ScxmlData("battery_percent", "100", "int16")]))
    use_battery_state = ScxmlState(
        "use_battery",
        on_entry=[ScxmlSend("ros_topic.level",
                            [ScxmlParam("data", expr="battery_percent")])],
        body=[ScxmlTransition("use_battery", ["ros_time_rate.my_timer"],
                              body=[ScxmlAssign("battery_percent", "battery_percent - 1")]),
              ScxmlTransition("use_battery", ["ros_topic.charge"],
                              body=[ScxmlAssign("battery_percent", "100")])])
    battery_drainer_scxml.add_state(use_battery_state, initial=True)
    # Check output xml
    ref_file = os.path.join(os.path.dirname(__file__), '_test_data',
                            'expected_output_ros_to_scxml', 'battery_drainer.scxml')
    assert os.path.exists(ref_file), f"Cannot find ref. file {ref_file}."
    with open(ref_file, 'r', encoding='utf-8') as f_o:
        expected_output = f_o.read()
    test_output = battery_drainer_scxml.as_xml_string()
    test_xml_string = remove_empty_lines(canonicalize_xml(test_output))
    ref_xml_string = remove_empty_lines(canonicalize_xml(expected_output))
    assert test_xml_string == ref_xml_string
    assert battery_drainer_scxml.is_plain_scxml()


def test_battery_drainer_ros_from_code():
    """
    Test for scxml_entries generation and conversion to xml (including ROS specific SCXML extension)

    It should support the following xml tree:
    - scxml
        - state
            - onentry
                - {executable content}
            - onexit
                - {executable content}
            - transition / ros_rate_callback / ros_topic_callback
                - {executable content}
        - datamodel
            - data

        Executable content consists of the following entries:
        - send
            - param
        - ros_topic_publish
            - field
        - if / elseif / else
        - assign
"""
    battery_drainer_scxml = ScxmlRoot("BatteryDrainer")
    battery_drainer_scxml.set_data_model(ScxmlDataModel([
        ScxmlData("battery_percent", "100", "int16")]))
    ros_topic_sub = RosTopicSubscriber("charge", "std_msgs/Empty")
    ros_topic_pub = RosTopicPublisher("level", "std_msgs/Int32")
    ros_timer = RosTimeRate("my_timer", 1)
    battery_drainer_scxml.add_ros_declaration(ros_topic_sub)
    battery_drainer_scxml.add_ros_declaration(ros_topic_pub)
    battery_drainer_scxml.add_ros_declaration(ros_timer)

    use_battery_state = ScxmlState("use_battery")
    use_battery_state.append_on_entry(
        RosTopicPublish(ros_topic_pub, [RosField("data", "battery_percent")]))
    use_battery_state.add_transition(
        RosRateCallback(ros_timer, "use_battery", None,
                        [ScxmlAssign("battery_percent", "battery_percent - 1")]))
    use_battery_state.add_transition(
        RosTopicCallback(ros_topic_sub, "use_battery", [ScxmlAssign("battery_percent", "100")]))
    battery_drainer_scxml.add_state(use_battery_state, initial=True)

    # Check output xml
    ref_file = os.path.join(os.path.dirname(__file__), '_test_data',
                            'input_files', 'battery_drainer.scxml')
    assert os.path.exists(ref_file), f"Cannot find ref. file {ref_file}."
    with open(ref_file, 'r', encoding='utf-8') as f_o:
        expected_output = f_o.read()
    test_output = battery_drainer_scxml.as_xml_string()
    test_xml_string = remove_empty_lines(canonicalize_xml(test_output))
    ref_xml_string = remove_empty_lines(canonicalize_xml(expected_output))
    assert test_xml_string == ref_xml_string
    assert not battery_drainer_scxml.is_plain_scxml()


def _test_xml_parsing(xml_file_path: str, valid_xml: bool = True):
    # TODO: Input path to scxml file fro args
    scxml_root = ScxmlRoot.from_scxml_file(xml_file_path)
    # Check output xml
    if valid_xml:
        test_output = scxml_root.as_xml_string()
        test_xml_string = remove_empty_lines(canonicalize_xml(test_output))
        with open(xml_file_path, 'r', encoding='utf-8') as f_o:
            ref_xml_string = remove_empty_lines(canonicalize_xml(f_o.read()))
        assert test_xml_string == ref_xml_string
        # All the test scxml files we are using contain ROS declarations
        assert not scxml_root.is_plain_scxml()
    else:
        assert not scxml_root.check_validity()


def test_xml_parsing_battery_drainer():
    _test_xml_parsing(os.path.join(os.path.dirname(__file__), '_test_data',
                                   'input_files', 'battery_drainer.scxml'))


def test_xml_parsing_bt_topic_condition():
    _test_xml_parsing(os.path.join(os.path.dirname(__file__), '_test_data',
                                   'input_files', 'bt_topic_condition.scxml'))


def test_xml_parsing_invalid_battery_drainer_xml():
    _test_xml_parsing(os.path.join(os.path.dirname(__file__), '_test_data', 'input_files',
                                   'invalid_xmls', 'battery_drainer.scxml'), valid_xml=False)


def test_xml_parsing_invalid_bt_topic_action_xml():
    _test_xml_parsing(os.path.join(os.path.dirname(__file__), '_test_data', 'input_files',
                                   'invalid_xmls', 'bt_topic_action.scxml'), valid_xml=False)


if __name__ == '__main__':
    test_battery_drainer_from_code()
    test_battery_drainer_ros_from_code()
    test_xml_parsing_battery_drainer()
    test_xml_parsing_bt_topic_condition()
    test_xml_parsing_invalid_battery_drainer_xml()
    test_xml_parsing_invalid_bt_topic_action_xml()
