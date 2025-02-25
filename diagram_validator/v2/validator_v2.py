import re
import time
import warnings
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from bs4 import MarkupResemblesLocatorWarning

from diagram_validator.v2.validator_lib_v2 import decompress_data_if_required, save_decompressed_file, \
    extract_production_allowed_names_from_json_file, save_validation_errors_to_file, generate_post_validation_xml
from library.tools_validation import get_allowed_names

xml_file_path = r"examples/Gothic/produkcje_diagram_Gothic.drawio"
decompressed_xml_file_path = r"diagram_validator/v2/diagram_data/decompressed_diagram.xml"

generic_production_json_file_path = r"json_validation/allowed_names/produkcje_generyczne.json"
detailed_production_json_file_path = r"examples/Gothic/produkcje_Gothic.json"

allowedList = get_allowed_names()
allowed_locations = allowedList.get("Locations")
allowed_characters = allowedList.get("Characters")
allowed_items = allowedList.get("Items")
allowed_generic_production_names = extract_production_allowed_names_from_json_file(generic_production_json_file_path)
allowed_detailed_production_names = extract_production_allowed_names_from_json_file(detailed_production_json_file_path)

generic_productions = []
detailed_productions = []
automatic_productions = []
comments = []
final_productions = []
unknown_productions = []

generic_productions_info = {
    "name": "generic productions",
    "data": generic_productions,
    "valid_colors": {"fillColor=#ffffff;", ""}
}

detailed_productions_info = {
    "name": "detailed productions",
    "data": detailed_productions,
    "valid_colors": {"fillColor=#ffe6cc;"}
}

automatic_productions_info = {
    "name": "automatic productions",
    "data": automatic_productions,
    "valid_colors": {}
}

comments_info = {
    "name": "comments",
    "data": comments,
    "valid_colors": {"fillColor=#e1d5e7"}
}

final_productions_info = {
    "name": "final productions",
    "data": final_productions,
    "valid_colors": {"fillColor=#f5f5f5", "fillColor=#fff2cc", "fillColor=#e1d5e7", "fillColor=#000000"}
}

all_productions_info = [
    generic_productions_info,
    detailed_productions_info,
    automatic_productions_info,
    comments_info,
    final_productions_info
]

validation_errors = []


def clean_html(text):
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)
        soup = BeautifulSoup(text, "html.parser")
    return soup.get_text().strip()

def add_error(production_id, production_type, error_message, error_type, details=None):
    validation_errors.append({
        "id": production_id,
        "type": production_type,
        "error": error_message,
        "details": details,
        "error_type": error_type
    })

def get_production_types():
    tree = ET.parse(decompressed_xml_file_path)
    root = tree.getroot()

    # get all <mxCell>
    cells = root.findall(".//mxCell")

    # TODO: sprawdzanie nazw z plików

    for cell in cells:
        value = cell.get("value", "")
        value = clean_html(value)
        style = cell.get("style", "")

        # if production value contains "/"
        if "/" in value:

            # if allowed_generic_production_names is not None and empty and allowed_generic_production_names contains production value
            if not "dashed=1" in style and allowed_generic_production_names and any(element in value for element in allowed_generic_production_names) and "(" in value and ")" in value:
                generic_productions.append({
                    "id": cell.get("id"),
                    "value": value,
                    "style": cell.get("style"),
                    "cleaned_value": clean_html(value)
                })
                continue

            # if allowed_detailed_production_names is not None and empty and allowed_detailed_production_names contains production value
            elif not "dashed=1" in style and allowed_detailed_production_names and any(element in value for element in allowed_detailed_production_names) and "(" in value and ")" in value:
                detailed_productions.append({
                    "id": cell.get("id"),
                    "value": value,
                    "style": cell.get("style"),
                    "cleaned_value": clean_html(value)
                })
                continue
        if "dashed=1" in style and "(" in value and ")" in value: # automatic
            automatic_productions.append({
                "id": cell.get("id"),
                "value": value,
                "style": cell.get("style"),
                "cleaned_value": clean_html(value)
            })
        elif "/" in value and "(" in value and ")" in value and "dashed=1" not in style: # generic
            generic_productions.append({
                "id": cell.get("id"),
                "value": value,
                "style": cell.get("style"),
                "cleaned_value": clean_html(value)
            })
        elif "/" in value and "(" not in value and ")" not in value and value and "rounded=0" in style: # detailed
            detailed_productions.append({
                "id": cell.get("id"),
                "value": value,
                "style": cell.get("style"),
                "cleaned_value": clean_html(value)
            })
        elif value and "rounded=0" in style and "/" not in value and not "ellipse;" in style:
            comments.append({
                "id": cell.get("id"),
                "value": value,
                "style": cell.get("style"),
                "cleaned_value": clean_html(value)
            })
        elif "ellipse;" in style:
            final_productions.append({
                "id": cell.get("id"),
                "value": value,
                "style": cell.get("style"),
                "cleaned_value": clean_html(value)
            })
        elif value:
            unknown_productions.append({
                "id": cell.get("id"),
                "value": value,
                "style": cell.get("style"),
                "cleaned_value": clean_html(value)
            })

    print("\nGeneric productions:")
    for g in generic_productions:
        print(f"ID: {g['id']}, Value: {g['cleaned_value']}")

    print("\nAutomatic productions:")
    for a in automatic_productions:
        print(f"ID: {a['id']}, Value: {a['cleaned_value']}")

    print("\nDetailed productions:")
    for s in detailed_productions:
        print(f"ID: {s['id']}, Value: {s['cleaned_value']}")

    print("\nComments:")
    for c in comments:
        print(f"ID: {c['id']}, Value: {c['cleaned_value']}")

    print("\nFinal productions:")
    for fp in final_productions:
        print(f"ID: {fp['id']}, Value: {fp['cleaned_value']}")

    print("\nUnknown productions:")
    for up in unknown_productions:
        print(f"ID: {up['id']}, Value: {up['cleaned_value']}")


def extract_arguments_from_generic_production(cleaned_value):
    match = re.search(r"\(([^)]+)\)", cleaned_value)
    if match:
        arguments = match.group(1)
        return [arg.strip() for arg in arguments.split(",")]
    return []


def get_generic_productions_arguments():
    production_data = []
    for generic_production in generic_productions:
        production_id = generic_production.get("id")
        cleaned_value = generic_production.get("cleaned_value", "")
        arguments = extract_arguments_from_generic_production(cleaned_value)
        production_data.append({
            "id": production_id,
            "arguments": arguments
        })
    return production_data


def validate_arguments(arguments, production_id):
    for arg in arguments:
        if arg in allowed_characters:
            print(f"{arg} is allowed character.")
        elif arg in allowed_items:
            print(f"{arg} is allowed item.")
        elif arg in allowed_locations:
            print(f"{arg} is allowed location.")
        else:
            message = f"Unknown argument: {arg}"
            print(message)
            add_error(
                production_id,
                "generic productions",
                message,
                "ARGUMENT_NAME_VALIDATION",
                "Argument validation error. The name does not appear in any of the lists: Characters/Items/Locations"
            )


def validate_generic_production_arguments():
    if not allowedList:
        print("Allowed list is null or empty, argument validation skipped...")
    else:
        generic_production_data = get_generic_productions_arguments()
        print("\n validate arguments:")
        for data in generic_production_data:
            validate_arguments(data.get("arguments"), data.get("id"))


def extract_before_semicolon(text):
    if ";" in text:
        return text.split(";")[0].strip()
    return text


# def validate_generic_production_name(cleaned_value):
#     return extract_before_semicolon(cleaned_value) in allowed_generic_production_names

def validate_production_name(cleaned_value, allowed_production_names_list):
    return extract_before_semicolon(cleaned_value).strip() in {name.strip() for name in allowed_production_names_list}


# def validate_generic_production_names():
#     if not allowed_generic_production_names:
#         print("Missing json file, skipping name validation!")
#
#     else:
#         productions_with_invalid_names = []
#         for generic_production in generic_productions:
#             production_id = generic_production.get("id")
#             cleaned_value = generic_production.get("cleaned_value", "")
#             is_allowed_name = validate_generic_production_name(cleaned_value)
#             if not is_allowed_name:
#                 productions_with_invalid_names.append({
#                     "id": production_id,
#                     "name": extract_before_semicolon(cleaned_value)
#                 })
#         print("\n validate generic production names:")
#
#         if len(productions_with_invalid_names) > 0:
#             for p in productions_with_invalid_names:
#                 print(f"Generic production with invalid name: {p}")
#         else:
#             print("All generic production names are valid!")


def validate_production_names(production_type, allowed_production_names_list, productions_list):
    if not allowed_production_names_list:
        print("Missing json file, skipping name validation!")

    else:
        productions_with_invalid_names = []
        for production in productions_list:
            production_id = production.get("id")
            cleaned_value = production.get("cleaned_value", "")
            is_allowed_name = validate_production_name(cleaned_value, allowed_production_names_list)
            if not is_allowed_name:
                productions_with_invalid_names.append({
                    "id": production_id,
                    "name": extract_before_semicolon(cleaned_value)
                })
                add_error(
                    production_id,
                    production_type,
                    "Invalid production name (name not found in JSON file)",
                    "PRODUCTION_NAME_VALIDATION",
                    "Name validation error. The name does not appear in json file!"
                )

        if production_type == "generic_productions":
            print("\n validate generic production names:")
        elif production_type == "detailed_productions":
            print("\n validate detailed production names:")

        if len(productions_with_invalid_names) > 0:
            for p in productions_with_invalid_names:
                print(f"Generic production with invalid name: {p}")
        else:
            print("All generic production names are valid!")


def validate_production_colors():
    """
    Validates the colors of productions based on the `valid_colors` field in their corresponding production info.

    The `valid_colors` field in each production info object specifies acceptable `fillColor` values. The validation
    works as follows:
        - If `valid_colors` is empty (`{}` or `set()`), the absence of a `fillColor` attribute in the style is valid.
          Any `fillColor` present will be treated as invalid.
        - If `""` (an empty string) is in `valid_colors`, the `fillColor` attribute is optional in the style.
          - If `fillColor` is present, it must match one of the other colors in `valid_colors`.
          - If `fillColor` is absent, the style is valid.
        - If `""` is not in `valid_colors`, the presence of a valid `fillColor` is mandatory. The `fillColor` must match
          one of the values in `valid_colors`.

    For any invalid production, the method reports:
        - The production's ID.
        - The current `fillColor` in the style, or "No fillColor" if absent.
        - The expected `fillColor` values.

    Example:
        If `valid_colors` = {"fillColor=#ffffff;", ""}:
            - A production with `fillColor=#ffffff;` is valid.
            - A production with no `fillColor` is valid.
            - A production with `fillColor=#ff0000;` is invalid.

    Prints the results for each production type:
        - The ID of invalid productions.
        - The current color or its absence.
        - The expected valid colors.

    Args:
        None

    Returns:
        None
    """
    for production_info in all_productions_info:
        invalid = []
        valid_colors = production_info.get("valid_colors", set())
        production_name = production_info.get("name")

        for production in production_info.get("data"):
            production_id = production.get("id")
            style = production.get("style", "")
            fill_color_match = re.search(r"fillColor=#[a-fA-F0-9]{6};", style)  # Matches `fillColor` if present

            if not valid_colors:
                # If valid_colors is empty, the absence of fillColor is valid; any fillColor is invalid
                if fill_color_match:
                    current_color = fill_color_match.group()
                    invalid.append({
                        "id": production_id,
                        "current_color": current_color,
                        "expected_colors": "No fillColor"
                    })
                    add_error(
                        production_id,
                        production_name,
                        f"Production color is {current_color}. Should be: None",
                        "PRODUCTION_COLOR_VALIDATION"
                    )

            elif "" in valid_colors:
                # If "" is in valid_colors, absence of fillColor is acceptable
                if not fill_color_match:
                    continue  # No fillColor, but it's valid due to ""
                elif fill_color_match.group() not in valid_colors:
                    # If fillColor is present but not in valid_colors
                    current_color = fill_color_match.group()
                    expected_colors = valid_colors - {""}
                    invalid.append({
                        "id": production.get("id"),
                        "current_color": current_color,
                        "expected_colors": expected_colors
                    })
                    add_error(
                        production_id,
                        production_name,
                        f"Invalid production color found! Current color: {current_color}, expected colors: {expected_colors}.",
                        "PRODUCTION_COLOR_VALIDATION"
                    )
            else:
                # Standard validation: fillColor must be present and valid
                current_color = fill_color_match.group() if fill_color_match else "No fillColor",
                expected_colors = valid_colors
                if not any(color in style for color in valid_colors):
                    invalid.append({
                        "id": production.get("id"),
                        "current_color": current_color,
                        "expected_colors": expected_colors
                    })
                    add_error(
                        production_id,
                        production_name,
                        f"Invalid production color found! Current color: {current_color}, expected colors: {expected_colors}.",
                        "PRODUCTION_COLOR_VALIDATION"
                    )

        # Display validation results
        print(f"\n validate {production_name} colors:")
        if invalid:
            for prod in invalid:
                print(f"ID: {prod['id']}, Current color: {prod['current_color']}, Expected: {prod['expected_colors']}")
        else:
            print(f"All {production_name} colors are valid!")


def is_valid_generic_production_name(value):
    """
    Validates if a generic production contains parentheses with at least two comma-separated elements.

    Args:
        value (str): The production value to validate.

    Returns:
        bool: True if valid, False otherwise.
    """

    # Extract the content inside parentheses
    match = re.search(r'\(([^)]+)\)', value)
    if not match:
        return False

    # Split the content by commas
    content = match.group(1).strip()
    items = [item.strip() for item in content.split(",")]

    # Check if there are at least two elements
    result = len(items) >= 2
    return result


def is_valid_detailed_production_name(value):
    """
    Validates if a detailed production does not contain parentheses.

    Args:
        value (str): The production value to validate.

    Returns:
        bool: True if valid, False otherwise.
    """

    # Check for parentheses
    result = "(" not in value and ")" not in value
    return result


def is_comment_name_valid(name):
    """
    Validates if the name matches the comment pattern:
    "(Fakt z innej misji mogący wpłynąć na akcje bieżącej, nr requestu)"
    """
    pattern = r"^\([^()]+,\s*Q\d+\)$"
    return re.match(pattern, name.strip()) is not None


def validate_production_name_patterns(productions_info):
    """
    Validates production names based on their type and structure.

    Args:
        productions_info (list): List of production information, where each contains data for a production.

    Prints:
        A report of invalid production names and their expected patterns.
    """
    invalid_productions = []
    #
    # for production_info in productions_info:
    #     production_type = production_info.get("name", "")
    #     production_data = production_info.get("data", [])
    #
    #     for production in production_data:
    #         production_id = production.get("id")
    #         cleaned_value = production.get("cleaned_value", "").strip()
    #
    #         if not is_valid_generic_production_name(cleaned_value) \
    #                 and not is_valid_detailed_production_name(cleaned_value) \
    #                 and not is_comment_name_valid(cleaned_value):
    #             invalid_productions.append({
    #                 "id": production_id,
    #                 "value": cleaned_value,
    #                 "type": production_type
    #             })
    #             add_error(
    #                 production_id,
    #                 production_type,
    #                 "The production name does not match any pattern!",
    #                 "PRODUCTION_NAME_PATTERN_VALIDATION",
    #                 f"Current production name: {cleaned_value}"
    #             )

    for unknown_production in unknown_productions:
        production_id = unknown_production.get("id")
        production_value = unknown_production.get("value")
        production_type = "unknown_production"

        invalid_productions.append({
            "id": production_id,
            "value": production_value,
            "type": production_type
        })

        add_error(
            production_id,
            production_type,
            "The production name does not match any pattern!",
            "PRODUCTION_NAME_PATTERN_VALIDATION",
            f"Current production name: {production_value}"
        )

    if invalid_productions:
        print("\nInvalid production names:")
        for invalid in invalid_productions:
            print(f"ID: {invalid['id']}, Value: {invalid['value']}, Type: {invalid['type']}")
    else:
        print("\nAll production names are valid!")


def validate_final_productions():
    # 1. Validate whether final productions are correct (no outgoing edges, and have at least one incoming edge)
    # 2. Validate final production values
    # 3. Validate whether there are no productions != final that not contain outgoing edges

    tree = ET.parse(decompressed_xml_file_path)
    root = tree.getroot()

    edges_incoming = {}
    edges_outgoing = {}

    # Get diagram's edges
    for edge in root.findall(".//mxCell[@edge='1']"):
        source = edge.get("source")
        target = edge.get("target")

        if source:
            edges_outgoing.setdefault(source, []).append(edge.get("id"))
        if target:
            edges_incoming.setdefault(target, []).append(edge.get("id"))

    invalid_final_productions = []
    invalid_non_final_productions = []

    for final_production in final_productions:
        production_id = final_production.get("id")
        production_type = final_production.get("name")
        style = final_production.get("style", "")
        cleaned_value = final_production.get("cleaned_value", ""). strip()

        # validate outgoing and incoming edges
        incoming_edges = edges_incoming.get(production_id, [])
        outgoing_edges = edges_outgoing.get(production_id, [])

        # 1. Validate final productions
        if outgoing_edges:
            invalid_final_productions.append({
                "id": production_id,
                "error": "Final production has outgoing edges!",
                "edges": outgoing_edges
            })
            add_error(
                production_id,
                production_type,
                f"Final production has outgoing edges!: {outgoing_edges}",
                "FINAL_PRODUCTION_VALIDATION"
            )
        if not incoming_edges:
            error_message = "Final production has no incoming edges!"
            invalid_final_productions.append({
                "id": production_id,
                "error": error_message
            })
            add_error(
                production_id,
                production_type,
                error_message,
                "FINAL_PRODUCTION_VALIDATION"
            )

        # 2. Validate final production values
        if "fillColor=#f5f5f5" in style or "fillColor=#fff2cc" in style or "fillColor=#000000" in style:
            # White, black and yellow requires empty value
            if cleaned_value:
                error_message = "Final production with invalid value! Value should be empty!"
                invalid_final_productions.append({
                    "id": production_id,
                    "error": error_message,
                    "value": cleaned_value,
                    "expected": "empty"
                })
                add_error(
                    production_id,
                    production_type,
                    error_message,
                    "FINAL_PRODUCTION_VALIDATION"
                )
            elif "fillColor=#e1d5e7" in style:
                # purple requires numeric value
                if not cleaned_value.is_digit():
                    invalid_final_productions.append({
                        "id": production_id,
                        "error": "Final production with invalid value",
                        "value": cleaned_value,
                        "expected": "numeric"
                    })
                    add_error(
                        production_id,
                        production_type,
                        f"Final production with invalid value! Current value: {cleaned_value}, but should be numeric!",
                        "FINAL_PRODUCTION_VALIDATION"
                    )
    # 3. Non-final productions without outgoing edges
    for production_info in all_productions_info:
        if production_info["name"] == "final productions":
            continue
        for production in production_info["data"]:
            production_id = production.get("id")
            production_type = production.get("name")
            outgoing_edges = edges_outgoing.get(production_id, [])
            if not outgoing_edges:
                error_message = "Non-final production has no outgoing edges!"
                invalid_non_final_productions.append({
                    "id": production_id,
                    "error": error_message
                })
                add_error(
                    production_id,
                    production_type,
                    error_message,
                    "FINAL_PRODUCTION_VALIDATION"
                )

    print("\nInvalid final productions:")
    if invalid_final_productions:
        for invalid in invalid_final_productions:
            print(f"ID: {invalid['id']}, Error: {invalid['error']}, Details: {invalid.get('value', '')}")
    else:
        print("All final productions are valid!")

    print("\nInvalid non-final productions:")
    if invalid_non_final_productions:
        for invalid in invalid_non_final_productions:
            print(f"ID: {invalid['id']}, Error: {invalid['error']}")
    else:
        print("All non-final productions have outgoing edges!")

# Method to validate generic or automatic production values
def validate_production_by_production_type(production_list, production_type):
    for production in production_list:
        value = production.get("value")
        production_id = production.get("id")

        if value and ";" not in value:
            add_error(
                production_id,
                production_type,
                "Missing semicolon!",
                "PRODUCTION_VALUE_VALIDATION"
            )

        if value and not "(" in value or not ")" in value:
            add_error(
                production_id,
                production_type,
                "Missing parenthesis!",
                "PRODUCTION_VALUE_VALIDATION"
            )

        if value and "(" in value and ")" in value:
            match = re.search(r"\((.*?)\)", value)
            if match:
                inside_parentheses = match.group(1)
                arguments = [arg.strip() for arg in inside_parentheses.split(",")]
                if len(arguments) < 2 or not all(arguments):
                    add_error(
                        production_id,
                        production_type,
                        "Invalid number of arguments between parentheses!",
                        "PRODUCTION_VALUE_VALIDATION"
                    )

        validate_slash_in_production_value(value, production_id, production_type)


def validate_slash_in_production_value(value, production_id, production_type):
    if value and not "/" in value:
        add_error(
            production_id,
            production_type,
            "Missing slash!",
            "PRODUCTION_VALUE_VALIDATION"
        )

    if value and "/" in value and not " / " in value:
        add_error(
            production_id,
            production_type,
            "Space next to '/' required!",
            "PRODUCTION_VALUE_VALIDATION"
        )


def validate_generic_and_automatic_production_values():
    validate_production_by_production_type(generic_productions, "generic_production")
    validate_production_by_production_type(automatic_productions, "automatic_production")


def validate_detailed_production_values():
    for production in detailed_productions:
        value = production.get("value")
        production_id = production.get("id")

        validate_slash_in_production_value(value, production_id, "detailed_production")


def validate_production_values():
    validate_generic_and_automatic_production_values()
    validate_detailed_production_values()


with open(xml_file_path, 'rb') as xml_file:
    xml_content = xml_file.read()

if __name__ == "__main__":
    decompressed_xml = decompress_data_if_required(xml_content)
    save_decompressed_file(decompressed_xml, decompressed_xml_file_path)
    get_production_types()
    validate_generic_production_arguments()
    # validate_generic_production_names()
    validate_production_names("generic_productions", allowed_generic_production_names, generic_productions)
    validate_production_names("detailed_productions", allowed_detailed_production_names, detailed_productions)

    validate_production_colors()
    validate_production_name_patterns(all_productions_info)
    validate_production_values()
    validate_final_productions()

    timestamp = str(time.time())
    save_validation_errors_to_file(validation_errors, xml_file_path, timestamp)
    generate_post_validation_xml(decompressed_xml_file_path, validation_errors, xml_file_path, timestamp)



