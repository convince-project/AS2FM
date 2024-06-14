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
Definition of SCXML Tags that can be part of executable content
"""

from typing import List, Union

from scxml_converter.scxml_entries import ScxmlAssign, ScxmlSend, ScxmlIf

ScxmlExecutableEntries = Union[ScxmlAssign, ScxmlIf, ScxmlSend]
ScxmlExecutionBody = List[ScxmlExecutableEntries]


def valid_execution_body(execution_body: ScxmlExecutionBody) -> bool:
    """
    Check if an execution body is valid.

    :param execution_body: The execution body to check
    :return: True if the execution body is valid, False otherwise
    """
    valid = isinstance(execution_body, list)
    if not valid:
        print("Error: SCXML execution body: invalid type found: expected a list.")
    for entry in execution_body:
        if not isinstance(entry, ScxmlExecutableEntries):
            valid = False
            print("Error: SCXML execution body: invalid entry type found.")
            break
        if not entry.check_validity():
            valid = False
            print("Error: SCXML execution body: invalid entry content found.")
            break
    return valid
