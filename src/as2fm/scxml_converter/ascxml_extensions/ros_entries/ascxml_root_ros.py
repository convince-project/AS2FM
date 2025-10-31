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

from typing import List, Type

from as2fm.scxml_converter.ascxml_extensions.ros_entries import RosActionThread, RosDeclaration
from as2fm.scxml_converter.scxml_entries import AscxmlDeclaration, AscxmlThread, GenericScxmlRoot


class AscxmlRootROS(GenericScxmlRoot):
    """
    The main entry point of specialized ASCXML Models for ROS nodes.
    In XML, it uses the tag `ascxml`.
    """

    @staticmethod
    def get_tag_name() -> str:
        """Get the expected tag name related to this class."""
        return "ascxml"

    @classmethod
    def get_declaration_classes(cls) -> List[Type[AscxmlDeclaration]]:
        return RosDeclaration.__subclasses__()  # type: ignore

    @classmethod
    def get_thread_classes(cls) -> List[Type[AscxmlThread]]:
        return [RosActionThread]  # type: ignore

    def add_declaration(self, ros_declaration: RosDeclaration):
        """Add a new ROS declaration to the ASCXML model"""
        assert isinstance(
            ros_declaration, RosDeclaration
        ), "Error: ASCXML root: invalid ROS declaration type."
        assert ros_declaration.check_validity(), "Error: SCXML root: invalid ROS declaration."
        self._ascxml_declarations.append(ros_declaration)

    def add_thread(self, action_thread: RosActionThread):
        """Add a new thread to the ASCXML model, relative to a ROS action."""
        assert isinstance(
            action_thread, RosActionThread
        ), f"Error: ASCXML root: invalid action thread type {type(action_thread)}."
        self._ascxml_threads.append(action_thread)
