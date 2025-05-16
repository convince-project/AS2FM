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
from typing import Dict

from as2fm.scxml_converter.data_types.struct_definition import StructDefinition

OBJECT = "object"
PROPERTIES = "properties"
TITLE = "title"
TYPE = "type"

JSON_SCHEMA_TYPE_TO_SCXML_TYPE = {
    "integer": "int",
    "number": "float",
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
    def from_dict(json_def: Dict[str, any]):
        assert (
            json_def.get(TYPE) == OBJECT
        ), f"Only object definitions are supported. Got {json_def.get(TYPE)}"
        properties = json_def.get(PROPERTIES)

        struct_name = json_def.get(TITLE)
        assert isinstance(struct_name, str), "The schema must have a title."

        struct_members = {}
        for prop_name, prop_def in properties.items():
            if prop_def.get(TYPE) in JSON_SCHEMA_TYPE_TO_SCXML_TYPE:
                assert (
                    prop_name not in struct_members
                ), f"{prop_name=} must not be in {struct_members=} already."
                struct_members[prop_name] = JSON_SCHEMA_TYPE_TO_SCXML_TYPE.get(prop_def.get(TYPE))
            else:
                raise NotImplementedError(f"{prop_def.get(TYPE)=}")

        return JsonStructDefinition(struct_name, struct_members)
