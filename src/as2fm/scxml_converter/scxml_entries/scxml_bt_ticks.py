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

from typing import List, Optional, Union

from lxml import etree as ET

from as2fm.scxml_converter.scxml_entries import (
    ScxmlExecutionBody,
    ScxmlIf,
    ScxmlParam,
    ScxmlSend,
    ScxmlTransition,
    execution_body_from_xml,
    instantiate_exec_body_bt_events,
)
from as2fm.scxml_converter.scxml_entries.bt_utils import (
    BtResponse,
    generate_bt_response_event,
    generate_bt_tick_event,
)
from as2fm.scxml_converter.scxml_entries.utils import is_non_empty_string
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

    def check_validity(self) -> bool:
        return super().check_validity()

    def instantiate_bt_events(self, instance_id: int, children_ids: List[int]) -> ScxmlTransition:
        self._events = [generate_bt_tick_event(instance_id)]
        instantiate_exec_body_bt_events(self._body, instance_id, children_ids)
        return ScxmlTransition(self._target, self._events, self._condition, self._body)

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
        if isinstance(child_id, str):
            child_id = child_id.strip()
            try:
                self._child = int(child_id)
            except ValueError:
                self._child = child_id
                assert is_non_empty_string(BtTickChild, "id", self._child)
                assert (
                    self._child.isidentifier()
                ), f"Error: SCXML BT Tick Child: invalid child id '{self._child}'."

    def check_validity(self) -> bool:
        return True

    def instantiate_bt_events(
        self, instance_id: int, children_ids: List[int]
    ) -> Union[ScxmlIf, ScxmlSend]:
        """
        Convert the BtTickChild to ScxmlSend if the child id is constant and an ScxmlIf otherwise.
        """
        if isinstance(self._child, int):
            # We know the exact child ID we want to tick
            assert self._child < len(children_ids), (
                f"Error: SCXML BT Tick Child: invalid child ID {self._child} "
                f"for {len(children_ids)} children."
            )
            return ScxmlSend(generate_bt_tick_event(children_ids[self._child]))
        else:
            # The children to tick depends on the index of the self._child variable at runtime
            if_bodies = []
            for child_id in children_ids:
                if_bodies.append(
                    (f"{self._child} == {child_id}", [ScxmlSend(generate_bt_tick_event(child_id))])
                )
            return ScxmlIf(if_bodies).instantiate_bt_events(instance_id, children_ids)

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
        if self._condition is not None:
            self._condition = BtResponse.process_expr(self._condition)
        self._body = body

    def instantiate_bt_events(
        self, instance_id: int, children_ids: List[int]
    ) -> List[ScxmlTransition]:
        if isinstance(self._child_id, int):
            # Handling specific child ID, return a single transition
            assert self._child_id < len(children_ids), (
                f"Error: SCXML BT Child Status: invalid child ID {self._child_id} "
                f"for {len(children_ids)} children."
            )
            target_child_id = children_ids[self._child_id]
            return [
                ScxmlTransition(
                    self._target,
                    [generate_bt_tick_event(target_child_id)],
                    self._condition,
                    self._body,
                ).instantiate_bt_events(instance_id, children_ids)
            ]
        else:
            # Handling a generic child ID, return a transition for each child
            condition_prefix = "" if self._condition is None else f"({self._condition}) &amp;&amp; "
            return [
                ScxmlTransition(
                    self._target,
                    [generate_bt_tick_event(child_id)],
                    condition_prefix + f"({self._child_id} == {child_id})",
                    self._body,
                ).instantiate_bt_events(instance_id, children_ids)
                for child_id in children_ids
            ]

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

    def check_validity(self) -> bool:
        return True

    def instantiate_bt_events(self, instance_id: int, children_ids: List[int]) -> ScxmlSend:
        return ScxmlSend(
            generate_bt_response_event(instance_id),
            [ScxmlParam("status", expr=f"{self._status_id}")],
        )

    def as_xml(self) -> ET.Element:
        return ET.Element(BtReturnStatus.get_tag_name(), {"status": self._status})
