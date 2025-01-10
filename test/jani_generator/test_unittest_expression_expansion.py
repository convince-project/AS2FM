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

from as2fm.jani_generator.jani_entries import generate_jani_expression
from as2fm.jani_generator.jani_entries.jani_convince_expression_expansion import (
    expand_distribution_expressions,
)


def test_jani_expression_expansion_no_distribution():
    """
    Test the expansion of an expression containing no distribution (should stay the same).
    """
    jani_entry = generate_jani_expression(5)
    jani_expressions = expand_distribution_expressions(jani_entry)
    assert len(jani_expressions) == 1, "Expression without distribution should not be expanded!"
    assert jani_entry.as_dict() == jani_expressions[0].as_dict()
    jani_entry = generate_jani_expression(
        {"op": "*", "left": 2, "right": {"op": "floor", "exp": 1.1}}
    )
    jani_expressions = expand_distribution_expressions(jani_entry)
    assert len(jani_expressions) == 1, "Expression without distribution should not be expanded!"
    assert jani_entry.as_dict() == jani_expressions[0].as_dict()


def test_jani_expression_expansion_distribution():
    """
    Test the expansion of an expression with only a distribution.
    """
    # Simplest case, just a distribution. Boundaries are included
    n_options = 100
    jani_distribution = generate_jani_expression({"distribution": "Uniform", "args": [1.0, 3.0]})
    jani_expressions = expand_distribution_expressions(jani_distribution, n_options=n_options)
    assert len(jani_expressions) == n_options, "Base distribution was not expanded!"
    assert all(expr.as_literal() is not None for expr in jani_expressions)
    assert jani_expressions[0].as_literal().value() == pytest.approx(1.0)
    assert jani_expressions[99].as_literal().value() == pytest.approx(2.98)
    assert jani_expressions[10].as_literal().value() == pytest.approx(1.2)
    # Test a non trivial expression
    jani_distribution = generate_jani_expression(
        {
            "op": "floor",
            "exp": {
                "op": "*",
                "left": {"distribution": "Uniform", "args": [0.0, 1.0]},
                "right": 20,
            },
        }
    )
    jani_expressions = expand_distribution_expressions(jani_distribution, n_options=n_options)
    assert len(jani_expressions) == n_options, "Base distribution was not expanded!"
    assert jani_expressions[0].as_dict() == {
        "op": "floor",
        "exp": {"op": "*", "left": 0.0, "right": 20},
    }
    assert jani_expressions[10].as_dict() == {
        "op": "floor",
        "exp": {"op": "*", "left": 0.1, "right": 20},
    }
    assert jani_expressions[99].as_dict() == {
        "op": "floor",
        "exp": {"op": "*", "left": 0.99, "right": 20},
    }


def test_jani_expression_expansion_expr_with_multiple_distribution():
    """
    Test the expansion of complex expressions with multiple distributions.
    """
    # Multiple distributions at the same level
    n_options = 20
    jani_distribution = generate_jani_expression(
        {
            "op": "floor",
            "exp": {
                "op": "*",
                "left": {"distribution": "Uniform", "args": [0.0, 20.0]},
                "right": {"distribution": "Uniform", "args": [0.0, 10.0]},
            },
        }
    )
    jani_expressions = expand_distribution_expressions(jani_distribution, n_options=n_options)
    assert len(jani_expressions) == n_options**2, "Base distribution was not expanded!"
    assert jani_expressions[0].as_dict() == {
        "op": "floor",
        "exp": {"op": "*", "left": 0.0, "right": 0.0},
    }
    assert jani_expressions[-1].as_dict() == {
        "op": "floor",
        "exp": {"op": "*", "left": 19.0, "right": 9.5},
    }
    assert jani_expressions[-2].as_dict() == {
        "op": "floor",
        "exp": {"op": "*", "left": 19.0, "right": 9.0},
    }
    # Multiple distributions at a different level
    jani_distribution = generate_jani_expression(
        {
            "op": "*",
            "left": {"distribution": "Uniform", "args": [0.0, 20.0]},
            "right": {
                "op": "*",
                "left": 2,
                "right": {"distribution": "Uniform", "args": [0.0, 10.0]},
            },
        }
    )
    jani_expressions = expand_distribution_expressions(jani_distribution, n_options=n_options)
    assert len(jani_expressions) == n_options**2, "Base distribution was not expanded!"
    assert jani_expressions[0].as_dict() == {
        "op": "*",
        "left": 0.0,
        "right": {"op": "*", "left": 2, "right": 0.0},
    }
    assert jani_expressions[-1].as_dict() == {
        "op": "*",
        "left": 19.0,
        "right": {"op": "*", "left": 2, "right": 9.5},
    }
    assert jani_expressions[1].as_dict() == {
        "op": "*",
        "left": 0.0,
        "right": {"op": "*", "left": 2, "right": 0.5},
    }
