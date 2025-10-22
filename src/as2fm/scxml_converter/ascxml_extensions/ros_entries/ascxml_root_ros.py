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

from typing import List, Optional, Type

from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration, AscxmlThread
from as2fm.scxml_converter.ascxml_extensions.ros_entries import RosActionThread, RosDeclaration
from as2fm.scxml_converter.scxml_entries import GenericScxmlRoot


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
        return RosDeclaration.__subclasses__()

    @classmethod
    def get_thread_classes(cls) -> List[Type[AscxmlThread]]:
        return [RosActionThread]

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

    def _check_valid_ros_declarations(self) -> bool:
        """Check if the ros declarations and instantiations are valid."""
        # Prepare the ROS declarations, to check no undefined ros instances exist
        ros_decl_container = self._generate_ros_declarations_helper()
        if ros_decl_container is None:
            return False
        # Check the ROS instantiations
        if not all(
            state.check_valid_ros_instantiations(ros_decl_container) for state in self._states
        ):
            return False
        if not all(
            isinstance(scxml_thread, RosActionThread)
            and scxml_thread.check_valid_ros_instantiations(ros_decl_container)
            for scxml_thread in self._ascxml_threads
        ):
            return False
        return True

    def _generate_ros_declarations_helper(self) -> Optional[ScxmlRosDeclarationsContainer]:
        """Generate a HelperRosDeclarations object from the existing ROS declarations."""
        ros_decl_container = ScxmlRosDeclarationsContainer(self._name)
        for ros_declaration in self._ros_declarations:
            if not (
                ros_declaration.check_validity() and ros_declaration.check_valid_instantiation()
            ):
                return None
            ros_decl_container.append_ros_declaration(ros_declaration)
        return ros_decl_container
