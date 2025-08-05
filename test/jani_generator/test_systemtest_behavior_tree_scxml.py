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

import os
import unittest

import pytest

from as2fm.jani_generator.scxml_helpers.top_level_interpreter import interpret_top_level_xml

from ..as2fm_common.test_utilities_smc_storm import run_smc_storm_with_output


# pylint: disable=too-many-public-methods
class TestConversion(unittest.TestCase):
    """
    Test the conversion of SCXML to JANI.
    """

    def _test_with_main(
        self,
        path_to_main_xml: str,
        property_name: str,
        expected_result_probability: float,
        result_probability_tolerance: float = 0.0,
    ):
        """
        Testing the model resulting from the main xml file with the entrypoint.

        :param path_to_main_xml: The path to the main xml file.
        :param property_name: The property name to test.
        :param success: If the property is expected to be always satisfied or always not satisfied.
        """
        test_folder = os.path.join(os.path.dirname(__file__), "_test_data")
        main_xml_full_path = os.path.join(test_folder, path_to_main_xml)
        generated_scxml_path = "generated_plain_scxml"
        jani_file = "main.jani"
        test_folder = os.path.dirname(main_xml_full_path)
        interpret_top_level_xml(
            main_xml_full_path, jani_file="main.jani", scxmls_dir=generated_scxml_path
        )
        jani_file_path = os.path.join(test_folder, jani_file)
        generated_scxml_path = os.path.join(test_folder, generated_scxml_path)
        self.assertTrue(os.path.exists(jani_file_path))
        run_smc_storm_with_output(
            f"--model {jani_file_path} --properties-names {property_name}",
            [property_name, jani_file_path],
            [],
            expected_result_probability,
            result_probability_tolerance,
        )
        # Remove generated file (in case of test passed)
        if os.path.exists(jani_file_path):
            os.remove(jani_file_path)
        if os.path.exists(generated_scxml_path):
            for file in os.listdir(generated_scxml_path):
                assert file.endswith(".scxml")
                os.remove(os.path.join(generated_scxml_path, file))
            os.removedirs(generated_scxml_path)

    def test_reactive_sequence(self):
        """Test the reactive_sequence behavior."""
        self._test_with_main(
            os.path.join("bt_test_models", "main_test_reactive_sequence.xml"),
            "ten_tick_zero_no_tick_one",
            expected_result_probability=1.0,
        )

    def test_reactive_fallback(self):
        """Test the reactive_fallback behavior."""
        self._test_with_main(
            os.path.join("bt_test_models", "main_test_reactive_fallback.xml"),
            "ten_tick_zero_no_tick_one",
            expected_result_probability=1.0,
        )

    def test_sequence(self):
        """Test the sequence behavior."""
        self._test_with_main(
            os.path.join("bt_test_models", "main_test_sequence.xml"),
            "regular_bt_test",
            expected_result_probability=1.0,
        )

    def test_fallback(self):
        """Test the sequence behavior."""
        self._test_with_main(
            os.path.join("bt_test_models", "main_test_fallback.xml"),
            "regular_bt_test",
            expected_result_probability=1.0,
        )


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
