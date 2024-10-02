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

import unittest
import pytest
from array import array

from as2fm.as2fm_common.ecmascript_interpretation import interpret_ecma_script_expr


class TestEcmascriptInterpreter(unittest.TestCase):

    def test_ecmascript_types(self):
        """
        Test with ECMAScript expression that evaluates to different types.

        src https://alexzhornyak.github.io/SCXML-tutorial/Doc/\
            datamodel.html#ecmascript
        """
        self.assertEqual(interpret_ecma_script_expr("1"), 1)
        self.assertEqual(interpret_ecma_script_expr("1.1"), 1.1)
        self.assertEqual(interpret_ecma_script_expr("true"), True)
        self.assertEqual(interpret_ecma_script_expr("false"), False)
        self.assertEqual(interpret_ecma_script_expr("[1,2,3]"), array('i', [1, 2, 3]))

    def test_ecmascript_unsupported(self):
        """
        Test with ECMA script expressions that evaluates to unsupported types.

        This should raise a ValueError because the types are not supported
        by Jani.

        src https://alexzhornyak.github.io/SCXML-tutorial/Doc/\
            datamodel.html#ecmascript
        """
        self.assertRaises(ValueError, interpret_ecma_script_expr, "\'this is a string\'")
        self.assertRaises(ValueError, interpret_ecma_script_expr, "null")
        self.assertRaises(ValueError, interpret_ecma_script_expr, "undefined")
        self.assertRaises(ValueError, interpret_ecma_script_expr, "new Date()")


if __name__ == '__main__':
    pytest.main(['-s', '-v', __file__])
