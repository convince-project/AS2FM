# Copyright (c) 2025 - for information on the respective copyright owner
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

"""Declaration of a generic ASCXML Configuration superclass."""

from abc import abstractmethod
from typing import List, Optional

from as2fm.as2fm_common.logging import get_error_msg
from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration
from as2fm.scxml_converter.scxml_entries import ScxmlBase


class AscxmlConfiguration(ScxmlBase):
    """
    Base class for a generic configuration entry in ASCXML.

    Children classes will contain values coming from external configuration.
    The configured value can be retrieved using the provided method.
    """

    def __init__(self):
        self._entry_value: Optional[str] = None

    @abstractmethod
    def update_configured_value(self, ascxml_declarations: List[AscxmlDeclaration]):
        """Configure the entry value using the existing AscxmlDeclarations"""
        pass

    def get_configured_value(self) -> str:
        """Retrieve the previously configured value."""
        assert self._entry_value is not None, get_error_msg(
            self.get_xml_origin(), "The entry value is not yet set."
        )
        return self._entry_value
