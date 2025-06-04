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
from typing import Any, Dict, List, Optional, Tuple

from as2fm.as2fm_common.logging import log_warning
from as2fm.scxml_converter.data_types.struct_definition import StructDefinition

ARRAY = "array"
OBJECT = "object"
PROPERTIES = "properties"
TITLE = "title"
TYPE = "type"
ITEMS = "items"
REF = "$ref"
REF_PATH_DELIM = "/"
REF_PATH_START = "#"
DEFINITIONS = "definitions"
DEFS = "$defs"
SUPPORTED_DEF_KEYS = [DEFINITIONS, DEFS]

# compare: https://json-schema.org/understanding-json-schema/reference/type
JSON_SCHEMA_TYPE_TO_SCXML_TYPE = {
    "boolean": "bool",
    "integer": "int32",
    "number": "float32",
    "string": "string",
}


class JsonStructDefinition(StructDefinition):

    @staticmethod
    def from_file(fname: str):
        assert os.path.exists(fname), f"File {fname} must exist."
        with open(fname, "r") as file:
            json_def = json.loads(file.read())
            return JsonStructDefinition.from_dict(json_def, fname)

    @staticmethod
    def _resolve_ref(
        root_obj: Dict[str, Any], obj_def: Dict[str, Any], fname: str
    ) -> Tuple[Dict[str, Any], str]:
        assert REF in obj_def.keys()
        path = obj_def.get(REF)
        assert isinstance(path, str)
        keys = path.split(REF_PATH_DELIM)
        assert (
            keys[0] == REF_PATH_START
        ), f"Expected first character in reference to be `{REF_PATH_START}`, got `{keys[0]}`."
        definitions_key = keys[1]
        assert (
            definitions_key in SUPPORTED_DEF_KEYS
        ), f"Expected definitions key to be in {SUPPORTED_DEF_KEYS}, got `{definitions_key}`."
        assert (
            definitions_key in root_obj.keys()
        ), f"Json must contain definitions under key {definitions_key}."
        new_suggested_name = keys[-1]
        indexes = keys[2:]
        keys.reverse()
        referenced_definition = root_obj[definitions_key]
        for idx in indexes:
            referenced_definition = referenced_definition[idx]
        return referenced_definition, new_suggested_name

    @staticmethod
    def _handle_objects(
        root_obj: Dict[str, Any], obj_def: Dict[str, Any], suggested_name: str, fname: str
    ) -> Optional[Tuple[str, List["JsonStructDefinition"]]]:
        if REF in obj_def.keys():
            # this is a reference, resolve it first
            obj_def, suggested_name = JsonStructDefinition._resolve_ref(root_obj, obj_def, fname)
        if obj_def.get(TYPE) == OBJECT:
            properties = obj_def.get(PROPERTIES)
            if properties is None:
                log_warning(fname, f"Object must have properties: {obj_def}")
                return None
            struct_members = {}
            definitions = []
            for prop_name, prop_def in properties.items():
                prop = JsonStructDefinition._handle_objects(root_obj, prop_def, prop_name, fname)
                if prop is not None:
                    this_obj, new_defs = prop
                    if isinstance(this_obj, str):
                        type_str = this_obj
                    else:
                        definitions.append(this_obj)
                        type_str = this_obj.get_name()
                    definitions.extend(new_defs)
                    struct_members[prop_name] = type_str
            definitions.append(JsonStructDefinition(suggested_name, struct_members))
            return suggested_name, definitions
        elif obj_def.get(TYPE) == ARRAY:
            assert ITEMS in obj_def
            prop = JsonStructDefinition._handle_objects(
                root_obj, obj_def.get(ITEMS), suggested_name, fname
            )
            if prop is None:
                return None
            type_str, new_defs = prop
            return type_str + "[]", new_defs
        elif isinstance(obj_def.get(TYPE), list):
            log_warning(fname, "List of types not supported.")
            return None
        elif obj_def.get(TYPE) in JSON_SCHEMA_TYPE_TO_SCXML_TYPE:
            type_str = JSON_SCHEMA_TYPE_TO_SCXML_TYPE.get(obj_def.get(TYPE))
            return type_str, []
        else:
            raise NotImplementedError(f"{obj_def}")

    @staticmethod
    def from_dict(json_def: Dict[str, Any], fname: str):
        assert (
            json_def.get(TYPE) == OBJECT
        ), f"Only object definitions are supported. Got {json_def.get(TYPE)}"
        schema_name = json_def.get(TITLE)
        assert isinstance(schema_name, str), "The schema must have a title."

        _, other_objs = JsonStructDefinition._handle_objects(json_def, json_def, schema_name, fname)
        return {s.get_name(): s for s in other_objs}
