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
import random
import subprocess
import unittest

import lxml.etree as ET
import pytest

from as2fm.jani_generator.scxml_helpers.scxml_event import EventsHolder
from as2fm.jani_generator.scxml_helpers.scxml_to_jani import (
    convert_multiple_scxmls_to_jani,
    convert_scxml_root_to_jani_automaton,
)
from as2fm.scxml_converter.data_types.type_utils import MEMBER_ACCESS_SUBSTITUTION
from as2fm.scxml_converter.scxml_entries import ScxmlRoot

rel_examples_folder = os.path.join("..", "..", "..", "examples")


# pylint: disable=too-many-public-methods
class TestConversion(unittest.TestCase):
    """
    Test the conversion of SCXML to JANI.
    """

    def test_basic_example(self):
        """
        Very basic example of a SCXML file.
        """
        basic_scxml = """
        <scxml
          version="1.0"
          name="BasicExample"
          initial="Initial">
            <datamodel>
                <data id="x" expr="0" type="int32" />
            </datamodel>
            <state id="Initial">
                <onentry>
                    <assign location="x" expr="42" />
                </onentry>
            </state>
        </scxml>"""
        scxml_root = ScxmlRoot.from_xml_tree(ET.fromstring(basic_scxml), [])
        eh = EventsHolder()
        jani_automaton = convert_scxml_root_to_jani_automaton(scxml_root, eh, 100)

        automaton = jani_automaton.as_dict(constant={})
        self.assertEqual(len(automaton["locations"]), 2)
        locations = [loc["name"] for loc in automaton["locations"]]
        self.assertIn("Initial-first-exec", locations)
        self.assertIn("Initial-first-exec", automaton["initial-locations"])

    def test_battery_drainer(self):
        """
        Testing conversion with the battery_drainer SCXML files.
        """
        scxml_battery_drainer = os.path.join(
            os.path.dirname(__file__), "_test_data", "battery_example", "battery_drainer.scxml"
        )

        scxml_root = ScxmlRoot.load_scxml_file(scxml_battery_drainer, {})
        eh = EventsHolder()
        jani_automaton = convert_scxml_root_to_jani_automaton(scxml_root, eh, 100)

        automaton = jani_automaton.as_dict(constant={})
        self.assertEqual(automaton["name"], "BatteryDrainer")
        self.assertEqual(len(automaton["locations"]), 4)
        self.assertEqual(len(automaton["initial-locations"]), 1)
        locations = [loc["name"] for loc in automaton["locations"]]
        self.assertIn(automaton.get("initial-locations")[0], locations)
        self.assertEqual(len(automaton["edges"]), 4)

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
            os.path.dirname(__file__), "_test_data", "battery_example", "battery_manager.scxml"
        )

        scxml_root = ScxmlRoot.load_scxml_file(scxml_battery_manager, {})
        eh = EventsHolder()
        jani_automaton = convert_scxml_root_to_jani_automaton(scxml_root, eh, 100)

        automaton = jani_automaton.as_dict(constant={})
        self.assertEqual(automaton["name"], "BatteryManager")
        self.assertEqual(len(automaton["locations"]), 1)
        self.assertEqual(len(automaton["initial-locations"]), 1)
        init_location = automaton["locations"][0]
        self.assertEqual(init_location["name"], automaton.get("initial-locations")[0])
        self.assertEqual(len(automaton["edges"]), 1)

        # Variables
        self.assertEqual(len(automaton["variables"]), 1)
        variable = automaton["variables"][0]
        self.assertEqual(variable["name"], "battery_alarm")
        self.assertEqual(variable["type"], "bool")
        self.assertEqual(variable["initial-value"], False)

    # pylint: disable=too-many-locals
    def test_example_with_sync(self):
        """
        Testing the conversion of two SCXML files with a sync.
        """
        test_data_folder = os.path.join(os.path.dirname(__file__), "_test_data", "battery_example")
        scxml_battery_drainer_path = os.path.join(test_data_folder, "battery_drainer.scxml")
        scxml_battery_manager_path = os.path.join(test_data_folder, "battery_manager.scxml")
        scxml_battery_drainer = ScxmlRoot.load_scxml_file(scxml_battery_drainer_path, {})
        scxml_battery_manager = ScxmlRoot.load_scxml_file(scxml_battery_manager_path, {})

        in_scxmls = [scxml_battery_drainer, scxml_battery_manager]
        jani_model = convert_multiple_scxmls_to_jani(in_scxmls, 100)
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
        self.assertEqual(len(syncs), 4)
        self.assertIn(
            {"result": "level_on_send", "synchronise": ["level_on_send", None, "level_on_send"]},
            syncs,
        )
        self.assertIn(
            {
                "result": "level_on_receive",
                "synchronise": [None, "level_on_receive", "level_on_receive"],
            },
            syncs,
        )

        # Check global variables for event
        variables = jani_dict["variables"]
        self.assertEqual(len(variables), 2)
        self.assertIn(
            {"name": "level.valid", "type": "bool", "initial-value": False, "transient": False},
            variables,
        )
        self.assertIn(
            {
                "name": f"level{MEMBER_ACCESS_SUBSTITUTION}data",
                "type": "int",
                "initial-value": 0,
                "transient": False,
            },
            variables,
        )

        # Check full jani file
        test_file = os.path.join(test_data_folder, "output.jani")
        ground_truth_file = os.path.join(test_data_folder, "output_GROUND_TRUTH.jani")
        if os.path.exists(test_file):
            os.remove(test_file)
        with open(test_file, "w", encoding="utf-8") as output_file:
            json.dump(jani_dict, output_file, indent=4, ensure_ascii=False)
        with open(ground_truth_file, "r", encoding="utf-8") as f:
            ground_truth = json.load(f)
        self.maxDiff = None  # pylint: disable=invalid-name
        self.assertEqual(jani_dict, ground_truth)
        # TODO: Can't test this in storm right now, because it has no properties.
        if os.path.exists(test_file):
            os.remove(test_file)

    def test_command_line_output_with_line_numbers(self):
        """Test the command line output with line numbers for the main.xml file."""
        tmp_test_dir = os.path.join("/tmp", "test_as2fm")
        if not os.path.exists(tmp_test_dir):
            os.makedirs(tmp_test_dir)
        for file in os.listdir(tmp_test_dir):
            os.remove(os.path.join(tmp_test_dir, file))
        xml_main_path = os.path.join(tmp_test_dir, "main.xml")
        offset = random.Random().randint(1, 10)
        xml_content = "\n".join([" "] * offset + ["<aa>"] + ["<bb/>"] + ["</aa>"])
        with open(xml_main_path, "w", encoding="utf-8") as f:
            f.write(xml_content)
        p = subprocess.Popen(
            ["as2fm_scxml_to_jani", xml_main_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=tmp_test_dir,
        )
        stdout, stderr = p.communicate()
        print(f"{stdout=}")
        print(f"{stderr=}")

        expected_reference = f"E (./main.xml:{offset + 1})"
        self.assertIn(expected_reference, stderr.decode("utf-8"))
        for file in os.listdir(tmp_test_dir):
            os.remove(os.path.join(tmp_test_dir, file))


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
