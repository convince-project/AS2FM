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

""""Test the SCXML data conversion from all possible declaration types"""

import unittest
import xml.etree.ElementTree as ET
from typing import MutableSequence

import pytest

from as2fm.as2fm_common.logging import AS2FMLogger
from as2fm.scxml_converter.scxml_entries import ScxmlData, ScxmlDataModel


class TestScxmlData(unittest.TestCase):
    """
    Test the correct parsing of the SCXML data tags.
    """

    def test_no_type_information(self):
        """
        Test with no type information should raise a ValueError.
        """
        tag = ET.fromstring('<data id="level" />')
        with self.assertRaises(AssertionError):
            ScxmlData.from_xml_tree(tag, "", AS2FMLogger())
        tag = ET.fromstring('<data id="level" expr="0" />')
        with self.assertRaises(AssertionError):
            ScxmlData.from_xml_tree(tag, "", AS2FMLogger())

    def test_no_expr_information(self):
        """
        Test with no expr information should raise a AssertionError.
        """
        tag = ET.fromstring('<data id="level" type="int32" />')
        with self.assertRaises(AssertionError):
            ScxmlData.from_xml_tree(tag, "", AS2FMLogger())

    def test_no_id_information(self):
        """
        Test with no id information should raise a AssertionError.
        """
        tag = ET.fromstring('<data type="int32" expr="0" />')
        with self.assertRaises(AssertionError):
            ScxmlData.from_xml_tree(tag, "", AS2FMLogger())

    def test_regular_int_tag(self):
        """
        Test with regular tag with type int32.
        """
        tag = ET.fromstring('<data id="level" type="int32" expr="0" />')
        scxml_data = ScxmlData.from_xml_tree(tag, "", AS2FMLogger())
        self.assertEqual(scxml_data.get_name(), "level")
        self.assertEqual(scxml_data.get_type(), int)
        self.assertEqual(scxml_data.get_expr(), "0")

    def test_regular_float_tag(self):
        """
        Test with regular tag with type int32.
        """
        tag = ET.fromstring('<data id="level_float" type="float32" expr="1.1" />')
        scxml_data = ScxmlData.from_xml_tree(tag, "", AS2FMLogger())
        self.assertEqual(scxml_data.get_name(), "level_float")
        self.assertEqual(scxml_data.get_type(), float)
        self.assertEqual(scxml_data.get_expr(), "1.1")

    def test_regular_bool_tag(self):
        """
        Test with regular tag with type int32.
        """
        tag = ET.fromstring('<data id="condition" type="bool" expr="true" />')
        scxml_data = ScxmlData.from_xml_tree(tag, "", AS2FMLogger())
        self.assertEqual(scxml_data.get_name(), "condition")
        self.assertEqual(scxml_data.get_type(), bool)
        self.assertEqual(scxml_data.get_expr(), "true")

    def test_regular_int_array_tag(self):
        """
        Test with regular tag with type int32.
        """
        tag = ET.fromstring('<data id="some_array" type="int32[]" expr="[]" />')
        scxml_data = ScxmlData.from_xml_tree(tag, "", AS2FMLogger())
        self.assertEqual(scxml_data.get_name(), "some_array")
        self.assertEqual(scxml_data.get_type(), MutableSequence[int])
        self.assertEqual(scxml_data.get_expr(), "[]")

    # Tests with comment above the data tag ####################################
    def test_comment_int32(self):
        """
        Test with comment above and type int32.

        src https://github.com/convince-project/data-model/blob/\
            00d8b3356f632db3d6a564cf467c482f900a8657/examples/museum-guide/\
            environment-XML/batteryDriverCmp.scxml#L11C1-L11C28
        """
        comment_above = "TYPE level:int32"
        tag = ET.fromstring('<data id="level" expr="0" />')
        scxml_data = ScxmlData.from_xml_tree(tag, comment_above, AS2FMLogger())
        self.assertEqual(scxml_data.get_name(), "level")
        self.assertEqual(scxml_data.get_expr(), "0")
        self.assertEqual(scxml_data.get_type(), int)

    def test_invalid_id_in_comment(self):
        """
        Test with comment above and type int32.

        src https://github.com/convince-project/data-model/blob/\
            00d8b3356f632db3d6a564cf467c482f900a8657/examples/museum-guide/\
            environment-XML/batteryDriverCmp.scxml#L11C1-L11C28
        """
        comment_above = "TYPE other:int32"
        tag = ET.fromstring('<data id="level" expr="0" />')
        self.assertRaises(
            AssertionError, ScxmlData.from_xml_tree, tag, comment_above, AS2FMLogger()
        )

    def test_datamodel_loading(self):
        """
        Test the loading of the datamodel.
        """
        xml_parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        xml_tree = ET.fromstring(
            "<datamodel>"
            '<data id="level" type="int32" expr="0" />'
            '<data id="level_float" type="float32" expr="1.1" />'
            "<!-- TYPE condition:bool -->"
            '<data id="condition" expr="true" />'
            '<data id="some_array" type="int32[]" expr="[]" />'
            "</datamodel>",
            xml_parser,
        )
        scxml_data_model = ScxmlDataModel.from_xml_tree(xml_tree, AS2FMLogger())
        data_entries = scxml_data_model.get_data_entries()
        self.assertEqual(len(data_entries), 4)
        self.assertEqual(data_entries[0].get_name(), "level")
        self.assertEqual(data_entries[1].get_name(), "level_float")
        self.assertEqual(data_entries[2].get_name(), "condition")
        self.assertEqual(data_entries[3].get_name(), "some_array")


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__, "-k", "test_datamodel_loading"])
