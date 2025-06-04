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


def test_json_from_dict_types():
    json_defs = JsonStructDefinition.from_dict(
        {
            "title": "Test",
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
        }
    )

    assert len(json_defs) == 1
    json_def = json_defs["Test"]
    assert json_def.get_members() == {"name": "string", "age": "int32"}


def test_json_from_dict_arrays():
    json_defs = JsonStructDefinition.from_dict(
        {
            "title": "TestWArray",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "grades": {"type": "array", "items": {"type": "number"}},
            },
        }
    )

    assert len(json_defs) == 1
    json_def = json_defs["TestWArray"]
    assert json_def.get_members() == {"name": "string", "grades": "float32[]"}


def test_json_from_dict_def_arrays():
    json_defs = JsonStructDefinition.from_dict(
        {
            "title": "TestWArrayADefs",
            "type": "object",
            "properties": {
                "year": {"type": "integer"},
                "students": {"type": "array", "items": {"$ref": "#/definitions/Student"}},
            },
            "definitions": {
                "Student": {"type": "object", "properties": {"name": {"type": "string"}}}
            },
        }
    )

    assert len(json_defs) == 2
    assert json_defs["TestWArrayADefs"].get_members() == {"year": "int32", "students": "Student[]"}
    assert json_defs["Student"].get_members() == {"name": "string"}


def test_json_from_dict_refs():
    json_defs = JsonStructDefinition.from_dict(
        {
            "title": "TestWDef",
            "type": "object",
            "properties": {
                "person": {"$ref": "#/definitions/Person"},
            },
            "definitions": {
                "Person": {"type": "object", "properties": {"name": {"type": "string"}}}
            },
        }
    )

    assert len(json_defs) == 2
    assert json_defs["TestWDef"].get_members() == {"person": "Person"}
    assert json_defs["Person"].get_members() == {"name": "string"}


def test_json_from_file():
    test_schema_path = os.path.join(
        os.path.dirname(__file__), "_test_data", "json_schema", "test.schema"
    )
    json_defs = JsonStructDefinition.from_file(test_schema_path)
    assert len(json_defs) == 2
    assert json_defs["Product"].get_members() == {
        "productId": "int32",
        "productName": "string",
        "price": "float32",
        "tags": "str[]",
        "dimensions": "dimensions",
    }
    assert json_defs["dimensions"].get_members() == {
        "length": "float32",
        "width": "float32",
        "height": "float32",
    }
