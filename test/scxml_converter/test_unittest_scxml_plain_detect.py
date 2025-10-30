# Copyright (c) 2025 - for information on the respective copyright owner
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

"""Test the SCXML data conversion from all possible declaration types"""

import os

import pytest

from as2fm.scxml_converter.ascxml_extensions.ros_entries import AscxmlRootROS
from as2fm.scxml_converter.scxml_entries import ScxmlRoot

TEST_FOLDER: str = os.path.join(os.path.dirname(__file__), "_test_data", "battery_drainer_w_bt")


def test_scxml_detect_non_plain():
    test_scxml = os.path.join(TEST_FOLDER, "battery_manager.scxml")
    scxml_root = AscxmlRootROS.load_scxml_file(test_scxml, {})
    assert not scxml_root.is_plain_scxml(), "Expected the loaded scxml model to be non-plain SCXML."


def test_scxml_detect_plain():
    test_scxml = os.path.join(TEST_FOLDER, "gt_plain_scxml", "battery_manager.scxml")
    scxml_root = ScxmlRoot.load_scxml_file(test_scxml, {})
    assert scxml_root.is_plain_scxml(), "Expected the loaded scxml model to be plain SCXML."


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
