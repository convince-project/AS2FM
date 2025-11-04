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

"""
Modules that help produce error messages with references to the right line of the (sc)XML file
that caused the error.
"""
import os
from enum import Enum, auto
from typing import Tuple, Type, Union

from lxml.etree import _Element as XmlElement

from moco.moco_common.common import is_comment

LOCATION_INFO = Tuple[str, int]  # filename, line_number
SUPPORTED_LOCATIONS = Union[XmlElement, LOCATION_INFO, str]


# This is the name of an internal attribute that is used to store the filepath of an element.
INTERNAL_FILEPATH_ATTR = "_filepath"
SOURCELINE = "sourceline"


class Severity(Enum):
    """
    Enum to represent the severity of the error.
    """

    ERROR = auto()
    WARNING = auto()
    INFO = auto()


def set_filepath_for_all_sub_elements(root: XmlElement, filepath: str) -> None:
    """
    Set the filepath for all elements in the XML tree.

    :param root: The root element
    :param filepath: The filepath
    """
    # make a relative path for better readability (shorter)
    rel_path = os.path.relpath(filepath, os.getcwd())
    if not rel_path.startswith("./"):
        rel_path = "./" + rel_path
    # set the filepath for all elements
    for element in root.iter():
        try:
            element.attrib[INTERNAL_FILEPATH_ATTR] = rel_path
        except KeyError as e:
            if is_comment(element):
                continue
            raise e


def _get_xml_location(element: XmlElement) -> LOCATION_INFO:
    """Get location info from xml element."""
    assert hasattr(element, SOURCELINE), (
        "The element must have a sourceline attribute. This is set by the parser, "
        "i. e. when `lxml.etree.ElementTree` is used."
    )
    assert INTERNAL_FILEPATH_ATTR in element.attrib.keys(), (
        "The element must have a filepath attribute. This is set by "
        "`moco_common.logging.set_filepath_for_all_elements`."
    )
    path = element.attrib[INTERNAL_FILEPATH_ATTR]
    sourceline = element.sourceline
    return (path, sourceline)


def _assemble_message(severity: Severity, location: SUPPORTED_LOCATIONS, message: str) -> str:
    """
    Produce an logging message with the line number of the element.

    :param severity: The severity of the error
    :param location: The location that caused the error
    :param message: The message
    :return: The message with path and line number
    """

    severity_initial = severity.name[0]
    if isinstance(location, XmlElement):
        location_info = _get_xml_location(location)
    elif isinstance(location, tuple):
        assert len(location) == 2
        location_info = location
    elif isinstance(location, str):
        location_info = (location, None)
    elif location is None:
        location_info = ("UNKNOWN", None)
    else:
        raise NotImplementedError(f"Location type {location.__class__} not supported.")

    path, sourceline = location_info
    if sourceline is None:
        location_str = path
    else:
        location_str = f"{path}:{sourceline}"

    return f"{severity_initial} ({location_str}) {message}"


def get_error_msg(element: SUPPORTED_LOCATIONS, message: str) -> str:
    """
    Log an error message.

    :param element: The element that caused the error
    :param message: The message
    :return: The message with the line number
    """
    return _assemble_message(Severity.ERROR, element, message)


def get_warn_msg(element: SUPPORTED_LOCATIONS, message: str) -> str:
    """
    Log a warning message.

    :param element: The element that caused the warning
    :param message: The message
    :return: The message with the line number
    """
    return _assemble_message(Severity.WARNING, element, message)


def get_info_msg(element: SUPPORTED_LOCATIONS, message: str) -> str:
    """
    Log an info message.

    :param element: The element that caused the info message
    :param message: The message
    :return: The message with the line number
    """
    return _assemble_message(Severity.INFO, element, message)


def log_error(element: SUPPORTED_LOCATIONS, message: str) -> None:
    """
    Log an error message and print it.

    :param element: The element that caused the error
    :param message: The message
    """
    error_msg = get_error_msg(element, message)
    print(error_msg)


def log_warning(element: SUPPORTED_LOCATIONS, message: str) -> None:
    """
    Log an warning message and print it.

    :param element: The element that caused the warning
    :param message: The message
    """
    warning_msg = get_warn_msg(element, message)
    print(warning_msg)


def check_assertion(
    condition: bool,
    element: SUPPORTED_LOCATIONS,
    message: str,
    error_type: Type[BaseException] = RuntimeError,
) -> None:
    """
    Check if a condition holds, and raise an exception in case it doesn't.

    :param condition: The condition to evaluate. If False, an exception will be raised.
    :param element: The element associated with the assertion, used for error context.
    :param message: The error message to include in the raised exception.
    :param error_type: The type of exception to raise if the condition is False.

    :raises error_type: Raised when the condition is False, with the provided message.
    """
    if not condition:
        raise error_type(get_error_msg(element, message))
