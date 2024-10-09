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
SCXML entries related to Behavior Tree Ticks and related responses.
"""

from typing import Optional, Union

from lxml import etree as ET

from as2fm.scxml_converter.scxml_entries import (
    ScxmlExecutionBody,
    ScxmlSend,
    ScxmlTransition,
    execution_body_from_xml,
)
from as2fm.scxml_converter.scxml_entries.bt_utils import BtResponse
from as2fm.scxml_converter.scxml_entries.xml_utils import assert_xml_tag_ok, get_xml_argument


class BtTick(ScxmlTransition):
    """
    Process a BT plugin/control node tick, triggering the related transition.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_tick"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "BtTick":
        assert_xml_tag_ok(BtTick, xml_tree)
        target: str = get_xml_argument(BtTick, xml_tree, "target")
        condition: Optional[str] = get_xml_argument(BtTick, xml_tree, "cond", none_allowed=True)
        body = execution_body_from_xml(xml_tree)
        return BtTick(target, condition, body)

    def __init__(
        self,
        target: str,
        condition: Optional[str] = None,
        body: Optional[ScxmlExecutionBody] = None,
    ):
        super().__init__(target, ["bt_tick"], condition, body)

    def as_xml(self) -> ET.Element:
        xml_bt_tick = ET.Element(BtTick.get_tag_name(), {"target": self._target})
        if self._condition is not None:
            xml_bt_tick.set("cond", self._condition)
        if self._body is not None:
            for executable_entry in self._body:
                xml_bt_tick.append(executable_entry.as_xml())
        return xml_bt_tick


class BtTickChild(ScxmlSend):
    """Tick one child of a control node."""

    @staticmethod
    def get_tag_name() -> str:
        return "bt_tick_child"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "BtTickChild":
        assert_xml_tag_ok(BtTickChild, xml_tree)
        child_id: str = get_xml_argument(BtTickChild, xml_tree, "id")
        return BtTickChild(child_id)

    def __init__(self, child_id: Union[str, int]):
        assert isinstance(
            child_id, (str, int)
        ), f"Error: SCXML BT Tick Child: invalid child id type {type(child_id)}."
        self._child = child_id

    def as_xml(self) -> ET.Element:
        xml_bt_tick_child = ET.Element(BtTickChild.get_tag_name(), {"id": str(self._child)})
        return xml_bt_tick_child


class BtChildStatus(ScxmlTransition):
    """
    Process the response received from a BT child.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_child_status"

    @staticmethod
    def from_xml_tree(xml_tree):
        assert_xml_tag_ok(BtChildStatus, xml_tree)
        child_id = get_xml_argument(BtChildStatus, xml_tree, "id")
        target = get_xml_argument(BtChildStatus, xml_tree, "target")
        condition = get_xml_argument(BtChildStatus, xml_tree, "cond", none_allowed=True)
        body = execution_body_from_xml(xml_tree)
        return BtChildStatus(child_id, target, condition, body)

    def __init__(
        self,
        child_id: Union[str, int],
        target: str,
        condition: Optional[str] = None,
        body: Optional[ScxmlExecutionBody] = None,
    ):
        self._child_id = child_id
        self._target = target
        self._condition = condition
        self._body = body

    def as_xml(self) -> ET.Element:
        xml_bt_child_status = ET.Element(
            BtChildStatus.get_tag_name(), {"id": str(self._child_id), "target": self._target}
        )
        if self._condition is not None:
            xml_bt_child_status.set("cond", self._condition)
        if self._body is not None:
            for executable_entry in self._body:
                xml_bt_child_status.append(executable_entry.as_xml())
        return xml_bt_child_status


class BtReturnStatus(ScxmlSend):
    """
    Send a status response to a BT parent node.
    """

    @staticmethod
    def get_tag_name() -> str:
        return "bt_return_status"

    @staticmethod
    def from_xml_tree(xml_tree: ET.Element) -> "BtReturnStatus":
        assert_xml_tag_ok(BtReturnStatus, xml_tree)
        status = get_xml_argument(BtReturnStatus, xml_tree, "status")
        return BtReturnStatus(status)

    def __init__(self, status: str):
        self._status: str = status
        self._status_id: int = BtResponse.str_to_int(status)

    def as_xml(self) -> ET.Element:
        return ET.Element(BtReturnStatus.get_tag_name(), {"status": self._status})
