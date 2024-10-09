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
Module to go through existing bt.xml and scxml files and replace strings with constant numbers,
because model checkers usually don't like strings.

- preprocessing step that looks through the bt.xml and all scxmls for string constants
- fixed mapping between strings constants and unique integers (like a enum)
- replace strings with corresponding numbers in bt.xml and scxmls

e.g.
(in bt.xml)
```
<DetectObject name="DetectSnack" object="snacks0"/>
```
turns into ...
```
<DetectObject name="DetectSnack" object="8"/>
```
and
(in scxml)
```
<field name="data" expr="_msg.data == 'snacks0'" />
```
turns into ...
```
<field name="data" expr="_msg.data == 8" />
```
"""
from typing import Set

from lxml import etree as ET

from as2fm.jani_generator.scxml_helpers.full_model_type import FullModel


def replace_strings_in_model(model: FullModel) -> FullModel:
    """
    Replace all strings in the model with corresponding numbers.
    """
    # Find all strings in the model
    # strings = _find_strings_in_model(model)
    # TODO ...

    return model


def _find_strings_in_model(model: FullModel) -> Set[str]:
    """
    Find all strings in the model.
    """
    strings: Set[str] = set()
    if model.bt is not None:
        strings.update(_find_strings_in_bt_xml(model.bt))
    # for scxml in model.scxmls:
    #     strings.extend(_find_strings_in_scxml(scxml.xml))
    return strings


def _find_strings_in_bt_xml(bt_xml_fname: str) -> Set[str]:
    """
    Find all strings used in ports in the bt.xml file.

    e.g. 'pantry' in the following line:
    <Action ID="NavigateAction" name="navigate" data="pantry" />
    """
    ATTRS_THAT_CANT_BE_PORTS = ["name", "ID"]
    strings = set()
    with open(bt_xml_fname, "r", encoding="utf-8") as f:
        et = ET.parse(f)
        root = et.getroot()
        for node in root.iter():
            for key in node.keys():
                if key in ATTRS_THAT_CANT_BE_PORTS:
                    continue
                port_value = node.get(key)
                if not isinstance(port_value, str):
                    continue
                strings.add(port_value)
    return strings
