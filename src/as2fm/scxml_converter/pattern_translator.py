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

"""Collection of classes and functions to translate property patterns into LTL/MTL properties."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Optional, Tuple, Union

from jinja2 import Template


class Pattern(Enum):
    """List of supported patterns."""

    UNIVERSALITY = auto()
    ABSENCE = auto()
    RESPONSE = auto()
    RECURRENCE = auto()
    PRECEDENCE = auto()
    EXISTENCE = auto()


class Scope(Enum):
    """List of supported scopes."""

    GLOBALLY = auto()
    BEFORE = auto()
    AFTER = auto()


class PropertyTemplates:
    MTL_UNIVERSALITY_GLOBALLY: str = (
        "historically{% if time != None %}[:{{ time }}]{% endif %}({ {{event}} })"
    )
    MTL_UNIVERSALITY_AFTER: str = (
        "historically{% if time != None %}[:{{ time }}]{% endif %}"
        "( once({ {{scope_event}} }) -> { {{event}} })"
    )
    MTL_ABSENCE_GLOBALLY: str = (
        "historically{% if time != None %}[:{{ time }}]{% endif %}(not({ {{event}} }))"
    )
    MTL_ABSENCE_AFTER: str = (
        "historically{% if time != None %}[:{{ time }}]{% endif %}"
        "( once({ {{scope_event}} }) -> not({ {{event}} }))"
    )
    MTL_RESPONSE_GLOBALLY: str = (
        "historically( not( not({ {{ response }} }) since{% if time != None %}"
        "[{{ time }}:]{% endif %} ({ {{ request }} }) ) )"
    )
    MTL_RECURRENCE_GLOBALLY: str = (
        "historically( (once[{{time}}:] true) -> (once[:{{time}}]{ {{event}} }) )"
    )
    MTL_PRECEDENCE_GLOBALLY: str = (
        "historically( ({ {{second}} }) -> once{% if after != None and within != None %}"
        "[{{after}}:{{within}}]{% elif after != None %}[{{after}}:]{% elif within != None %}"
        "[:{{within}}]{% endif %}({ {{first}} }) )"
    )
    MTL_EXISTENCE_GLOBALLY: str = "once{% if time != None %}[:{{ time }}]{% endif %}({ {{event}} })"


@dataclass()
class PatternInfo:
    """
    Information of a property pattern.

    :attribute pattern: The pattern of the property.
    :attribute scope: The scope of the pattern.
    :attribute events: The list of predicates involved in the property.
    :attribute scope_events: The list of predicates defining the scope of the property.
    :attribute time: Value defining an interval in the property.
    """

    pattern: Pattern
    scope: Scope
    events: List[str] = field(default_factory=list)
    scope_events: List[str] = field(default_factory=list)
    time: Optional[Union[str, Tuple[str, str]]] = None


def translate_pattern(pattern: PatternInfo) -> str:
    match pattern.pattern:
        case Pattern.UNIVERSALITY:
            return _translate_universality(pattern)
        case Pattern.ABSENCE:
            return _translate_absence(pattern)
        case Pattern.RESPONSE:
            return _translate_response(pattern)
        case Pattern.RECURRENCE:
            return _translate_recurrence(pattern)
        case Pattern.PRECEDENCE:
            return _translate_precedence(pattern)
        case Pattern.EXISTENCE:
            return _translate_existence(pattern)
        case _:
            raise ValueError("Unsupported pattern")


def _translate_universality(pattern: PatternInfo) -> str:
    assert pattern.scope in [Scope.GLOBALLY, Scope.AFTER], "Unsupported scope"
    if pattern.scope == Scope.GLOBALLY:
        template = Template(PropertyTemplates.MTL_UNIVERSALITY_GLOBALLY)
        property = template.render(
            event=pattern.events[0],
            time=pattern.time,
        )
    if pattern.scope == Scope.AFTER:
        template = Template(PropertyTemplates.MTL_UNIVERSALITY_AFTER)
        property = template.render(
            event=pattern.events[0],
            time=pattern.time,
            scope_event=pattern.scope_events[0],
        )
    return property


def _translate_absence(pattern: PatternInfo) -> str:
    assert pattern.scope in [Scope.GLOBALLY, Scope.AFTER], "Unsupported scope"
    if pattern.scope == Scope.GLOBALLY:
        template = Template(PropertyTemplates.MTL_ABSENCE_GLOBALLY)
        property = template.render(
            event=pattern.events[0],
            time=pattern.time,
        )
    if pattern.scope == Scope.AFTER:
        template = Template(PropertyTemplates.MTL_ABSENCE_AFTER)
        property = template.render(
            event=pattern.events[0],
            time=pattern.time,
            scope_event=pattern.scope_events[0],
        )
    return property


def _translate_response(pattern: PatternInfo) -> str:
    assert pattern.scope in [Scope.GLOBALLY], "Unsupported scope"
    if pattern.scope == Scope.GLOBALLY:
        template = Template(PropertyTemplates.MTL_RESPONSE_GLOBALLY)
        property = template.render(
            request=pattern.events[0],
            response=pattern.events[1],
            time=pattern.time,
        )
    return property


def _translate_recurrence(pattern: PatternInfo) -> str:
    assert pattern.scope in [Scope.GLOBALLY], "Unsupported scope"
    assert pattern.time is not None, "Time not specified, property needs to be timed"
    if pattern.scope == Scope.GLOBALLY:
        template = Template(PropertyTemplates.MTL_RECURRENCE_GLOBALLY)
        property = template.render(
            event=pattern.events[0],
            time=pattern.time,
        )
    return property


def _translate_precedence(pattern: PatternInfo) -> str:
    assert pattern.scope in [Scope.GLOBALLY], "Unsupported scope"
    if pattern.time is None:
        pattern.time = (None, None)
    if pattern.scope == Scope.GLOBALLY:
        template = Template(PropertyTemplates.MTL_PRECEDENCE_GLOBALLY)
        property = template.render(
            first=pattern.events[0],
            second=pattern.events[1],
            after=pattern.time[0],
            within=pattern.time[1],
        )
    return property


def _translate_existence(pattern: PatternInfo) -> str:
    assert pattern.scope in [Scope.GLOBALLY], "Unsupported scope"
    if pattern.scope == Scope.GLOBALLY:
        template = Template(PropertyTemplates.MTL_EXISTENCE_GLOBALLY)
        property = template.render(
            event=pattern.events[0],
            time=pattern.time,
        )
    return property
