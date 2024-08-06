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

""""Test the SCXML data conversion"""

import pytest
import xml.etree.ElementTree as ET
import unittest

from jani_generator.scxml_helpers.scxml_data import ScxmlData


class TestScxmlData(unittest.TestCase):

    def test_no_type_information(self):
        """
        Test with no type information should raise a ValueError.
        """
        tag = ET.fromstring(
            '<data id="level" />')
        self.assertRaises(ValueError, ScxmlData, tag)

    # Tests with comment above the data tag ####################################
    def test_comment_int32(self):
        """
        Test with comment above and type int32.

        src https://github.com/convince-project/data-model/blob/\
            00d8b3356f632db3d6a564cf467c482f900a8657/examples/museum-guide/\
            environment-XML/batteryDriverCmp.scxml#L11C1-L11C28
        """
        comment_above = "		<!-- TYPE level:int32 -->"
        tag = ET.fromstring(
            '<data id="level" expr="0" />')
        scxml_data = ScxmlData(tag, comment_above)
        self.assertEqual(scxml_data.id, "level")
        self.assertEqual(scxml_data.xml_src, None)
        self.assertEqual(scxml_data.xml_expr, "0")
        self.assertEqual(scxml_data.type, int)
        self.assertEqual(scxml_data.initial_value, 0)

    def test_comment_boolean(self):
        """
        Test with comment above and type boolean.

        src https://github.com/convince-project/data-model/blob/\
            00d8b3356f632db3d6a564cf467c482f900a8657/examples/museum-guide/\
            environment-XML/batteryDriverCmp.scxml#L13
        """
        comment_above = "		<!-- TYPE notify:bool -->"
        tag = ET.fromstring(
            '<data id="notify" expr="false" />')
        scxml_data = ScxmlData(tag, comment_above)
        self.assertEqual(scxml_data.id, "notify")
        self.assertEqual(scxml_data.xml_src, None)
        self.assertEqual(scxml_data.xml_expr, "false")
        self.assertEqual(scxml_data.type, bool)
        self.assertEqual(scxml_data.initial_value, False)

    # Tests with type attribute ################################################
    def test_type_attr_int32(self):
        """
        Test with type int32 defined in the type attribute.

        src https://github.com/convince-project/data-model/blob/\
            00d8b3356f632db3d6a564cf467c482f900a8657/examples/museum-guide/\
            property-XML/properties.xml#L3
        """
        tag = ET.fromstring(
            '<data id="level" type="int32" />')
        scxml_data = ScxmlData(tag)
        self.assertEqual(scxml_data.id, "level")
        self.assertEqual(scxml_data.xml_src, None)
        self.assertEqual(scxml_data.xml_expr, None)
        self.assertEqual(scxml_data.type, int)
        self.assertEqual(scxml_data.initial_value, 0)

    def test_type_attr_bool(self):
        """
        Test with type bool defined in the type attribute.

        src https://github.com/convince-project/data-model/blob/\
            00d8b3356f632db3d6a564cf467c482f900a8657/examples/museum-guide/\
            property-XML/properties.xml#L11
        """
        tag = ET.fromstring(
            '<data id="alarm" type="bool" />')
        scxml_data = ScxmlData(tag)
        self.assertEqual(scxml_data.id, "alarm")
        self.assertEqual(scxml_data.xml_src, None)
        self.assertEqual(scxml_data.xml_expr, None)
        self.assertEqual(scxml_data.type, bool)
        self.assertEqual(scxml_data.initial_value, False)

    def test_comment_conflicting_type(self):
        """
        Test with conflicting type in comment and type attribute.
        """
        comment_above = "		<!-- TYPE notify:int32 -->"
        tag = ET.fromstring(
            '<data id="notify" type="bool" expr="false" />')
        self.assertRaises(ValueError, ScxmlData, tag, comment_above)

    # Tests with ECMAScript expressions ########################################
    def test_ecmascript_bool(self):
        """
        Test with ECMAScript expression that evaluates to a boolean.

        src https://alexzhornyak.github.io/SCXML-tutorial/Doc/\
            datamodel.html#ecmascript
        """
        tag = ET.fromstring(
            '<data id="VarBool" expr="true"/>')
        scxml_data = ScxmlData(tag)
        self.assertEqual(scxml_data.id, "VarBool")
        self.assertEqual(scxml_data.xml_src, None)
        self.assertEqual(scxml_data.xml_expr, "true")
        self.assertEqual(scxml_data.type, bool)
        self.assertEqual(scxml_data.initial_value, True)

    def test_ecmascript_int(self):
        """
        Test with ECMAScript expression that evaluates to a boolean.

        src https://alexzhornyak.github.io/SCXML-tutorial/Doc/\
            datamodel.html#ecmascript
        """
        tag = ET.fromstring(
            '<data id="VarInt" expr="555"/>')
        scxml_data = ScxmlData(tag)
        self.assertEqual(scxml_data.id, "VarInt")
        self.assertEqual(scxml_data.xml_src, None)
        self.assertEqual(scxml_data.xml_expr, "555")
        self.assertEqual(scxml_data.type, int)
        self.assertEqual(scxml_data.initial_value, 555)

    def test_ecmascript_float(self):
        """
        Test with ECMAScript expression that evaluates to a boolean.

        src https://alexzhornyak.github.io/SCXML-tutorial/Doc/\
            datamodel.html#ecmascript
        """
        tag = ET.fromstring(
            '<data id="VarFloat" expr="777.777"/>')
        scxml_data = ScxmlData(tag)
        self.assertEqual(scxml_data.id, "VarFloat")
        self.assertEqual(scxml_data.xml_src, None)
        self.assertEqual(scxml_data.xml_expr, "777.777")
        self.assertEqual(scxml_data.type, float)
        self.assertEqual(scxml_data.initial_value, 777.777)

    def test_ecmascript_unsupported(self):
        """
        Test with ECMA script expressions that evaluates to unsupported types.

        This should raise a ValueError because the types are not supported
        by Jani.

        src https://alexzhornyak.github.io/SCXML-tutorial/Doc/\
            datamodel.html#ecmascript
        """
        tag_str = ET.fromstring(
            '<data id="VarString" expr="\'this is a string\'"/>')
        self.assertRaises(ValueError, ScxmlData, tag_str)
        tag_function = ET.fromstring(
            '<data id="VarFunction" expr=' +
            '"function() { return \'hello from func\' }"/>')
        self.assertRaises(ValueError, ScxmlData, tag_function)
        tag_null = ET.fromstring(
            '<data id="VarNull" expr="null"/>')
        self.assertRaises(ValueError, ScxmlData, tag_null)
        tag_undefined = ET.fromstring(
            '<data id="VarUndefined" expr="undefined"/>')
        self.assertRaises(ValueError, ScxmlData, tag_undefined)
        tag_object = ET.fromstring(
            '<data id="VarComplexObject" expr="new Date()"/>')
        self.assertRaises(ValueError, ScxmlData, tag_object)


if __name__ == '__main__':
    pytest.main(['-s', '-v', __file__])
