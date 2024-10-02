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
Utilities used to compare XML.
"""

import re
from xml.etree import ElementTree as ET


def to_snake_case(text: str) -> str:
    """Convert a string to snake case."""
    return re.sub(r'(?<!^)(?=[A-Z])', '_', text).lower()


def canonicalize_xml(xml: str) -> str:
    """Helper function to make XML comparable."""
    # sort attributes
    assert isinstance(xml, str), f"Error: invalid input: expected str, found {type(xml)}"
    et = ET.fromstring(xml)
    for elem in et.iter():
        elem.attrib = {k: elem.attrib[k] for k in sorted(elem.attrib.keys())}
    return ET.tostring(et, encoding='unicode')


def remove_empty_lines(text: str) -> str:
    """Remove empty lines from a string."""
    assert isinstance(text, str), f"Error: invalid input: expected str, found {type(text)}"
    return "\n".join([line for line in text.split("\n") if line.strip()])
