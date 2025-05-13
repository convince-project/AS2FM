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

from as2fm.as2fm_common.common import get_padded_array


def test_array_padding_1d():
    assert get_padded_array([42], [1], int) == [42]
    assert get_padded_array([42], [2], int) == [42, 0]
    assert get_padded_array([42], [2], float) == [42, 0.0]


def test_array_padding_2d():
    assert get_padded_array([[42]], [1, 1], int) == [[42]]
    assert get_padded_array([[42]], [1, 2], int) == [[42, 0]]
    assert get_padded_array([[42]], [2, 2], int) == [[42, 0], [0, 0]]


def test_array_padding_3d():
    assert get_padded_array([[[42]]], [1, 1, 1], int) == [[[42]]]
    assert get_padded_array([[[42]]], [1, 1, 2], int) == [[[42, 0]]]
    assert get_padded_array([[[42]]], [2, 1, 2], int) == [[[42, 0]], [[0, 0]]]
    assert get_padded_array([[[42]]], [1, 2, 2], int) == [[[42, 0], [0, 0]]]


def test_array_padding_wrong():
    test_tuples = [
        ([1, 2, 3], [1]),
        ([[]], [3]),
        ([[], [1, 2, 3]], [2, 2]),
        ([[[]], [1, 2, 3]], [2, 3]),
    ]
    for in_seq, exp_sizes in test_tuples:
        with pytest.raises(ValueError):
            get_padded_array(in_seq, exp_sizes, int)


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
