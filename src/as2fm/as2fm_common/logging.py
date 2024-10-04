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
Modules that help produce better error messages.
"""

import os
import xml.etree.ElementTree as ET
from enum import Enum, auto
from typing import Optional


class Severity(Enum):
    """
    Enum to represent the severity of the error.
    """

    ERROR = auto()
    WARNING = auto()
    INFO = auto()


class AS2FMLogger:
    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = None
            return
        assert isinstance(path, str), "The path must be a string."
        assert os.path.exists(path), "The path must exist."
        cwd = os.getcwd()
        rel_path = os.path.relpath(path, cwd)
        if not rel_path.startswith("./"):
            rel_path = "./" + rel_path
        self.path = rel_path

    def _assemble_message(self, severity: Severity, element: ET.Element, message: str) -> str:
        """
        Produce an logging message with the line number of the element.

        :param severity: The severity of the error
        :param element: The element that caused the error
        :param message: The message
        :return: The message with the line number
        """
        severity_initial = severity.name[0]
        if self.path is not None:
            assert hasattr(element, "sourceline"), (
                "The element must have a sourceline attribute. This is usually set by the parser, "
                "when `lxml.etree.ElementTree` is used."
            )
            filename_with_line: str = f"({self.path}:{element.sourceline}) "
        else:
            filename_with_line = ""
        return f"{severity_initial} {filename_with_line}{message}"

    def error(self, element: ET.Element, message: str) -> str:
        """
        Log an error message.

        :param element: The element that caused the error
        :param message: The message
        :return: The message with the line number
        """
        return self._assemble_message(Severity.ERROR, element, message)

    def warning(self, element: ET.Element, message: str) -> str:
        """
        Log a warning message.

        :param element: The element that caused the warning
        :param message: The message
        :return: The message with the line number
        """
        return self._assemble_message(Severity.WARNING, element, message)

    def info(self, element: ET.Element, message: str) -> str:
        """
        Log an info message.

        :param element: The element that caused the info message
        :param message: The message
        :return: The message with the line number
        """
        return self._assemble_message(Severity.INFO, element, message)
