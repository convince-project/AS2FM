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

from typing import Type, List

from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration
from as2fm.scxml_converter.scxml_entries import ScxmlBase


class AscxmlConfiguration(ScxmlBase):
    """
    Base class for a generic configuration entry in ASCXML.
    
    Children classes will contain values coming from external configuration.
    The configured value can be retrieved using the provided method.
    """

    @abstractmethod
    def get_configured_value(self, type: Type, ascxml_declarations: List[AscxmlDeclaration]):
        """Retrieve the configured value from the existing AscxmlDeclarations."""
        pass
