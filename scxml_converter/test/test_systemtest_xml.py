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
import xml.etree.ElementTree as ET

from scxml_converter.scxml_converter import ros_to_scxml_converter


def _canonicalize_xml(xml: str) -> str:
    """Helper function to make XML comparable."""
    # sort attributes
    et = ET.fromstring(xml)
    for elem in et.iter():
        elem.attrib = {k: elem.attrib[k] for k in sorted(elem.attrib.keys())}
    return ET.tostring(et, encoding='unicode')


def test_ros_scxml_to_plain_scxml():
    """Test the conversion of SCXML with ROS-specific macros to plain SCXML."""
    for fname in ['battery_manager.scxml', 'battery_drainer.scxml']:
        input_file = os.path.join(os.path.dirname(__file__),
                                  '_test_data', 'battery_drainer_charge', fname)
        output_file = os.path.join(os.path.dirname(__file__),
                                   '_test_data', 'expected_output', fname)
        with open(input_file, 'r', encoding='utf-8') as f_i:
            input_data = f_i.read()
        sms = ros_to_scxml_converter(input_data)
        out = sms[0]
        with open(output_file, 'r', encoding='utf-8') as f_o:
            expected_output = f_o.read()
        assert _canonicalize_xml(out) == _canonicalize_xml(expected_output)

        # if fname == 'battery_drainer.scxml':
        #     assert len(sms) == 2, "Must also have the time state machine."
        # elif fname == 'battery_manager.scxml':
        #     assert len(sms) == 1, "Must only have the battery state machine."

if __name__ == '__main__':
    test_ros_scxml_to_plain_scxml()
