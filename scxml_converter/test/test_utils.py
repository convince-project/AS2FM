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

from xml.etree import ElementTree as ET


def canonicalize_xml(xml: str) -> str:
    """Helper function to make XML comparable."""
    # sort attributes
    et = ET.fromstring(xml)
    for elem in et.iter():
        elem.attrib = {k: elem.attrib[k] for k in sorted(elem.attrib.keys())}
    return ET.tostring(et, encoding='unicode')
