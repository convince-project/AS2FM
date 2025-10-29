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

"""Declaration of the ROS Field SCXML tag extension."""

from typing import List

from as2fm.as2fm_common.logging import get_error_msg
from as2fm.scxml_converter.ascxml_extensions import AscxmlDeclaration
from as2fm.scxml_converter.scxml_entries import ScxmlBase, ScxmlParam
from as2fm.scxml_converter.scxml_entries.type_utils import ScxmlStructDeclarationsContainer
from as2fm.scxml_converter.scxml_entries.utils import (
    ROS_FIELD_PREFIX,
    get_plain_expression,
)


class RosField(ScxmlParam):
    """Field of a ROS msg published in a topic."""

    @staticmethod
    def get_tag_name() -> str:
        return "field"

    def as_plain_scxml(
        self,
        struct_declarations: ScxmlStructDeclarationsContainer,
        ascxml_declarations: List[AscxmlDeclaration],
        **kwargs,
    ) -> List[ScxmlBase]:
        # In order to distinguish the message body from additional entries, add a prefix to the name
        assert self._cb_type is not None, get_error_msg(
            self.get_xml_origin(), "No callback type set for ROS field."
        )
        plain_field_name = ROS_FIELD_PREFIX + self._name
        assert isinstance(self._expr, str), get_error_msg(
            self.xml_origin(),
            "Expressions with conf. entries should be already evaluated at this stage.",
        )
        plain_scxml_param = ScxmlParam(
            plain_field_name,
            expr=get_plain_expression(self._expr, self._cb_type, struct_declarations),
        )
        plain_scxml_param._set_plain_name_and_expression(struct_declarations)
        return [plain_scxml_param]
