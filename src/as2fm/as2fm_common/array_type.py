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
from typing import List, MutableSequence, Optional, Tuple, Type, Union, get_args

from as2fm.as2fm_common.common import ValidPlainScxmlTypes

ARRAY_BASE_TYPES = (int, float, None)


@dataclass()
class ArrayInfo:
    """
    Representation of metadata about an array, including its type, dimensions, and maximum sizes
    for each dimension.

    :attribute array_type: The data type of the array elements.
    :attribute array_dimensions: The number of dimensions of the array.
    :attribute array_max_sizes: A list specifying the maximum size for each dimension of the array.
    :attribute is_base_type: Whether the array_type is assumed to be a float or int, i.e. not a
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

    def __eq__(self, other: "ArrayInfo"):
        return (
            self.array_dimensions == other.array_dimensions
            and self.array_max_sizes == other.array_max_sizes
            and self.array_type == other.array_type
            and self.is_base_type == other.is_base_type
        )

    def substitute_unbounded_dims(self, max_size: int):
        """
        Substitute the 'None' entries in the array_max_sizes with the provided max_size.
        """
        self.array_max_sizes = [
            max_size if curr_size is None else curr_size for curr_size in self.array_max_sizes
        ]


def array_value_to_type_info(data_value: MutableSequence) -> ArrayInfo:
    """Generate the `ArrayInfo` from a given instance."""
    array_type, array_sizes = get_array_type_and_sizes(data_value)
    n_dims = len(array_sizes)
    return ArrayInfo(array_type, n_dims, [None] * n_dims)


def is_valid_array(in_sequence: Union[MutableSequence, str]) -> bool:
    """
    Check that the array is composed of a list of (int, float, list).

    This does *not* check that all sub-lists have the same depth (e.g. [[1], [[1,2,3]]]).
    """
    assert isinstance(
        in_sequence, list
    ), f"Input values are expected to be lists, found '{in_sequence}' of type {type(in_sequence)}."
    if len(in_sequence) == 0:
        return True
    if isinstance(in_sequence[0], MutableSequence):
        return all(
            isinstance(seq_value, MutableSequence) and is_valid_array(seq_value)
            for seq_value in in_sequence
        )
    # base case: simple array of base types
    first_value_type = type(in_sequence[0])
    assert first_value_type in (
        int,
        float,
        str,
        dict,
    ), f"Unexpected list entry type: {first_value_type}."
    return all(isinstance(seq_value, first_value_type) for seq_value in in_sequence)


def get_array_type_and_sizes(
    in_sequence: Union[MutableSequence, str],
) -> Tuple[Optional[Type[Union[int, float]]], MutableSequence]:
    """
    Extract the type and size(s) of the provided multi-dimensional array.

    Exemplary output for 3-dimensional array `[ [], [ [1], [1, 2], [] ] ]` is:
    `tuple(int, [2, [0, 3], [[], [1, 2, 0]]]])`.
    The sizes contain one entry per dimension (here 3).
    """
    if not is_valid_array(in_sequence):
        raise ValueError(f"Invalid sub-array found: {in_sequence}")
    if isinstance(in_sequence, str):
        raise ValueError("This should not contain string expressions any more.")
    if len(in_sequence) == 0:
        return None, [0]
    if not isinstance(in_sequence[0], MutableSequence):
        # 1-D array -> type is int or float
        ret_type: Optional[Type[Union[int, float]]] = float
        if all(isinstance(seq_entry, int) for seq_entry in in_sequence):
            # if at least one entry is float, all will be float
            ret_type = int
        return ret_type, [len(in_sequence)]
    # Recursive part
    curr_type: Optional[Type[Union[int, float]]] = None
    base_size = len(in_sequence)  # first dimension
    child_sizes = []  # on this first dimension
    children_max_depth = 0  # keep track of how deep we go
    for seq_entry in in_sequence:
        single_type, single_sizes = get_array_type_and_sizes(seq_entry)
        child_depth = len(single_sizes)
        if curr_type is None:
            if single_type is not None and child_depth < children_max_depth:
                raise ValueError("Unbalanced list found.")
            # We do not know *yet* the max depth of the children.
            children_max_depth = max(children_max_depth, child_depth)
            curr_type = single_type
        else:
            # We have to make sure the max depth doesn't grow
            if single_type is None:
                if child_depth > children_max_depth:
                    raise ValueError("Unbalanced list found.")
            else:
                if child_depth != children_max_depth:
                    raise ValueError("Unbalanced list found.")
                if curr_type == int:
                    curr_type = single_type
        child_sizes.append(single_sizes)
    # At this point, we need to merge the sizes from the child_sizes to create the desired
    # output format. (List with one entry per dimension)
    max_depth = children_max_depth + 1
    processed_sizes: List[Union[int, List]] = []
    for level in range(max_depth):
        if level == 0:
            processed_sizes.append(base_size)
            continue
        processed_sizes.append([])
        for curr_size_entry in child_sizes:
            if len(curr_size_entry) < level:
                # there was an empty list at the previous depth level
                processed_sizes[level].append([])
            else:
                assert isinstance(
                    processed_sizes[level], list
                ), f"Unexpected a list of sizes at {level=}."
                processed_sizes[level].append(curr_size_entry[level - 1])
    return curr_type, processed_sizes


def get_padded_array(
    array_to_pad: List[Union[int, float, List]],
    size_per_level: List[int],
    array_type: Type[Union[int, float]],
) -> List[Union[int, float, List]]:
    """Given a N-Dimensional list, add padding for each level, depending on the provided sizes."""
    padding_size = size_per_level[0] - len(array_to_pad)
    if padding_size < 0:
        raise ValueError(
            f"Expected level's size '{size_per_level[0]}' is smaller than ",
            f"the current instance length '{len(array_to_pad)}'.",
        )
    if len(size_per_level) == 1:
        # We are at the lowest level -> only floats and integers allowed
        if any(isinstance(entry, list) for entry in array_to_pad):
            raise ValueError("The array to pad is deeper than expected.")
        array_to_pad.extend([array_type(0)] * padding_size)
    else:
        # There are lower levels -> Here we expect only empty lists
        if not all(isinstance(entry, list) for entry in array_to_pad):
            raise ValueError("Found non-array entries at intermediate depth.")
        array_to_pad.extend([[]] * padding_size)
        for idx in range(size_per_level[0]):
            array_to_pad[idx] = get_padded_array(array_to_pad[idx], size_per_level[1:], array_type)
    return array_to_pad


def is_array_type(field_type: Type[ValidPlainScxmlTypes]) -> bool:
    """Check if the field type is an array type."""
    return field_type is MutableSequence or isinstance(field_type, ArrayInfo)


def get_default_expression_for_type(field_type: Type[ValidPlainScxmlTypes]) -> ValidPlainScxmlTypes:
    """Generate a default expression for a field type."""
    # if isinstance(field_type, ArrayInfo):
    #     # TODO: We need to handle types properly.
    #     return []
    assert field_type in get_args(
        ValidPlainScxmlTypes
    ), f"Error: Unsupported SCXML data type {field_type}."
    if field_type is MutableSequence:
        return []
    if field_type is str:
        return ""
    else:
        return field_type()
