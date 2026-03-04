# Copyright (c) 2026 - for information on the respective copyright owner
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

from dataclasses import dataclass, field
from re import search
from typing import Dict, List


@dataclass()
class RosEventInfo:
    """
    Information about a single ROS communication event.

    :attribute interface_name: Sanitized interface name.
    :attribute interface_type: Type of ROS interface ("topic", "service", or "action")
    :attribute scxml_event_name: SCXML event name
    :attribute event_type: Event type ("publish", "request", "response", "goal_request", "goal_response", "feedback", "result")
    :attribute origin: Name of the automaton that sends the event
    :attribute target: Name of the automaton that receives the event
    :attribute fields: ROS field names mapped to their type strings
    """
    interface_name: str
    interface_type: str
    scxml_event_name: str
    event_type: str
    origin: str
    target: str
    fields: List[Dict[str, str]] = field(default_factory=list)

    def is_bt_info(self) -> bool:
        # Either origin or target of the SCXML event start with BT/bt
        IS_BT_INFO_REGEX = "(?i:^bt.*)"
        if search(IS_BT_INFO_REGEX, self.origin) or search(IS_BT_INFO_REGEX, self.target):
            return True
        return False
