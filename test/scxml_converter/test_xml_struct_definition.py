from typing import Dict

from as2fm.scxml_converter.data_types.xml_struct_definition import XmlStructDefinition


def expand_struct_definitions(struct_definitions: Dict[str, XmlStructDefinition]):
    """Loop over all the definitions and expand their content."""
    for single_struct_name in struct_definitions:
        struct_definitions[single_struct_name].expand_members(struct_definitions)


def test_expand_members_basic():
    # Create mock dict of elements for struct with basic types and arrays thereof
    struct_definitions: Dict[str, XmlStructDefinition] = {
        "Int": XmlStructDefinition("Int", {"x": "int8"}),
        "Ints": XmlStructDefinition("Ints", {"x": "int8[]"}),
        "Ints42": XmlStructDefinition("Ints42", {"x": "int8[42]"}),
        "String": XmlStructDefinition("Int", {"x": "string"}),
        "Strings": XmlStructDefinition("Strings", {"x": "string[]"}),
        "Strings1": XmlStructDefinition("Strings1", {"x": "string[1]"}),
    }
    expand_struct_definitions(struct_definitions)

    assert struct_definitions["Int"].get_expanded_members()["x"] == "int8"
    assert struct_definitions["Ints"].get_expanded_members()["x"] == "int8[]"
    assert struct_definitions["Ints42"].get_expanded_members()["x"] == "int8[42]"
    assert struct_definitions["String"].get_expanded_members()["x"] == "string"
    assert struct_definitions["Strings"].get_expanded_members()["x"] == "string[]"
    assert struct_definitions["Strings1"].get_expanded_members()["x"] == "string[1]"


def test_expand_members_complex():
    # Create mock dict of elements for complex struct definitions
    struct_definitions: Dict[str, XmlStructDefinition] = {
        "PolygonsArray": XmlStructDefinition("PolygonsArray", {"polygons": "Polygon[]"}),
        "Polygon": XmlStructDefinition("Polygon", {"points": "Point2D[]"}),
        "Point2D": XmlStructDefinition("Point2D", {"x": "float32", "y": "float32"}),
        "Hexagon": XmlStructDefinition("Hexagon", {"points": "Point2D[6]"}),
    }
    expand_struct_definitions(struct_definitions)

    # Check expansion of PolygonsArray
    assert (
        struct_definitions["PolygonsArray"].get_expanded_members()["polygons.points.x"]
        == "float32[][]"
    )
    assert (
        struct_definitions["PolygonsArray"].get_expanded_members()["polygons.points.y"]
        == "float32[][]"
    )
    # Check expansion of Hexagon
    assert struct_definitions["Hexagon"].get_expanded_members()["points.x"] == "float32[6]"
    assert struct_definitions["Hexagon"].get_expanded_members()["points.y"] == "float32[6]"


def test_instance_evaluation():
    # Create mock dict of elements for struct definitions
    struct_definitions: Dict[str, XmlStructDefinition] = {
        "PolygonsArray": XmlStructDefinition("PolygonsArray", {"polygons": "Polygon[]"}),
        "Polygon": XmlStructDefinition("Polygon", {"points": "Point2D[]", "frame": "string"}),
        "Point2D": XmlStructDefinition("Point2D", {"x": "float32", "y": "float32"}),
    }
    expand_struct_definitions(struct_definitions)
    js_expression = """{
        'polygons': [
            {
                'points':
                    [
                        {'x': 1, 'y': 2},
                        {'x': 3, 'y': 4}
                    ],
                'frame': 'map',
            },
            {
                'points':
                    [
                        {'x': -1.5, 'y': 3},
                        {'x': -2.0, 'y': 5}
                    ],
                'frame': 'world',
            },
            {
                'points': [],
                'frame': '',
            },
        ]}"""
    poly_instance = struct_definitions["PolygonsArray"].get_instance_from_expression(js_expression)
    assert len(poly_instance) == 3
    assert poly_instance["polygons.points.x"] == [[1, 3], [-1.5, -2.0], []]
    assert poly_instance["polygons.points.y"] == [[2, 4], [3, 5], []]
    assert poly_instance["polygons.frame"] == ["'map'", "'world'", "''"]


def test_empty_instance_evaluation():
    # Create mock dict of elements for struct definitions
    struct_definitions: Dict[str, XmlStructDefinition] = {
        "PolygonsArray": XmlStructDefinition("PolygonsArray", {"polygons": "Polygon[]"}),
        "Polygon": XmlStructDefinition("Polygon", {"points": "Point2D[]"}),
        "Point2D": XmlStructDefinition("Point2D", {"x": "float32", "y": "float32"}),
    }
    expand_struct_definitions(struct_definitions)
    js_expression = """{
        'polygons': []}"""
    poly_instance = struct_definitions["PolygonsArray"].get_instance_from_expression(js_expression)
    assert len(poly_instance) == 2
    assert poly_instance["polygons.points.x"] == []
    assert poly_instance["polygons.points.y"] == []
