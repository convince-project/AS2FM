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

""" "Test the SCXML data conversion"""

from typing import List, Tuple

import pytest

from as2fm.as2fm_common.common import is_valid_variable_name


def test_variable_names_check():
    test_names: List[Tuple[str, bool]] = [
        ("a", True),
        ("1", False),
        ("'", False),
        (".", False),
        ("_", False),
        ("-", False),
        ("'asd", False),
        (".asd", False),
        ("_asd", True),
        ("-asd", False),
        ("asd", True),
        ("as-d", True),
        ("as_d", True),
        ("as.d", True),
        ("as'd", False),
        ("as.d1", True),
        ("as.d_1", True),
        ("as.d_a1", True),
        ("as.d_a1w", True),
        ("1as.d_a1w", False),
        ("as.d_a1w.", False),
        ("as.d_a1w-", False),
        ("as.d_a1w_", False),
        ("'as.d_a1w", False),
        ("as.d_a1w'", False),
        ("'as.d_a1w'", False),
    ]
    for name, exp_res in test_names:
        assert is_valid_variable_name(name) == exp_res


if __name__ == "__main__":
    pytest.main(["-s", "-vv", __file__])
