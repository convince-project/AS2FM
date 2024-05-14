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

"""Test the ROS timer conversion"""

import pytest
import unittest

from jani_generator.ros_helpers.ros_timer import RosTimer


class TestRosTimer(unittest.TestCase):

    def test_initialization_10hz(self):
        """
        Test the initialization of the RosTimer class for 10Hz.
        """
        name = "timer"
        freq = 10
        ros_timer = RosTimer(name, freq)
        assert ros_timer.name == name
        assert ros_timer.freq == freq
        assert ros_timer.period == 1.0 / freq
        assert ros_timer.unit == "ms"
        assert ros_timer.period_int == 100


    def test_initialization_1MHz(self):
        """
        Test the initialization of the RosTimer class for 1MHz.
        """
        name = "timer"
        freq = 1e6
        ros_timer = RosTimer(name, freq)
        assert ros_timer.name == name
        assert ros_timer.freq == freq
        assert ros_timer.period == 1.0 / freq
        assert ros_timer.unit == "us"
        assert ros_timer.period_int == 1


if __name__ == '__main__':
    pytest.main(['-s', '-v', __file__])
