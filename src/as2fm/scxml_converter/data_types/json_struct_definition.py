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

import json
import os
from typing import Dict, List, Tuple

from as2fm.scxml_converter.data_types.struct_definition import StructDefinition

ARRAY = "array"
OBJECT = "object"
PROPERTIES = "properties"
TITLE = "title"
TYPE = "type"
ITEMS = "items"

# compare: https://json-schema.org/understanding-json-schema/reference/type
JSON_SCHEMA_TYPE_TO_SCXML_TYPE = {
    "boolean": "bool",
    "integer": "int32",
    "number": "float32",
    "string": "str",
}


class JsonStructDefinition(StructDefinition):

    @staticmethod
    def from_file(fname: str):
        assert os.path.exists(fname), f"File {fname} must exist."
        with open(fname, "r") as file:
            json_def = json.loads(file.read())
            return JsonStructDefinition.from_dict(json_def)

    @staticmethod
    def _handle_property(prop_def: Dict[str, any]) -> str:
        if prop_def.get(TYPE) in JSON_SCHEMA_TYPE_TO_SCXML_TYPE:
            return JSON_SCHEMA_TYPE_TO_SCXML_TYPE.get(prop_def.get(TYPE))
        elif prop_def.get(TYPE) == ARRAY:
            assert ITEMS in prop_def
            return JsonStructDefinition._handle_property(prop_def.get(ITEMS)) + "[]"
        else:
            raise NotImplementedError(f"{prop_def}")

    @staticmethod
    def _handle_objects(
        obj_def: Dict[str, any], suggested_name: str
    ) -> Tuple["JsonStructDefinition", List["JsonStructDefinition"]]:
        assert obj_def.get(TYPE) == OBJECT
        properties = obj_def.get(PROPERTIES)
        assert properties is not None, f"Object must have properties: {obj_def}"
        struct_members = {}
        definitions = []
        for prop_name, prop_def in properties.items():
            if prop_def.get(TYPE) == OBJECT:
                this_obj, new_defs = JsonStructDefinition._handle_objects(prop_def, prop_name)
                definitions.append(this_obj)
                definitions.extend(new_defs)
                type_str = this_obj.get_name()
            else:
                type_str = JsonStructDefinition._handle_property(prop_def)
            struct_members[prop_name] = type_str
        return JsonStructDefinition(suggested_name, struct_members), definitions

    @staticmethod
    def from_dict(json_def: Dict[str, any]):
        assert (
            json_def.get(TYPE) == OBJECT
        ), f"Only object definitions are supported. Got {json_def.get(TYPE)}"
        schema_name = json_def.get(TITLE)
        assert isinstance(schema_name, str), "The schema must have a title."

        root_obj, other_objs = JsonStructDefinition._handle_objects(json_def, schema_name)
        return [root_obj] + other_objs
