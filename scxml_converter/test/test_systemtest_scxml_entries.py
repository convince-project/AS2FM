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
from test_utils import canonicalize_xml
from scxml_converter.scxml_entries import ScxmlRoot, ScxmlDataModel, ScxmlState, ScxmlSend, ScxmlParam, \
    ScxmlTransition, ScxmlAssign


def test_battery_drainer_from_code():
    battery_drainer_scxml = ScxmlRoot("BatteryDrainer")
    battery_drainer_scxml.set_data_model(ScxmlDataModel([("battery", "100")]))
    use_battery_state = ScxmlState("use_battery",
                                   on_entry=[ScxmlSend("ros_topic.level", "BatteryManager",
                                                       [ScxmlParam("data", expr="battery_percent")])],
                                   body=[ScxmlTransition("use_battery", "ros_time_rate.my_timer",
                                                         body=[ScxmlAssign("battery_percent", "battery_percent - 1")]),
                                         ScxmlTransition("use_battery", "ros_topic.charge",
                                                         body=[ScxmlAssign("battery_percent", "100")])])
    battery_drainer_scxml.add_state(use_battery_state, initial=True)
    # Check output xml
    ref_file = os.path.join(os.path.dirname(__file__), '_test_data', 'expected_output', 'battery_drainer.scxml')
    with open(ref_file, 'r', encoding='utf-8') as f_o:
        expected_output = f_o.read()
    test_output = ET.dump(battery_drainer_scxml.as_xml())
    assert canonicalize_xml(test_output) == canonicalize_xml(expected_output)


if __name__ == '__main__':
    test_battery_drainer_from_code()

# We want to support ..

# - scxml
#     - state
#         - onentry
#             - {executable content}
#         - onexit
#             - {executable content}
#         - transition
#             - {executable content}
#     - datamodel
#         - data

# executable content
# - send
#     - param
# - if / elseif / else
# - assign

# dump to scxml file
# (read scxml file)
