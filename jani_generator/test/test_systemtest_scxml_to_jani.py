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

"""Test the SCXML conversion to JANI"""

import json
import os
import unittest
import xml.etree.ElementTree as ET
from pprint import pprint

import pytest
from jani_generator.jani_entries import JaniModel
from jani_generator.jani_entries.jani_automaton import JaniAutomaton
from jani_generator.scxml_helpers.scxml_event import EventsHolder
from jani_generator.scxml_helpers.scxml_to_jani import (
    convert_multiple_scxmls_to_jani, convert_scxml_element_to_jani_automaton,
    interpret_top_level_xml)
from .test_utilities_smc_storm import run_smc_storm_with_output


class TestConversion(unittest.TestCase):
    def test_basic_example(self):
        """
        Very basic example of a SCXML file.
        """
        basic_scxml = """
        <scxml
          version="1.0"
          initial="Initial">
            <state id="Initial">
                <onentry>
                    <assign location="x" expr="42" />
                </onentry>
            </state>
        </scxml>"""
        basic_scxml = ET.fromstring(basic_scxml)
        jani_a = JaniAutomaton()
        eh = EventsHolder()
        convert_scxml_element_to_jani_automaton(basic_scxml, jani_a, eh)

        automaton = jani_a.as_dict(constant={})
        self.assertEqual(len(automaton["locations"]), 1)
        init_location = automaton["locations"][0]
        self.assertIn("Initial", init_location["name"])
        self.assertIn("Initial", automaton["initial-locations"])

    def test_battery_drainer(self):
        """
        Testing conversion with the battery_drainer SCXML files.
        """
        scxml_battery_drainer = os.path.join(
            os.path.dirname(__file__), '_test_data', 'battery_example',
            'battery_drainer.scxml')
        with open(scxml_battery_drainer, 'r', encoding='utf-8') as f:
            basic_scxml = ET.parse(f).getroot()

        jani_a = JaniAutomaton()
        eh = EventsHolder()
        convert_scxml_element_to_jani_automaton(basic_scxml, jani_a, eh)

        automaton = jani_a.as_dict(constant={})
        self.assertEqual(automaton["name"], "BatteryDrainer")
        self.assertEqual(len(automaton["locations"]), 2)
        self.assertEqual(len(automaton["initial-locations"]), 1)
        init_location = automaton["locations"][0]
        self.assertEqual(init_location['name'],
                         automaton.get("initial-locations")[0])
        self.assertEqual(len(automaton["edges"]), 2)

        # Variables
        self.assertEqual(len(automaton["variables"]), 1)
        variable = automaton["variables"][0]
        self.assertEqual(variable["name"], "battery_percent")
        self.assertEqual(variable["type"], "int")
        self.assertEqual(variable["initial-value"], 100)

    def test_battery_manager(self):
        """
        Testing conversion with the battery_manager SCXML files.
        """
        scxml_battery_manager = os.path.join(
            os.path.dirname(__file__), '_test_data', 'battery_example',
            'battery_manager.scxml')
        with open(scxml_battery_manager, 'r', encoding='utf-8') as f:
            basic_scxml = ET.parse(f).getroot()

        jani_a = JaniAutomaton()
        eh = EventsHolder()
        convert_scxml_element_to_jani_automaton(basic_scxml, jani_a, eh)

        automaton = jani_a.as_dict(constant={})
        self.assertEqual(automaton["name"], "BatteryManager")
        self.assertEqual(len(automaton["locations"]), 1)
        self.assertEqual(len(automaton["initial-locations"]), 1)
        init_location = automaton["locations"][0]
        self.assertEqual(init_location['name'],
                         automaton.get("initial-locations")[0])
        self.assertEqual(len(automaton["edges"]), 1)

        # Variables
        self.assertEqual(len(automaton["variables"]), 1)
        variable = automaton["variables"][0]
        self.assertEqual(variable["name"], "battery_alarm")
        self.assertEqual(variable["type"], "bool")
        self.assertEqual(variable["initial-value"], False)

    def test_example_with_sync(self):
        """
        Testing the conversion of two SCXML files with a sync.
        """
        TEST_DATA_FOLDER = os.path.join(
            os.path.dirname(__file__), '_test_data', 'battery_example')
        scxml_battery_drainer_path = os.path.join(
            TEST_DATA_FOLDER, 'battery_drainer.scxml')
        scxml_battery_manager_path = os.path.join(
            TEST_DATA_FOLDER, 'battery_manager.scxml')
        with open(scxml_battery_drainer_path, 'r', encoding='utf-8') as f:
            scxml_battery_drainer = f.read()
        with open(scxml_battery_manager_path, 'r', encoding='utf-8') as f:
            scxml_battery_manager = f.read()

        jani_model = convert_multiple_scxmls_to_jani([
            scxml_battery_drainer,
            scxml_battery_manager],
            [],
            0
        )
        jani_dict = jani_model.as_dict()
        # pprint(jani_dict)

        # Check automata
        self.assertEqual(len(jani_dict["automata"]), 3)
        names = [a["name"] for a in jani_dict["automata"]]
        self.assertIn("BatteryDrainer", names)
        self.assertIn("BatteryManager", names)
        self.assertIn("level", names)

        # Check the syncs
        elements = jani_dict["system"]["elements"]
        self.assertEqual(len(elements), 3)
        self.assertIn({"automaton": "BatteryDrainer"}, elements)
        self.assertIn({"automaton": "BatteryManager"}, elements)
        self.assertIn({"automaton": "level"}, elements)
        syncs = jani_dict["system"]["syncs"]
        self.assertEqual(len(syncs), 3)
        self.assertIn({'result': 'level_on_send',
                       'synchronise': [
                           'level_on_send', None, 'level_on_send']},
                      syncs)
        self.assertIn({'result': 'level_on_receive',
                       'synchronise': [
                           None, 'level_on_receive', 'level_on_receive']},
                      syncs)

        # Check global variables for event
        variables = jani_dict["variables"]
        self.assertEqual(len(variables), 2)
        self.assertIn({"name": "level.valid",
                       "type": "bool",
                       "initial-value": False,
                       "transient": False}, variables)
        self.assertIn({"name": "level.data",
                       "type": "int",
                       "initial-value": 0,
                       "transient": False}, variables)

        # Check full jani file
        TEST_FILE = os.path.join(
            TEST_DATA_FOLDER, 'output.jani')
        GROUND_TRUTH_FILE = os.path.join(
            TEST_DATA_FOLDER, 'output_GROUND_TRUTH.jani')
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)
        with open(TEST_FILE, "w", encoding='utf-8') as output_file:
            json.dump(jani_dict, output_file,
                      indent=4, ensure_ascii=False)
        with open(GROUND_TRUTH_FILE, "r", encoding='utf-8') as f:
            ground_truth = json.load(f)
        self.maxDiff = None
        self.assertEqual(jani_dict, ground_truth)
        # TODO: Can't test this in storm right now, because it has no properties.
        if os.path.exists(TEST_FILE):
            os.remove(TEST_FILE)

    def _test_with_entrypoint(self, main_xml: str, success: bool):
        """Testing the conversion of the main.xml file with the entrypoint."""
        test_data_dir = os.path.join(
            os.path.dirname(__file__), '_test_data', 'ros_example')
        xml_main_path = os.path.join(test_data_dir, main_xml)
        ouput_path = os.path.join(test_data_dir, 'main.jani')
        if os.path.exists(ouput_path):
            os.remove(ouput_path)
        interpret_top_level_xml(xml_main_path)
        self.assertTrue(os.path.exists(ouput_path))
        ground_truth = os.path.join(
            test_data_dir,
            'jani_model_GROUND_TRUTH.jani')
        with open(ouput_path, "r", encoding='utf-8') as f:
            jani_dict = json.load(f)
        with open(ground_truth, "r", encoding='utf-8') as f:
            ground_truth = json.load(f)
        self.maxDiff = None
        # self.assertEqual(jani_dict, ground_truth)
        property_name = "battery_depleted"
        pos_res = "Result: 1" if success else "Result: 0"
        neg_res = "Result: 0" if success else "Result: 1"
        run_smc_storm_with_output(
            f"--model {ouput_path} --property-name {property_name}",
            [property_name,
             ouput_path,
             pos_res],
            [neg_res])
        if os.path.exists(ouput_path):
            os.remove(ouput_path)

    def test_with_entrypoint_main_success(self):
        """Test the main.xml file with the entrypoint.
        Here we expect the property to be satisfied."""
        self._test_with_entrypoint('main.xml', True)

    def test_with_entrypoint_main_fail(self):
        """Test the main_failing.xml file with the entrypoint.
        Here we expect the property to be *not* satisfied."""
        self._test_with_entrypoint('main_failing_prop.xml', False)


if __name__ == '__main__':
    pytest.main(['-s', '-v', __file__])
