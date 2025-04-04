from typing import Dict

from as2fm.scxml_converter.xml_data_types.xml_struct_definition import XmlStructDefinition


def test_expand_members():
    # Create mock XML elements for struct definitions
    struct_definitions: Dict[str, XmlStructDefinition] = {
        "PolygonsArray": XmlStructDefinition("PolygonsArray", {"polygons": "Polygon[]"}),
        "Polygon": XmlStructDefinition("Polygon", {"points": "Point2D[]"}),
        "Point2D": XmlStructDefinition("Point2D", {"x": "float32", "y": "float32"}),
    }

    for single_struct_name in struct_definitions:
        struct_definitions[single_struct_name].expand_members(struct_definitions)
    print(struct_definitions["PolygonsArray"]._expanded_members)
