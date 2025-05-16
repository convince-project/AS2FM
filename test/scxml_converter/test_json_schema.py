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

import os

from as2fm.scxml_converter.data_types.json_struct_definition import JsonStructDefinition


def test_json_from_dict():
    json_defs = JsonStructDefinition.from_dict(
        {
            "title": "Test",
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }
    )

    assert len(json_defs) == 1
    json_def = json_defs[0]
    assert json_def.get_name() == "Test"
    assert json_def.get_members() == {"name": "str", "age": "int"}


def test_json_from_file():
    test_schema_path = os.path.join(
        os.path.dirname(__file__), "_test_data", "json_schema", "test.schema"
    )
    json_defs = JsonStructDefinition.from_file(test_schema_path)
    assert len(json_defs) == 2
    for json_def in json_defs:
        if json_def.get_name() == "Product":
            assert json_def.get_members() == {
                "productId": "int",
                "productName": "str",
                "price": "float",
                "tags": "str[]",
                "dimensions": "dimensions",
            }
        elif json_def.get_name() == "dimensions":
            assert json_def.get_members() == {
                "length": "float",
                "width": "float",
                "height": "float",
            }
        else:
            assert False
