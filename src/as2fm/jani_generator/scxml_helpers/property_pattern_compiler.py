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

"""
Compile the specification patterns declared in a properties.xml file into JANI properties.
"""

import re
from typing import Dict, Iterable, List, Optional, Tuple

from as2fm.as2fm_common.logging import check_assertion
from as2fm.jani_generator.jani_entries import JaniExpression, JaniProperty
from as2fm.jani_generator.jani_entries.jani_expression_generator import and_operator, not_operator
from as2fm.jani_generator.scxml_helpers.scxml_expression import parse_ecmascript_to_jani_expression
from as2fm.scxml_converter.pattern_translator import (
    JANI_PATTERN_MAPPING,
    JaniExpressionTree,
    JaniPatternOp,
    PatternInfo,
)
from as2fm.scxml_converter.property_converter import PortBinding

_COMPARISON_OPERATORS = ("<=", ">=", "==", "!=", "<", ">")


def compile_patterns_to_jani_properties(
    compiled_patterns: List[Tuple[str, PatternInfo]],
    resolved_ports: Dict[str, PortBinding],
    existing_property_names: Optional[Iterable[str]] = None,
) -> List[JaniProperty]:
    """
    Compile a list of (property_id, PatternInfo) pairs into JaniProperty objects.

    :param compiled_patterns: properties parsed by PropertyConverter
    :param resolved_ports: state_var/event_var ids resolved to variable names
    :param existing_property_names: properties already present in the JANI model
    :return: one JaniProperty per compiled pattern.
    """
    seen_names = set(existing_property_names) if existing_property_names is not None else set()
    jani_properties: List[JaniProperty] = []
    for property_id, pattern_info in compiled_patterns:
        check_assertion(
            property_id not in seen_names,
            property_id,
            f"Duplicate property id '{property_id}' in JANI and XML declared properties.",
            error_type=ValueError,
        )
        mapping = JANI_PATTERN_MAPPING.get((pattern_info.pattern, pattern_info.scope))
        check_assertion(
            mapping is not None,
            property_id,
            f"No JANI encoding for pattern {pattern_info.pattern.name} with scope "
            f"{pattern_info.scope.name}.",
            error_type=NotImplementedError,
        )
        if mapping.op == JaniPatternOp.UNTIL:
            _, left_tree, right_tree = mapping.expression
            left = _compile_expression(
                left_tree, pattern_info.predicates, resolved_ports, property_id
            )
            right = _compile_expression(
                right_tree, pattern_info.predicates, resolved_ports, property_id
            )
            path_dict = {"op": mapping.op.value, "left": left, "right": right}
        else:
            predicate = _compile_expression(
                mapping.expression, pattern_info.predicates, resolved_ports, property_id
            )
            path_dict = {"op": mapping.op.value, "exp": predicate}
        expression_dict = {
            "op": "filter",
            "fun": "values",
            "values": {"op": "Pmin", "exp": path_dict},
            "states": {"op": "initial"},
        }
        jani_properties.append(JaniProperty(property_id, expression_dict))
        seen_names.add(property_id)
    return jani_properties


def _compile_expression(
    expr: JaniExpressionTree,
    predicates: Dict[str, str],
    resolved_ports: Dict[str, PortBinding],
    property_id: str,
) -> JaniExpression:
    """
    Walk a tree and build a JaniExpression.
    """
    if isinstance(expr, str):
        text = predicates[expr]
        return _resolve_predicate(text, resolved_ports, property_id)
    op, *args = expr
    if op == "not":
        child = _compile_expression(args[0], predicates, resolved_ports, property_id)
        return not_operator(child)
    raise NotImplementedError(f"Unknown expression operator: {op}")


def _resolve_predicate(
    text: str, resolved_ports: Dict[str, PortBinding], property_id: str
) -> JaniExpression:
    """
    An event_var .valid flag,
    or a state_var comparison and its source event .valid flag.
    """
    text = text.strip()
    binding = resolved_ports.get(text)
    if binding is not None and binding.kind == "event":
        return JaniExpression(binding.jani_valid_var)
    sv_binding, comparison = _resolve_state_var(text, resolved_ports, property_id)
    return and_operator(comparison, JaniExpression(sv_binding.jani_valid_var))


def _resolve_state_var(
    text: str, resolved_ports: Dict[str, PortBinding], property_id: str
) -> Tuple[PortBinding, JaniExpression]:
    """
    Find the single declared state_var referenced in a relational-comparison predicate, and
    parse the comparison against its JANI field.

    Only one shape is supported: a single comparison (<=, <, ==, !=, >=, >) against one
    declared state_var. Boolean connectives and multi-variable expressions not supported.
    """
    referenced = {
        var_id: resolved_ports[var_id]
        for var_id in resolved_ports
        if re.search(rf"\b{re.escape(var_id)}\b", text)
    }
    check_assertion(
        len(referenced) == 1,
        property_id,
        f"Predicate '{text}' must reference exactly one declared variable, "
        f"found {len(referenced)}: {list(referenced.keys()) or 'none'}.",
        error_type=ValueError,
    )
    var_id, binding = next(iter(referenced.items()))
    check_assertion(
        binding.kind == "state",
        property_id,
        f"Predicate '{text}' references event_var '{var_id}' inside a comparison - "
        "use a bare event_var id instead.",
        error_type=ValueError,
    )
    check_assertion(
        any(op in text for op in _COMPARISON_OPERATORS),
        property_id,
        f"Predicate '{text}' references state_var '{var_id}' without a comparison operator.",
        error_type=ValueError,
    )
    substituted = re.sub(rf"\b{re.escape(var_id)}\b", binding.jani_field_var, text)
    return binding, parse_ecmascript_to_jani_expression(substituted, None)
