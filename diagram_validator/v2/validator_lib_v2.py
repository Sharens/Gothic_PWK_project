import base64
import json
import os
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path
from urllib.parse import unquote


def is_xml_file_compressed(data):
    """
    Detect if the file is compressed.
    """

    content = data.decode('utf-8')
    if "<root>" in content:
        print("XML file is decompressed")
        return False

    print("XML file is compressed")
    return True


def extract_compressed_data_from_xml(data):
    """
    Extract and return the compressed content from the <diagram> tag.
    """
    root = ET.fromstring(data)
    diagram_element = root.find(".//diagram")
    if diagram_element is None:
        raise ValueError("No <diagram> element found in the XML.")
    return diagram_element.text


def decode_url_encoded_string(encoded_string):
    """
    Decodes a URL-encoded string into its original format.

    Args:
        encoded_string (str): The URL-encoded string.

    Returns:
        str: The decoded string.
    """
    return unquote(encoded_string)


def decompress_diagram_data(data):
    """
    Decode Base64 and decompress Deflate-encoded data.
    """
    encoded_data = extract_compressed_data_from_xml(data)
    compressed_data = base64.b64decode(encoded_data)
    decompressed_data = zlib.decompress(compressed_data, -15).decode('utf-8')  # -15 skips the zlib header check
    decoded_data = decode_url_encoded_string(decompressed_data)

    return decoded_data


def decompress_data_if_required(data):
    """
    Decompress data if its compressed.
    """
    if is_xml_file_compressed(data):
        return decompress_diagram_data(data)

    return data.decode('utf-8') if isinstance(data, bytes) else data


def save_decompressed_file(decompressed_xml_content, decompressed_xml_file_path):
    with open(decompressed_xml_file_path, 'w', encoding='utf-8') as decompressed_file:
        decompressed_file.write(decompressed_xml_content)
        print(f"Decompressed file saved to: {decompressed_xml_file_path}")


def extract_production_allowed_names_from_json_file(file_path):
    """
    Extracts unique titles from a JSON file containing generic productions.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        list: A list of unique titles.
    """
    unique_titles = set()

    try:
        with open(file_path, "r", encoding="utf-8") as file:
            productions = json.load(file)

            # Extract titles and add them to the set
            for production in productions:
                if "Title" in production:
                    unique_titles.add(production["Title"].strip())

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error reading the file: {e}")

    return sorted(unique_titles)


def save_validation_errors_to_file(validation_errors, xml_file_path, timestamp):
    """
    Saves the collected errors to a file in JSON format.

    Args:
        validation_errors (list): List of errors collected during validation.
        xml_file_path (str): The path of diagram file.
        timestamp: Current timestamp

    Returns:
        None
    """
    directory = "output"
    filename = Path(xml_file_path).stem
    file_path = directory + "/" + filename + "_output_" + timestamp + ".json"
    if not os.path.exists(directory):
        os.makedirs(directory)

    # Save the errors to the file
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(validation_errors, file, indent=4, ensure_ascii=False)


def generate_post_validation_xml(input_file, error_productions, xml_file_path, timestamp):
    """
    Modifies an XML file by marking productions with errors in red text and saves the result to a new file.

    Args:
        input_file (str): Path to the original XML file.
        error_productions (list): List of IDs for productions with errors.
        xml_file_path (str): Path to the XML diagram file.
        timestamp: Current timestamp

    Returns:
        None
    """
    # Parse the existing XML file
    tree = ET.parse(input_file)
    root = tree.getroot()

    for mxCell in root.findall(".//mxCell"):
        cell_id = mxCell.get("id")

        for error in error_productions:
            if error["id"] == cell_id:
                style = mxCell.get("style", "")
                value = mxCell.get("value", "")
                new_style = style + ";fontColor=#FF0000;"
                new_value = value + " --> " + error["error"]
                mxCell.set("style", new_style)
                mxCell.set("value", new_value)

    directory = "output"
    filename = Path(xml_file_path).stem
    file_path = directory + "/" + filename + "_output_" + timestamp + ".xml"
    # Write the modified XML to the output file
    tree.write(file_path, encoding="utf-8", xml_declaration=True)