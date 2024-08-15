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

"""Collection of SCXML utilities related to BT functionalities."""


def is_bt_event(event_name: str) -> bool:
    """Given an event name, returns whether it is related to a BT event or not."""
    bt_events = [f"bt_{suffix}" for suffix in ["tick", "running", "success", "failure"]]
    return event_name in bt_events


def replace_bt_event(event_name: str, instance_id: str) -> str:
    """Given a BT event name, returns the same event including the BT node instance."""
    assert is_bt_event(event_name), "Error: BT event instantiation: invalid BT event name."
    return f"bt_{instance_id}_{event_name.removeprefix('bt_')}"
