# Get the resolved types from the forward references in ScxmlExecutableEntry
_ResolvedScxmlExecutableEntry = \
    tuple(entry._evaluate(globals(), locals(), frozenset())
          for entry in get_args(ScxmlExecutableEntry))


def valid_execution_body(execution_body: ScxmlExecutionBody) -> bool:
    """
    Check if an execution body is valid.

    :param execution_body: The execution body to check
    :return: True if the execution body is valid, False otherwise
    """
    valid = isinstance(execution_body, list)
    if not valid:
        print("Error: SCXML execution body: invalid type found: expected a list.")
    for entry in execution_body:
        if not isinstance(entry, _ResolvedScxmlExecutableEntry):
            valid = False
            print(f"Error: SCXML execution body: entry type {type(entry)} not in valid set "
                  f" {_ResolvedScxmlExecutableEntry}.")
            break
        if not entry.check_validity():
            valid = False
            print("Error: SCXML execution body: invalid entry content found.")
            break
    return valid


def execution_body_from_xml(xml_tree: ET.ElementTree) -> ScxmlExecutionBody:
    """
    Create an execution body from an XML tree.

    :param xml_tree: The XML tree to create the execution body from
    :return: The execution body
    """
    raise NotImplementedError("Not implemented yet.")
