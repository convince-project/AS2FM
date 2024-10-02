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

import xml.etree.ElementTree as ET


class InformativeParser(ET.XMLParser):
    """
    An extension to the ElementTree parser that stores the line number of each element.
    This will be used to provide more informative error messages.
    """

    def _start_list(self, *args, **kwargs):
        element = super(InformativeParser, self)._start_list(*args, **kwargs)
        element._file_name = self.parser._file_name  # pylint: disable=protected-access
        element._start_line_number = (
            self.parser.CurrentLineNumber
        )  # pylint: disable=protected-access
        element._start_column_number = (
            self.parser.CurrentColumnNumber
        )  # pylint: disable=protected-access
        element._start_byte_index = self.parser.CurrentByteIndex  # pylint: disable=protected-access
        return element

    def _end(self, *args, **kwargs):
        element = super(InformativeParser, self)._end(*args, **kwargs)
        element._end_line_number = self.parser.CurrentLineNumber  # pylint: disable=protected-access
        element._end_column_number = (
            self.parser.CurrentColumnNumber
        )  # pylint: disable=protected-access
        element._end_byte_index = self.parser.CurrentByteIndex  # pylint: disable=protected-access
        return element


def error(element: ET.Element, message: str) -> str:
    """
    Produce an error message with the line number of the element.

    :param element: The element that caused the error
    :param message: The error message
    :return: The error message with the line number
    """
    assert hasattr(element, "_file_name"), (
        'The element must have the attribute "_file_name" '
        "(set by `as2fm_common.logging.InformativeParser`)"
    )
    assert hasattr(element, "_start_line_number"), (
        'The element must have the attribute "_start_line_number" '
        "(set by `as2fm_common.logging.InformativeParser`)"
    )
    return (
        f"E ({element._file_name}:"  # pylint: disable=protected-access
        + f"{element._start_line_number}) "  # pylint: disable=protected-access
        + f"{message}"
    )
