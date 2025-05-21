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

from dataclasses import dataclass
from typing import List, MutableSequence, Optional, Type, Union

from as2fm.as2fm_common.common import get_array_type_and_sizes

ARRAY_BASE_TYPES = (int, float, None)


@dataclass()
class ArrayInfo:
    """
    A class to represent metadata about an array, including its type, dimensions,
    and maximum sizes for each dimension.
    Attributes:
        array_type (type, str): The data type of the array elements.
        array_dimensions (int): The number of dimensions of the array.
        array_max_sizes (List[int]): A list specifying the maximum size for each
            dimension of the array.
        is_base_type (bool): Whether the array_type is assumed to be a float or int, i.e. not a
            custom object.
    """

    array_type: Union[Type[Union[int, float]], str, None]
    array_dimensions: int
    array_max_sizes: List[Optional[int]]
    is_base_type: bool = True

    def __post_init__(self):
        if self.is_base_type and self.array_type not in ARRAY_BASE_TYPES:
            raise ValueError(f"array_type {self.array_type} != (int, float, None)")
        if not (isinstance(self.array_dimensions, int) and self.array_dimensions > 0):
            raise ValueError(f"array_dimension is {self.array_dimensions}: it should be at least 1")
        if not all(
            d_size is None or (isinstance(d_size, int) and d_size > 0)
            for d_size in self.array_max_sizes
        ):
            raise ValueError(f"Invalid 'array_max_sizes': {self.array_max_sizes}")

    def substitute_unbounded_dims(self, max_size: int):
        """
        Substitute the 'None' entries in the array_max_sizes with the provided max_size.
        """
        self.array_max_sizes = [
            max_size if curr_size is None else curr_size for curr_size in self.array_max_sizes
        ]


def array_value_to_type_info(data_value: MutableSequence) -> ArrayInfo:
    """Small helper function to generate the array info from a given value instance."""
    array_type, array_sizes = get_array_type_and_sizes(data_value)
    n_dims = len(array_sizes)
    return ArrayInfo(array_type, n_dims, [None] * n_dims)
