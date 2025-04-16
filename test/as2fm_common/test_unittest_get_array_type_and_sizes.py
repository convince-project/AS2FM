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

"""Test the interpretation of nested array sizes."""

import pytest

from as2fm.as2fm_common.common import get_array_type_and_sizes


def test_array_dim_base_cases():
    assert get_array_type_and_sizes([]) == (None, [0])
    assert get_array_type_and_sizes([42]) == (int, [1])
    assert get_array_type_and_sizes([3.14]) == (float, [1])


def test_array_dim_2_dims():
    input_array = [[], [2, 0]]
    expected_dims = [2, [0, 2]]
    assert get_array_type_and_sizes(input_array) == (int, expected_dims)


def test_array_dim_3_dims():
    input_array = [[], [[2, 0]]]
    expected_dims = [2, [0, 1], [[], [2]]]
    assert get_array_type_and_sizes(input_array) == (int, expected_dims)


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
