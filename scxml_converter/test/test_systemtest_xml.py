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

from scxml_converter.bt_converter import bt_converter
from scxml_converter.scxml_converter import scxml_converter


def test_scxml_w_ros_to_plain_jani():
    for fname in ['battery_manager.scxml', 'battery_drainer.scxml']:
        input_file = os.path.join(os.path.dirname(__file__),
                                  '_test_data', 'battery_drainer_charge', fname)
        output_file = os.path.join(os.path.dirname(__file__),
                                   '_test_data', 'expected_output', fname)
        with open(input_file, 'r', encoding='utf-8') as f_i:
            input_data = f_i.read()
        sms = scxml_converter(input_data)
        out = sms[0]
        with open(output_file, 'r', encoding='utf-8') as f_o:
            expected_output = f_o.read()
        assert canonicalize_xml(out) == canonicalize_xml(expected_output)

        # if fname == 'battery_drainer.scxml':
        #     assert len(sms) == 2, "Must also have the time state machine."
        # elif fname == 'battery_manager.scxml':
        #     assert len(sms) == 1, "Must only have the battery state machine."


def test_bt_to_scxml():
    input_file = os.path.join(os.path.dirname(__file__),
                              '_test_data', 'battery_drainer_charge', 'bt.xml')
    output_file = os.path.join(os.path.dirname(__file__),
                               '_test_data', 'expected_output', 'bt.scxml')
    plugins = [os.path.join(os.path.dirname(__file__),
                            '_test_data', 'battery_drainer_charge', f)
                for f in ['bt_topic_action.scxml', 'bt_topic_condition.scxml']]
    bt_converter(input_file, plugins)


if __name__ == '__main__':
    test_bt_to_scxml()
