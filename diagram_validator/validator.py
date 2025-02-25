import sys
from collections import defaultdict

import os
from copy import deepcopy
import argparse

from config.config import path_root
from library.tools import get_quest_nr, find_file
from library.tools_validation import get_jsons_storygraph_validated, get_allowed_names
from validator_lib import *




# WGRYWANIE DANYCH ŹRÓDŁOWYCH

# wgrywanie produkcji i diagramu podanych w linii komend
parser = argparse.ArgumentParser()
parser.add_argument('--drawing', type=str, help="add --drawing path to drawing")
parser.add_argument('--detailed', type=str, help="add --detailed path to detailed prod json")
args = parser.parse_args()


# wgrywanie produkcji i diagramu ręcznie
dir_name = ''
json_path = f'{path_root}/{dir_name}'
jsons_OK, jsons_schema_OK, errors, warnings = get_jsons_storygraph_validated(json_path)

prod_det_names = ['quest00_DragonStory'] # nazwy plików bez rozszerzenia
prod_gen_names = ['produkcje_generyczne']
prod_aut_names = ['produkcje_automatyczne', 'produkcje_automatyczne_wygrywania']

prod_det_jsons = []
for y in [jsons_schema_OK[get_quest_nr(x, jsons_schema_OK)]['json'] for x in prod_det_names]:
    prod_det_jsons += y
prod_gen_jsons = []
for y in [deepcopy(jsons_schema_OK[get_quest_nr(x, jsons_schema_OK)]['json']) for x in prod_gen_names]:
    prod_gen_jsons += y
prod_aut_jsons = []
for y in [deepcopy(jsons_schema_OK[get_quest_nr(x, jsons_schema_OK)]['json']) for x in prod_aut_names]:
    prod_aut_jsons += y

diagram_path = find_file(json_path, f'{prod_det_names[0][0:12]}_diagram_{prod_det_names[0][13:]}.drawio')
if not diagram_path:
    diagram_path = json_path + f'{os.sep}DragonStory{os.sep}quest00_diagram_DragonStory.drawio'
# quest2023-02_diagram_Boat_Dream.drawio
# quest2023-07_diagram_Key_to_captain.drawio

# przypisywanie wartości parametrów z linii komend lub ręcznie
if args.detailed:
    allowed_detailed_productions = loadFromJson(args.detailed)
    # allowedGenericProductionList = json.load(open(f'..{os.sep}json_validation{os.sep}allowed_names{os.sep}produkcje_generyczne.json', encoding="utf8"))
else:
    allowed_detailed_productions = prod_det_jsons

allowed_generic_productions = prod_gen_jsons
allowed_automatic_productions = prod_aut_jsons

if args.drawing:
    pathToXml = args.drawing
else:
    pathToXml = diagram_path


# dozwolone nazwy obiektów

allowedList = get_allowed_names()
allowed_locations = allowedList.get("Locations")
allowed_characters = allowedList.get("Characters")
allowed_items = allowedList.get("Items")

"""
allowed_locations = json.load(open(f'..{os.sep}json_validation{os.sep}allowed_names{os.sep}locations.json', encoding="utf8"))
allowed_locations += json.load(open(f'..{os.sep}json_validation{os.sep}allowed_names{os.sep}locations_Wojtek.json', encoding="utf8"))
allowed_characters = json.load(open(f'..{os.sep}json_validation{os.sep}allowed_names{os.sep}characters.json', encoding="utf8"))
allowed_characters += json.load(open(f'..{os.sep}json_validation{os.sep}allowed_names{os.sep}characters_Wojtek.json', encoding="utf8"))
allowed_items = json.load(open(f'..{os.sep}json_validation{os.sep}allowed_names{os.sep}items.json', encoding="utf8"))
allowed_items += json.load(open(f'..{os.sep}json_validation{os.sep}allowed_names{os.sep}items_Wojtek.json', encoding="utf8"))

allowedCharactersList = allowed_characters
allowedItemsList = allowed_items
allowedLocationsList = allowed_locations
"""
drawing_file = open(pathToXml, encoding="utf-8").read()
res = validate_jb(drawing_file, allowed_characters, allowed_items, allowed_locations,
                  allowed_generic_productions, allowed_detailed_productions, allowed_automatic_productions)
printTestDict1(res)

"""
result = validate_drawing(drawingFile, allowedCharactersList, allowedItemsList, allowedLocationsList,
                     allowedGenericProductionList, allowedDetailedProductionList, allowedAutomaticProductionList)
printTestDict(result)
print(areThereErrorsInTestDict(result),"- there are errors")
"""
