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

from enum import Enum
import os
from typing import List

import lxml.etree as ET
from lxml.etree import _Element as XmlElement

from as2fm.scxml_converter.ascxml_extensions.ros_entries.ros_event_info import RosEventInfo
from as2fm.scxml_converter.ascxml_extensions.ros_entries.ros_utils import sanitize_ros_interface_name
from as2fm.scxml_converter.pattern_translator import Pattern, PatternInfo, Scope, translate_pattern


class TimeUnit(Enum):
    """List of supported time units."""
    SECONDS = 1
    MILLISECONDS = 1_000
    MICROSECONDS = 1_000_000
    NANOSECONDS = 1_000_000_000

class NoneAutomaton:
    """Class generating the NONE.scxml automaton"""
    @staticmethod
    def build() -> XmlElement:
        none_automaton = ET.Element(
            "scxml",
            {
                "name": "NONE",
                "version": "1.0",
                "model_src": "",
                "initial": "init",
                "xmlns": "http://www.w3.org/2005/07/scxml",
            },
        )

        init_state = ET.SubElement(none_automaton, "state")
        init_state.set("id", "init")
        init_state.text = ""

        return none_automaton

class PropertyConverter:
    """Class handling the conversion of properties.ascxml to properties.scxml."""
    def __init__(self, input_path: str, ros_events_info: List[RosEventInfo], model_time_step, model_time_unit: str):
        parser = ET.XMLParser(remove_comments=True)
        with open(input_path, "r", encoding="utf-8") as f:
            xml_tree = ET.parse(f, parser=parser)

        root = xml_tree.getroot()
        assert root.tag == "properties", "Invalid root tag"

        self._ports_node: XmlElement = root.find("ports")
        assert self._ports_node is not None, "No ports defined"

        self._assumes_node: XmlElement = root.find("assumes")
        self._guarantees_node: XmlElement = root.find("guarantees")
        assert (
            self._assumes_node is not None or self._guarantees_node is not None,
            "No properties defined"
        )

        self._ros_events_info: List[RosEventInfo] = ros_events_info
        self._model_time_step: int = model_time_step
        self._model_time_unit: TimeUnit = PropertyConverter._string_to_time_unit(model_time_unit)

    def export_properties(self, output_path: str) -> None:
        scxml_properties = ET.Element("properties")

        ports_node = ET.SubElement(scxml_properties, "ports")
        self._process_ports(ports_node)

        if self._assumes_node is not None:
            assumes_node = ET.SubElement(scxml_properties, "assumes")
            self._process_assumes(assumes_node)

        if self._guarantees_node is not None:
            guarantees_node = ET.SubElement(scxml_properties, "guarantees")
            self._process_guarantees(guarantees_node)

        if not os.path.exists(output_path):
            os.mkdir(output_path)

        with open(os.path.join(output_path, "properties.xml"), "wb") as f:
            f.write(
                ET.tostring(
                    scxml_properties,
                    pretty_print=True,
                    xml_declaration=True,
                    encoding="UTF-8",
                )
            )

        if self._exists_none_target():
            with open(os.path.join(output_path, "NONE.scxml"), "wb") as f:
                f.write(
                    ET.tostring(
                        NoneAutomaton.build(),
                        pretty_print=True,
                        encoding="UTF-8",
                    )
                )

    def _process_ports(self, ports: XmlElement) -> None:
        """Process all port declarations in the ports section."""

        for interface in self._ports_node:
            tag = interface.tag
            assert tag in ["ros_topic", "ros_service", "ros_action"], "Invalid port tag"

            match tag:
                case "ros_topic":
                    interface_name = interface.attrib["topic_name"]
                case "ros_service":
                    interface_name = interface.attrib["service_name"]
                case "ros_action":
                    interface_name = interface.attrib["action_name"]

            interface_name = sanitize_ros_interface_name(interface_name)
            event_type = interface.attrib["event"]

            ros_info_entries: List[RosEventInfo] = []
            for entry in self._ros_events_info:
                if entry.interface_name == interface_name and entry.event_type == event_type:
                    ros_info_entries.append(entry)

            ros_info_entry = PropertyConverter._get_most_relevant_entry(ros_info_entries)

            port = ET.SubElement(ports, "scxml_event_send")
            port.set("event", ros_info_entry.scxml_event_name)
            port.set("origin", ros_info_entry.origin)
            port.set("target", ros_info_entry.target)

            for var in interface:
                assert var.tag in ["state_var", "event_var", "goal_id", "result_code"], "Invalid variable type"
                v = ET.SubElement(port, var.tag)
                v.set("id", var.attrib["id"])
                if var.tag == "state_var":
                    v.set("type", var.attrib["type"])
                    v.set("expr", var.attrib["expr"])
                    for field in ros_info_entry.fields:
                        if var.attrib["field"] in field.keys():
                            v.set("param", field[var.attrib["field"]])
                if var.tag == "goal_id":
                    v.set("type", "int32")
                    v.set("expr", var.attrib["expr"])
                    v.set("param", "goal_id")
                if var.tag == "result_code":
                    v.set("type", "int32")
                    v.set("expr", var.attrib["expr"])
                    v.set("param", "code")

    def _process_assumes(self, assumes: XmlElement) -> None:
        self._process_properties(assumes, self._assumes_node)

    def _process_guarantees(self, guarantees: XmlElement) -> None:
        self._process_properties(guarantees, self._guarantees_node)
    
    def _process_properties(self, output_properties: XmlElement, input_properties: XmlElement) -> None:
        for property in input_properties:
            property_id = property.attrib["id"]
            pattern = property.attrib["pattern"]
            events = []
            scope = ""
            scope_events = []
            time = None

            for child in property:
                tag = child.tag
                if tag == "event":
                    events.append(child.text)
                if tag == "events":
                    for event in child:
                        events.append(event.text)
                if tag == "time_interval":
                    property_time_unit = PropertyConverter._string_to_time_unit(child.attrib["time_unit"])
                    if child.attrib.get("time") == None:
                        after = child.attrib.get("after")
                        within = child.attrib.get("within")
                        if after is not None:
                            after = self._convert_time(after, property_time_unit, self._model_time_unit)
                        if within is not None:
                            within = self._convert_time(within, property_time_unit, self._model_time_unit)
                        time = (after, within)
                    else:
                        time = child.attrib["time"]
                        time = self._convert_time(time, property_time_unit, self._model_time_unit)
                if tag == "scope":
                    scope = child.attrib["type"]
                    scope_events.append(child.attrib.get("event"))

            match pattern:
                case "universality":
                    pattern = Pattern.UNIVERSALITY
                case "absence":
                    pattern = Pattern.ABSENCE
                case "response":
                    pattern = Pattern.RESPONSE
                case "recurrence":
                    pattern = Pattern.RECURRENCE
                case "precedence":
                    pattern = Pattern.PRECEDENCE
                case "existence":
                    pattern = Pattern.EXISTENCE
                case _:
                    raise Exception

            match scope:
                case "globally":
                    scope = Scope.GLOBALLY
                case "before":
                    scope = Scope.BEFORE
                case "after":
                    scope = Scope.AFTER
                case _:
                    raise Exception

            property_pattern = PatternInfo(
                pattern=pattern,
                scope=scope,
                events=events,
                scope_events=scope_events,
                time=time,
            )
            translated_property = translate_pattern(property_pattern)
            output_property = ET.SubElement(output_properties, "property")
            output_property.set("id", property_id)
            output_property.set("expr", translated_property)

    def _convert_time(self, time_interval: str, starting_time_unit: TimeUnit, target_time_unit: TimeUnit) -> str:
        interval_value = float(time_interval)
        time_unit_ratio = target_time_unit.value / starting_time_unit.value
        assert interval_value * time_unit_ratio >= self._model_time_step, "Property time smaller than model time"
        interval_value = int((interval_value * time_unit_ratio) / self._model_time_step)

        return str(interval_value)

    def _exists_none_target(self) -> bool:
        for info in self._ros_events_info:
            if info.target == "NONE":
                return True
        return False
    
    @staticmethod
    def _string_to_time_unit(time_unit: str) -> TimeUnit:
        assert time_unit in ["s", "ms", "us", "ns"], "Unsupported time unit"
        match time_unit:
            case "s":
                return TimeUnit.SECONDS
            case "ms":
                return TimeUnit.MILLISECONDS
            case "us":
                return TimeUnit.MICROSECONDS
            case "ns":
                return TimeUnit.NANOSECONDS
    
    @staticmethod
    def _get_most_relevant_entry(entries: List[RosEventInfo]) -> RosEventInfo:
        """Returns an entry not containing events sent to/received by the BT if possible"""
        relevant_entries: List[RosEventInfo] = []
        for e in entries:
            if not e.is_bt_info():
                relevant_entries.append(e)
        if len(relevant_entries) == 0:
            relevant_entries = entries
        return relevant_entries[0]
