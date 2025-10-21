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

"""Generic declaration ASCXML entry."""

from abc import abstractmethod

from typing_extensions import Self

from as2fm.scxml_converter.scxml_entries import ScxmlBase


class AscxmlThread(ScxmlBase):
    """Base class for thread definition in ASCXML."""

    @classmethod
    @abstractmethod
    def get_tag_name(cls) -> str:
        """The xml tag related to the declaration."""
        pass

    @classmethod
    @abstractmethod
    def from_xml_tree_impl(cls, xml_tree, custom_data_types) -> Self:
        """Create an instance of the class from an XML tree."""
        pass
