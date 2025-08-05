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

"""Test the SCXML data conversion"""

import unittest

import pytest

from as2fm.as2fm_common.ecmascript_interpretation import (
    ArrayInfo,
    MemberAccessCheckException,
    has_array_access,
    has_member_access,
    parse_ecmascript_expr_to_type,
)


class TestEcmascriptInterpreter(unittest.TestCase):
    """
    Test the ECMAScript interpreter.
    """

    def test_ecmascript_types(self):
        """
        Test with ECMAScript expression that evaluates to different types.

        src https://alexzhornyak.github.io/SCXML-tutorial/Doc/\
            datamodel.html#ecmascript
        """
        # Basic literals
        self.assertEqual(parse_ecmascript_expr_to_type("1", {}), int)
        self.assertEqual(parse_ecmascript_expr_to_type("1.1", {}), float)
        self.assertEqual(parse_ecmascript_expr_to_type("true", {}), bool)
        self.assertEqual(parse_ecmascript_expr_to_type("false", {}), bool)
        self.assertEqual(parse_ecmascript_expr_to_type("'ecma'", {}), ArrayInfo(int, 1, [None]))
        self.assertEqual(parse_ecmascript_expr_to_type("[1,2,3]", {}), ArrayInfo(int, 1, [None]))
        # Identifiers
        self.assertEqual(parse_ecmascript_expr_to_type("x", {"x": int}), int)
        self.assertEqual(parse_ecmascript_expr_to_type("x", {"x": bool}), bool)
        self.assertEqual(
            parse_ecmascript_expr_to_type("x", {"x": ArrayInfo(int, 1, [None])}),
            ArrayInfo(int, 1, [None]),
        )
        self.assertEqual(
            parse_ecmascript_expr_to_type("x", {"x": ArrayInfo(float, 3, [None] * 3)}),
            ArrayInfo(float, 3, [None] * 3),
        )
        # Array Access
        self.assertEqual(
            parse_ecmascript_expr_to_type("x[1]", {"x": ArrayInfo(float, 3, [None] * 3)}),
            ArrayInfo(float, 2, [None] * 2),
        )
        self.assertEqual(
            parse_ecmascript_expr_to_type("x[1][0]", {"x": ArrayInfo(float, 3, [None] * 3)}),
            ArrayInfo(float, 1, [None]),
        )
        # Expressions
        self.assertEqual(parse_ecmascript_expr_to_type("-x", {"x": int}), int)
        self.assertEqual(parse_ecmascript_expr_to_type("-x", {"x": float}), float)
        self.assertEqual(parse_ecmascript_expr_to_type("x > 1", {"x": float}), bool)
        self.assertEqual(parse_ecmascript_expr_to_type("x != y", {"x": float, "y": float}), bool)
        self.assertEqual(
            parse_ecmascript_expr_to_type("x != y && y < 2.0", {"x": float, "y": float}), bool
        )

    def test_ecmascript_unsupported(self):
        """
        Test with ECMA script expressions that evaluates to unsupported types.

        This should raise a ValueError because the types are not supported
        by Jani.

        src https://alexzhornyak.github.io/SCXML-tutorial/Doc/\
            datamodel.html#ecmascript
        """
        self.assertRaises(ValueError, parse_ecmascript_expr_to_type, "null", {})
        self.assertRaises(KeyError, parse_ecmascript_expr_to_type, "undefined", {})
        self.assertRaises(ValueError, parse_ecmascript_expr_to_type, "new Date()", {})

    def test_has_array_access(self):
        self.assertTrue(has_array_access("a[0]", None))
        self.assertTrue(has_array_access("a.b[0]", None))
        self.assertTrue(has_array_access("a.b.c[0][1]", None))
        self.assertFalse(has_array_access("a", None))
        self.assertFalse(has_array_access("a.b", None))
        self.assertFalse(has_array_access("a.b.c", None))

        self.assertRaises(MemberAccessCheckException, has_array_access, "''", None)
        self.assertRaises(MemberAccessCheckException, has_array_access, "2", None)
        self.assertRaises(MemberAccessCheckException, has_array_access, "a.b()", None)
        self.assertRaises(MemberAccessCheckException, has_array_access, "c[1]()", None)
        self.assertRaises(RuntimeError, has_array_access, "d[]", None)

    def test_has_member_access(self):
        self.assertTrue(has_member_access("a.b", None))
        self.assertTrue(has_member_access("a.b[0]", None))
        self.assertTrue(has_member_access("a.b.c[0]", None))
        self.assertFalse(has_member_access("a", None))
        self.assertFalse(has_member_access("a[0]", None))
        self.assertFalse(has_member_access("a[0][1]", None))

        self.assertRaises(MemberAccessCheckException, has_member_access, "''", None)
        self.assertRaises(MemberAccessCheckException, has_member_access, "2", None)
        self.assertRaises(MemberAccessCheckException, has_member_access, "a.b()", None)
        self.assertRaises(MemberAccessCheckException, has_member_access, "c[1]()", None)
        self.assertRaises(RuntimeError, has_member_access, "d[]", None)


if __name__ == "__main__":
    pytest.main(["-s", "-v", __file__])
