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

from test_utils import canonicalize_xml

from as2fm.scxml_converter.scxml_entries import (
    BtGetValueInputPort,
    BtInputPortDeclaration,
    BtTick,
    RosField,
    RosRateCallback,
    RosTimeRate,
    RosTopicCallback,
    RosTopicPublish,
    RosTopicPublisher,
    RosTopicSubscriber,
    ScxmlAssign,
    ScxmlData,
    ScxmlDataModel,
    ScxmlParam,
    ScxmlRoot,
    ScxmlSend,
    ScxmlState,
    ScxmlTransition,
    ScxmlTransitionTarget,
)
from as2fm.scxml_converter.scxml_entries.utils import ROS_FIELD_PREFIX


def _test_scxml_from_code(scxml_root: ScxmlRoot, ref_file_path: str):
    # Check output xml
    with open(ref_file_path, "r", encoding="utf-8") as f_o:
        expected_output = f_o.read()
    test_output = scxml_root.as_xml_string()
    test_xml_string = canonicalize_xml(test_output)
    ref_xml_string = canonicalize_xml(expected_output)
    assert test_xml_string == ref_xml_string


def _test_xml_parsing(xml_file_path: str, valid_xml: bool = True):
    scxml_root = ScxmlRoot.from_scxml_file(xml_file_path)
    # Check output xml
    if valid_xml:
        test_output = scxml_root.as_xml_string()
        test_xml_string = canonicalize_xml(test_output)
        ref_file_path = os.path.join(
            os.path.dirname(xml_file_path), "gt_parsed_scxml", os.path.basename(xml_file_path)
        )
        with open(ref_file_path, "r", encoding="utf-8") as f_o:
            ref_xml_string = canonicalize_xml(f_o.read())
        assert test_xml_string == ref_xml_string
        # All the test scxml files we are using contain ROS declarations
        assert not scxml_root.is_plain_scxml()
    else:
        assert not scxml_root.check_validity()


def test_battery_drainer_from_code():
    """
    Test for scxml_entries generation and conversion to xml.
    """
    battery_drainer_scxml = ScxmlRoot("BatteryDrainer")
    battery_drainer_scxml.set_data_model(
        ScxmlDataModel([ScxmlData("battery_percent", "100", "int16")])
    )
    use_battery_state = ScxmlState(
        "use_battery",
        on_entry=[
            ScxmlSend(
                "topic_level_msg", [ScxmlParam(f"{ROS_FIELD_PREFIX}data", expr="battery_percent")]
            )
        ],
        body=[
            ScxmlTransition.make_single_target_transition(
                "use_battery",
                ["ros_time_rate.my_timer"],
                body=[ScxmlAssign("battery_percent", "battery_percent - 1")],
            ),
            ScxmlTransition.make_single_target_transition(
                "use_battery", ["topic_charge_msg"], body=[ScxmlAssign("battery_percent", "100")]
            ),
        ],
    )
    battery_drainer_scxml.add_state(use_battery_state, initial=True)
    _test_scxml_from_code(
        battery_drainer_scxml,
        os.path.join(
            os.path.dirname(__file__),
            "_test_data",
            "battery_drainer_w_bt",
            "gt_plain_scxml",
            "battery_drainer.scxml",
        ),
    )


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
    battery_drainer_scxml.set_data_model(
        ScxmlDataModel([ScxmlData("battery_percent", "100", "int16")])
    )
    ros_topic_sub = RosTopicSubscriber("charge", "std_msgs/Empty", "sub")
    ros_topic_pub = RosTopicPublisher("level", "std_msgs/Int32", "pub")
    ros_timer = RosTimeRate("my_timer", 1)
    battery_drainer_scxml.add_ros_declaration(ros_topic_sub)
    battery_drainer_scxml.add_ros_declaration(ros_topic_pub)
    battery_drainer_scxml.add_ros_declaration(ros_timer)

    use_battery_state = ScxmlState("use_battery")
    use_battery_state.append_on_entry(
        RosTopicPublish(ros_topic_pub, [RosField("data", "battery_percent")])
    )
    use_battery_state.add_transition(
        RosRateCallback(
            ros_timer, "use_battery", None, [ScxmlAssign("battery_percent", "battery_percent - 1")]
        )
    )
    use_battery_state.add_transition(
        RosTopicCallback(
            ros_topic_sub, "use_battery", None, [ScxmlAssign("battery_percent", "100")]
        )
    )
    battery_drainer_scxml.add_state(use_battery_state, initial=True)
    _test_scxml_from_code(
        battery_drainer_scxml,
        os.path.join(
            os.path.dirname(__file__),
            "_test_data",
            "battery_drainer_w_bt",
            "gt_parsed_scxml",
            "battery_drainer.scxml",
        ),
    )


def test_bt_action_with_ports_from_code():
    """
    Test for generating scxml code containing BT Ports
    """
    data_model = ScxmlDataModel([ScxmlData("number", "0", "int16")])
    topic_publisher = RosTopicPublisher(BtGetValueInputPort("name"), "std_msgs/Int16", "answer_pub")
    init_state = ScxmlState(
        "initial",
        body=[
            BtTick(
                [
                    ScxmlTransitionTarget(
                        "initial",
                        body=[
                            ScxmlAssign("number", BtGetValueInputPort("data")),
                            RosTopicPublish(topic_publisher, [RosField("data", "number")]),
                        ],
                    )
                ]
            )
        ],
    )
    scxml_root = ScxmlRoot("BtTopicAction")
    scxml_root.set_bt_plugin_id(0)
    scxml_root.set_data_model(data_model)
    scxml_root.add_bt_port_declaration(BtInputPortDeclaration("name", "string"))
    scxml_root.add_bt_port_declaration(BtInputPortDeclaration("data", "int16"))
    scxml_root.add_ros_declaration(topic_publisher)
    scxml_root.add_state(init_state, initial=True)
    assert not scxml_root.check_validity(), "Currently, we handle unspecified BT entries as invalid"
    scxml_root.set_bt_ports_values([("name", "/sys/add_srv"), ("data", "25")])
    scxml_root.instantiate_bt_information()
    _test_scxml_from_code(
        scxml_root,
        os.path.join(
            os.path.dirname(__file__),
            "_test_data",
            "bt_ports_only",
            "gt_parsed_scxml",
            "bt_topic_action.scxml",
        ),
    )


def test_xml_parsing_battery_drainer():
    """Test the parsing of the battery drainer scxml file."""
    _test_xml_parsing(
        os.path.join(
            os.path.dirname(__file__), "_test_data", "battery_drainer_w_bt", "battery_drainer.scxml"
        )
    )


def test_xml_parsing_bt_topic_condition():
    """Test the parsing of the bt topic condition scxml file."""
    _test_xml_parsing(
        os.path.join(
            os.path.dirname(__file__),
            "_test_data",
            "battery_drainer_w_bt",
            "bt_topic_condition.scxml",
        )
    )


def test_xml_parsing_invalid_battery_drainer_xml():
    """Test the parsing of the battery drainer scxml file with invalid xml."""
    _test_xml_parsing(
        os.path.join(
            os.path.dirname(__file__), "_test_data", "invalid_xmls", "battery_drainer.scxml"
        ),
        valid_xml=False,
    )


def test_xml_parsing_invalid_bt_topic_action_xml():
    """Test the parsing of the bt topic action scxml file with invalid xml."""
    _test_xml_parsing(
        os.path.join(
            os.path.dirname(__file__), "_test_data", "invalid_xmls", "bt_topic_action.scxml"
        ),
        valid_xml=False,
    )


if __name__ == "__main__":
    test_battery_drainer_from_code()
    test_battery_drainer_ros_from_code()
    test_xml_parsing_battery_drainer()
    test_xml_parsing_bt_topic_condition()
    test_xml_parsing_invalid_battery_drainer_xml()
    test_xml_parsing_invalid_bt_topic_action_xml()
