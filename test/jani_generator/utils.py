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

"""
Some test utils
"""

import json
import os


def json_jani_properties_match(path1: str, path2: str) -> bool:
    """Compare the property definition from 2 json files. Return true if they match."""
    assert os.path.exists(path1), f"Error: Path {path1} does not exist."
    assert os.path.exists(path2), f"Error: Path {path2} does not exist."
    with open(path1, "r", encoding="utf-8") as file:
        property1 = json.load(file)["properties"]
    with open(path2, "r", encoding="utf-8") as file:
        property2 = json.load(file)["properties"]
    return property1 == property2
