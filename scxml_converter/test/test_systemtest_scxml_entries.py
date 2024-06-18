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
from xml.etree import ElementTree as ET

from scxml_converter.scxml_entries import (ScxmlAssign, ScxmlDataModel,
                                           ScxmlParam, ScxmlRoot, ScxmlSend,
                                           ScxmlState, ScxmlTransition)
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
    battery_drainer_scxml.set_data_model(ScxmlDataModel([("battery_percent", "100")]))
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
    test_output = ET.tostring(battery_drainer_scxml.as_xml(), encoding='unicode')
    test_xml_string = remove_empty_lines(canonicalize_xml(test_output))
    ref_xml_string = remove_empty_lines(canonicalize_xml(expected_output))
    assert test_xml_string == ref_xml_string


if __name__ == '__main__':
    test_battery_drainer_from_code()
