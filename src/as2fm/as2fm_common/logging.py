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

import lxml.etree

from as2fm.as2fm_common.common import is_comment

# This is the name of an internal attribute that is used to store the filepath of an element.
INTERNAL_FILEPATH_ATTR = "_filepath"


class Severity(Enum):
    """
    Enum to represent the severity of the error.
    """

    ERROR = auto()
    WARNING = auto()
    INFO = auto()


def set_filepath_for_all_elements(root: "lxml.etree._Element", filepath: str) -> None:
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


def _assemble_message(severity: Severity, element: "lxml.etree._Element", message: str) -> str:
    """
    Produce an logging message with the line number of the element.

    :param severity: The severity of the error
    :param element: The element that caused the error
    :param message: The message
    :return: The message with path and line number
    """
    assert hasattr(element, "sourceline"), (
        "The element must have a sourceline attribute. This is set by the parser, "
        "i. e. when `lxml.etree.ElementTree` is used."
    )
    assert INTERNAL_FILEPATH_ATTR in element.attrib.keys(), (
        "The element must have a filepath attribute. This is set by "
        "`as2fm_common.logging.set_filepath_for_all_elements`."
    )
    severity_initial = severity.name[0]
    path = element.attrib[INTERNAL_FILEPATH_ATTR]
    return f"{severity_initial} ({path}:{element.sourceline}) {message}"


def error(element: "lxml.etree._Element", message: str) -> str:
    """
    Log an error message.

    :param element: The element that caused the error
    :param message: The message
    :return: The message with the line number
    """
    return _assemble_message(Severity.ERROR, element, message)


def warn(element: "lxml.etree._Element", message: str) -> str:
    """
    Log a warning message.

    :param element: The element that caused the warning
    :param message: The message
    :return: The message with the line number
    """
    return _assemble_message(Severity.WARNING, element, message)


def info(element: "lxml.etree._Element", message: str) -> str:
    """
    Log an info message.

    :param element: The element that caused the info message
    :param message: The message
    :return: The message with the line number
    """
    return _assemble_message(Severity.INFO, element, message)
