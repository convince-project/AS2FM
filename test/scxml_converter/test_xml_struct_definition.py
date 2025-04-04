from typing import Dict

from as2fm.scxml_converter.xml_data_types.xml_struct_definition import XmlStructDefinition


def expand_struct_definitions(struct_definitions: Dict[str, XmlStructDefinition]):
    """Loop over all the definitions and expand their content."""
    for single_struct_name in struct_definitions:
        struct_definitions[single_struct_name].expand_members(struct_definitions)


def test_expand_members():
    # Create mock dict of elements for struct definitions
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
        "Polygon": XmlStructDefinition("Polygon", {"points": "Point2D[]"}),
        "Point2D": XmlStructDefinition("Point2D", {"x": "float32", "y": "float32"}),
    }
    expand_struct_definitions(struct_definitions)
    js_expression = """{
        'polygons': [
            {'points': [
                {'x': 1, 'y': 2},
                {'x': 3, 'y': 4}
            ]},
            {'points': [
                {'x': -1.5, 'y': 3},
                {'x': -2.0, 'y': 5}
            ]},
        ]}"""
    struct_definitions["PolygonsArray"].get_instance_from_expression(js_expression)
