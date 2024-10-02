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

from as2fm.trace_visualizer.visualizer import Traces

import os


def test_traces():
    data_prefix: str = 'ros_example_w_bt_battery_below_20_p_0_0107'
    test_data_folder = os.path.join(
        os.path.dirname(__file__),
        '_test_data')
    csv_file = os.path.join(test_data_folder, f'{data_prefix}.csv')
    traces = Traces(csv_file)
    ver, fal = traces.print_info_about_result()
    assert ver == 73, \
        f"The id of the first verified trace must be 73 but is {ver}."
    assert fal == 0, \
        f"The id of the first falsified trace must be 0 but is {fal}."

    # Comparing the generated images with the reference images
    output_file = 'test.png'
    for i, fname_expected in [
        (ver, f'{data_prefix}_verified.png'),
            (fal, f'{data_prefix}_falsified.png')]:
        assert not os.path.exists(output_file), \
            f'The file {output_file} already exists.'
        traces.write_trace_to_img(i, output_file)
        assert os.path.exists(output_file), \
            f'The file {output_file} was not created.'
        path_expected = os.path.join(
            test_data_folder,
            'expected_output',
            fname_expected)
        with open(output_file, 'rb') as f1, open(path_expected, 'rb') as f2:
            assert f1.read() == f2.read(), \
                f'The content for {fname_expected} is not as expected.'
        os.remove(output_file)
