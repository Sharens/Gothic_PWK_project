import xml.etree.ElementTree as ET
import re
from html.parser import HTMLParser
from collections import defaultdict
from functools import reduce
import json
import sys
from typing import List
import os
from urllib.parse import unquote
import base64
import zlib
from typing import Tuple, List
from diagram_validator.validator import allowedCharactersList, allowedItemsList, allowedLocationsList, \
    allowedGenericProductionList, allowedDetailedProductionList, allowedAutomaticProductionList


def decompress_diagram(diagram_file: str) -> str:
    """
    Decompresses given xml/drawio file.
    Stolen from Maria
    https://crashlaker.github.io/programming/2020/05/17/draw.io_decompress_xml_python.html
    :param diagram_file: file opened as a string
    :return: string with decompressed file
    """

    diagram_pattern = re.compile(r"<diagram.*?>([\s\S]*?)</diagram>", re.DOTALL)
    diagram_match = diagram_pattern.search(diagram_file)

    if diagram_match:
        compressed_data = diagram_match.group(1)
        decompress = zlib.decompressobj(-15)
        decompressed_data = decompress.decompress(base64.b64decode(compressed_data))
        
    """    
    diagram_part = re.search("<diagram.*>[\s\S]*?</diagram>", diagram_file)
    part_to_decode = re.sub("</diagram>", "", diagram_part[0])
    part_to_decode = re.sub("<diagram.*>", "", part_to_decode)
    decompress = zlib.decompressobj(-15)
    decompressed_data = decompress.decompress(base64.b64decode(part_to_decode))
    """
    decompressed_data += decompress.flush()
    decoded_diagram = unquote(decompressed_data.decode())
    return decoded_diagram


# https://stackoverflow.com/questions/44542853/how-to-collect-the-data-of-the-htmlparser-in-python-3
class MyHTMLParser(HTMLParser):
    def __init__(self):
        self.d = []
        super().__init__()


    def handle_data(self, data):
        #some hispanic white space https://stackoverflow.com/questions/10993612/how-to-remove-xa0-from-string-in-python
        data = data.replace('&amp;', '&')
        data = data.replace(u'\xa0', u' ')

        self.d.append(data)
        # self.d.append(data.replace(u'\xa0', u' '))
        return (data)

    def return_data(self):
        result = self.d

        self.d =[]

        return result

def loadFromJson(filename):

    file = open(filename, encoding="utf8")
    data = json.load(file)
    return data

class Vertex:
    def __init__(self, id, content, prodType, color, font, xPosition, yPosition,vWidth,vHeight):
        self.id = id
        self.content = content
        self.prodType = prodType
        self.color = color
        self.font = font
        self.x = xPosition
        self.y = yPosition
        self.width = vWidth
        self.height = vHeight


    def show(self):
        print("Vertex:","\n\tid:", self.id,"\tid:", self.id,"\n\tcontent:", self.content,"\n\ttype:", self.prodType, "\n\tcolor",self.color,"\n\tfont:", self.font,"\n\txPos:",self.x,"\n\tyPos:",self.y,"\n\twidth:",self.width,"\n\theight:",self.height)

class Edge:
    def __init__(self, fromId, toId, edgeId):
        self.source = fromId
        self.target = toId
        self.edgeId = edgeId

    def show(self):
        print("Edge from ",self.source," to ",self.target)

class MainStoryProps:
    def __init__(self, mainStoryX, mainStoryY, mainStoryWidth,mainStoryHeight,mainStoryEndX,mainStoryEndY):
        self.x = mainStoryX
        self.y = mainStoryY
        self.width = mainStoryWidth
        self.height = mainStoryHeight
        self.endX = mainStoryEndX
        self.endY = mainStoryEndY





def isVertexColorCorrect(vertex:Vertex, vertexTypesList, vertexColorDict):
    """
    checks if Vertex class instance color attribute is adequate to its type
    :param vertex: Vertex class instance
    :param vertexTypesList: list of strings, naming current vertex types
    :param vertexColorDict: dictionary of possible colors, for each type of vertex
    :return: Boolean, True if color is correct, otherwise False
    """

    for type in vertexTypesList:
        if(vertex.prodType == type):
            return vertex.color.lower() in vertexColorDict[type]

    return False

def font_correct(vertex: Vertex, vertexTypesList, vertexFontDict):
    for type in vertexTypesList:
        if (vertex.prodType == type):
            return vertex.font.lower() in vertexFontDict[type]
    return False

def mayBeGeneric(production):

    """
    checks if production (content from vertex) suffices regular expressions for generic type

    :param production: string with production, ex. eng name / pl name; (Main_hero, Elixir)

    :return: Boolean
    """
    slashIndex = production.find("/")
    if(slashIndex == -1):
        return False

    beforeSlashRegex ="\s?([A-z\-’`',]+\s)+\s?"
    if(not bool(re.search(beforeSlashRegex,production[0:slashIndex]))):
        return False


    semicolonIndex  = production.find(";")

    if(semicolonIndex == -1):
        return False

    slashToSemicolon = production[slashIndex:semicolonIndex+1]
    slashToSemicolonRegex = "/\s([A-ząćĆęłŁńóÓśŚżŻźŹ\-’`',]+\s?)+\;"

    if(not bool(re.search(slashToSemicolonRegex,slashToSemicolon))):
        return False

    bracketsPart = production[semicolonIndex+1:]
    bracketsRegex ="\s?\((\s?([A-z_ /’`'])+\s?,)*\s?([A-z_ /’`'])+\s?\)"

    if(not bool(re.search(bracketsRegex,bracketsPart))):
        return False

    return True



def separateArgsFromBrackets(argsInBrackets):
    """
    helper method to obtain arguments list from string starting with brackets
    :param argsInBrackets: ex. (Main_hero,Wizzard)
    :return: list of string args from brackets
    """
    argsList = []

    argsInBrackets = argsInBrackets.strip()
    argsInBrackets = argsInBrackets.replace("(","")

    while "," in argsInBrackets:
        argsInBrackets = argsInBrackets.strip()
        commaAt = argsInBrackets.find(",")
        argsList.append(
            argsInBrackets[0:commaAt].strip()
        )
        argsInBrackets = argsInBrackets[commaAt+1:]

    argsInBrackets = argsInBrackets.replace(")","").strip()

    argsList.append(argsInBrackets)
    return argsList



def checkIfDetailedVertexesAreAllowed(vertexList, allowedDetailedProductionList, testResultDict):
    """
    loop for use of isDetailedProductionAllowed()
    :param vertexList: List containing Vertex entities
    :param allowedDetailedProductionList: allowed productions list, read from json
    :param testResultDict: reference for test dict
    """

    detailedProductionType = "detailed"

    for x in vertexList:
        if(x.prodType == detailedProductionType):
            isDetailedProductionAllowed(x,allowedDetailedProductionList, testResultDict)

def fill_dict(testResultDict, identifier, elementTitle, infoMessage, messageCategory):
    '''
    :param testResultDict: defaultdict to fill
    :param identifier: id of element to use as a key
    :param elementTitle: title of element, like production
    :param infoMessage: message with what is wrong
    :param messageCategory: type, for now it should be ERROR or WARNING
    '''

    if identifier not in testResultDict:
        testResultDict[identifier] = defaultdict()

    idDict = testResultDict[identifier]


    if "Title" not in idDict:
        idDict["Title"] = elementTitle

    if "Problems" not in idDict:
        idDict["Problems"] = defaultdict()

    problemDict = idDict["Problems"]

    if messageCategory not in problemDict:
        problemDict[messageCategory] = []

    problem = defaultdict()

    problem["Info"] = infoMessage
    problem["Category"] = messageCategory

    problemDict[messageCategory].append(problem) # ew zamiana na stringa


    # testResultDict[vertex.id][production].append(
    #     "ERROR\n\t" + production + "\n\tDetailed production was not found on allowed detailed productions list, check for spelling mistakes")

    # testResultDict.append("ERROR\n\t" +production + "\n\tDetailed production was not found on allowed detailed productions list, check for spelling mistakes" )


def printTestDict(testResultDict:defaultdict):
    for identifier in testResultDict.keys():
        print("Element with Id:", identifier)

        idDict = testResultDict[identifier]

        print("Title: ", idDict["Title"])
        print("Problems:")

        problemsDict = idDict["Problems"]
        # print(problemsDict.keys())
        for key in problemsDict:
            problem = problemsDict[key]
            for p in problem:
                print(key,"\n\t",p["Info"])

        print("\n")


def areThereErrorsInTestDict(testResultDict:defaultdict):
    hasError = False

    for identifier in testResultDict.keys():
        idDict = testResultDict[identifier]
        problemsDict = idDict["Problems"]
        if "ERROR" in problemsDict.keys():
            hasError = True
    return hasError

def isDetailedProductionAllowed(vertex, detailedProductionList, testResultDict):
    """
    checks if production is on allowed json list, by comparing name
    :param vertex: instance of Vertex
    :param allowedDetailedProductionList: allowed productions list, read from json
    :param testResultDict: reference for test dict
    """
    isOnList = False
    # print("val prod",production)
    for p in detailedProductionList:
        # print(production,"\n",p["Title"],"\n", p["Title"]==production,"\n")
        if p["Title"].strip() == vertex.content.strip():
            isOnList = True
    # print("\n")
    if not isOnList:

        message = "Detailed production was not found on allowed detailed productions list, check for spelling mistakes"
        fill_dict(testResultDict,vertex.id,vertex.content,message,"ERROR")

def checkIfDetailedOrAutomaticVertexesAreAllowed(vertexList, allowedDetailedProductionList, allowedAutomaticProductionList, testResultDict):
    """
    loop for use of isDetailedProductionAllowed()
    :param vertexList: List containing Vertex entities
    :param allowedDetailedProductionList: allowed productions list, read from json
    :param testResultDict: reference for test dict
    """

    detailedProductionType = "detailed"

    for x in vertexList:
        if(x.prodType == detailedProductionType):
            isDetailedOrAutomaticProductionAllowed(x, allowedDetailedProductionList, allowedAutomaticProductionList, testResultDict)

def isDetailedOrAutomaticProductionAllowed(vertex, detailedProductionList, automaticProductionList, testResultDict):
    """
    checks if production is on allowed json lists, by comparing name
    use of generic productions is due to similar form of detailed and automatic productions

    :param vertex: string name of production, format. Eng name / Pl name
    :param automaticProductionList: allowed generic productions list, read from json
    :param detailedProductionList: allowed productions list, read from json
    :param testResultDict: reference for test dict
    """
    isOnList = False
    # print("val prod",production)
    for p in detailedProductionList:
        # print(production,"\n",p["Title"],"\n", p["Title"]==production,"\n")
        if p["Title"].strip() == vertex.content.strip():
            isOnList = True

    if not isOnList:
        for p in automaticProductionList:
            # print(production,"\n",p["Title"],"\n", p["Title"]==production,"\n")
            if p["Title"].strip() == vertex.content.strip():
                isOnList = True

                message = "Automatic production detected. Make sure if there should be no args. You can ignore color warning for this one"
                fill_dict(testResultDict, vertex.id, vertex.content, message, "WARNING")

    # print("\n")
    if not isOnList:

        message = "Production was not found on allowed detailed and automatic productions lists, check for spelling mistakes"
        fill_dict(testResultDict, vertex.id, vertex.content, message, "ERROR")

        # testResultDict.append("ERROR\n\t" +production + "\n\tDetailed production was not found on allowed detailed productions list, check for spelling mistakes" )

def isGenericProductionAllowed(vertex, genericProductionList, charactersList, itemsList, locationsList, testResultDict):
    """
    checks if production is on allowed json list, by comparing name,
    checks if arguments in brackets are on one of allowed lists,
    counts and checks number of arguments

    :param vertex: string name of production, format. Eng name / Pl name; (Arg, Arg)
    :param genericProductionList: allowed generic productions, read from json
    :param charactersList: allowed characters list
    :param itemsList: allowed items list
    :param locationsList: allowed locations list
    :param testResultDict: reference for test dict

    :return Boolean
    """
    begIndex = 0
    if vertex.content[0] == " ":
        begIndex = 1

    semicolonIndex = vertex.content.find(";")

    if vertex.content[semicolonIndex] == " ":
        semicolonIndex -=1

    titlePart = vertex.content[begIndex:semicolonIndex]
    isOnList = False

    for p in genericProductionList:
        if p["Title"] == titlePart:

            isOnList = True

    if not isOnList:

        if "`" in vertex.content or "'" in vertex.content:
            message = "Generic production was not found on allowed generic productions list, check for accidental ' apostrophes, (maybe ’)"
            fill_dict(testResultDict, vertex.id, vertex.content, message, "ERROR")

        else:
            message = "Generic production was not found on allowed generic productions list, check for spelling mistakes"
            fill_dict(testResultDict, vertex.id, vertex.content, message, "ERROR")

        return False


    bracketPart = vertex.content[semicolonIndex + 1:]
    bracketPart = bracketPart.strip()

    argsInBrackets = separateArgsFromBrackets(bracketPart)

    # count args
    commaCount = bracketPart.count(',')
    if (commaCount != 0):
        argsCount = commaCount + 1
    else:
        argsCount = 1

    charactersCount = 0
    itemsCount = 0
    connectionsCount =0
    narrationCount = 0

    # print("!!")
    for p in genericProductionList:
        if p["Title"] in titlePart:
            loc = p["LSide"]
            characsloc = loc["Locations"]

            for i in characsloc[0]["Characters"]:
                # for c in i:
                # print(list(i))

                # if ["Id"] in list(i):
                # print(i)
                if "Id" in i:
                    charactersCount += 1
                    # print(i)
                # charactersCount += 1

                if("Items" in  i ):
                    itemsCount += len(i["Items"])
                    # for ids in i["Items"]:
                    #     # if ["Id"] in ids:
                    #     print(ids)
                    # print(i["Items"])

                if ("Narration" in i):
                    narrationCount +=1

            # if "Narration" in characsloc[0]:
            #     for i in characsloc[0]["Narration"]:
            #         charactersCount += 1
            #         if("Items" in  i ):
            #             itemsCount += len(i["Items"])


            if "Items" in characsloc[0]:
                for i in characsloc[0]["Items"]:
                    # print(i)
                    if "Id" in i:
                        charactersCount += 1

                    if("Items" in  i ):
                        itemsCount += len(i["Items"])
                        # for it in i["Items"]:
                        #     print(i)

                    if ("Narration" in i):
                        narrationCount +=1



            if "Location change" in vertex.content:
                if(argsCount == 2):
                    return True
            if "Picking item" in vertex.content or "Dropping item" in vertex.content:
                if(argsCount == 1):
                    return True

            if charactersCount + itemsCount + connectionsCount + narrationCount != argsCount:
                message = "Check amount of args in production"
                fill_dict(testResultDict, vertex.id, vertex.content, message, "WARNING")

                if argsCount == 1:
                    message = "Check amount of args in production"
                    fill_dict(testResultDict, vertex.id, vertex.content, message, "WARNING")


                elif "Location change" in vertex.content:
                    message = "Check amount of args in production"
                    fill_dict(testResultDict, vertex.id, vertex.content, message, "WARNING")

                else:
                    message = "Check amount of args in production, expected " + str(charactersCount + itemsCount + connectionsCount + narrationCount) + ", but got " + str(argsCount)

                    fill_dict(testResultDict, vertex.id, vertex.content, message, "WARNING")


    for arg in argsInBrackets:
        if (arg not in charactersList) and (arg not in itemsList) and (arg not in locationsList) :
            if "/" in arg:
                slashArgs = arg.split('/')
                areSlashArgsCorrect = True
                # print(slashArgs)
                for sa in slashArgs:
                    if (sa not in charactersList) and (sa not in itemsList) and (sa not in locationsList):
                        # zamiast errora - slashe
                        message = "In arg: " + arg + ", this arg " + sa + " was not found on Characters/Items/Locations list, check for spelling mistakes"
                        fill_dict(testResultDict, vertex.id, vertex.content, message, "ERROR")

                #
            else:

                if narrationCount > 0:
                    message = arg + " is not on allowed Characters/Items/Locations list, Narration element was detected, Ignore if its narration"
                    fill_dict(testResultDict, vertex.id, vertex.content, message, "WARNING")

                else:
                    message = arg + " is not on allowed Characters/Items/Locations list, check for spelling mistakes"
                    fill_dict(testResultDict, vertex.id, vertex.content, message, "ERROR")



    return True


def parseColor(style):
    """
    find color bycolor string from style cropped from drawing xml
    :param style: attrib["style"] from drawing
    :return: string color
    """
    fillColorTag ="fillColor"
    hexColorLen = 7 # with #xxxxxx
    if style.find(fillColorTag) == -1:
        return "none"


    begColorIndex = style.index(fillColorTag) + len(fillColorTag) +1
    endColorIndex = begColorIndex + hexColorLen


    return style[begColorIndex:endColorIndex]

def parse_font(style):
    fillFontTag = "fontFamily"
    font_len = 9
    if style.find("fontFamily") != -1:
        begFont = style.index(fillFontTag) + len(fillFontTag) + 1
        endFont = begFont + font_len
        return style[begFont:endFont]
    else:
        return ""

def getNeighboursIds(vertexId, edgeDict):
    """
    finds list of neighbouring vertexes ids
    :param production: string name of production, format. Eng name / Pl name; (Arg, Arg)
    :param edgeDict: dictionary of key: vertexId, value: list of Edge entities, which source is vertex of id key

    :return list of neighbouring vertexes ids
    """
    # print("checkup ", vertexId)
    neigboursList = edgeDict.get(vertexId)
    neigboursIdList = []
    # print(neigboursList)

    if bool(neigboursList):
        for e in neigboursList:
            neigboursIdList.append(e.target)
    else:
        neigboursIdList = []

    return neigboursIdList


def dfsToEnding(vertexDict, edgeDict, visitedList, foundEnding, currentVertex):
    """
    Checks if there is any ending using pseudo DFS search, use only on non ending vertexes

    :param vertexDictdictionary of key: vertexId value: Vertex entity
    :param edgeDict: dictionary of key: vertexId value: list of Edge entities, which source is vertex of id key
    :param visitedList: list of already visited vertex ids, should be empty at first
    :param foundEnding: List containing Boolean value if ending was found, list is there to keep reference value in recursion, use of this param should be done with [False], so search is done
    :param currentVertex - string id of current vertex, use one where you want to start

    :return Boolean
    """
    visitedList.append(currentVertex)

    neighboursIds = getNeighboursIds(currentVertex,edgeDict)

    endingProductionType = "ending"


    if( vertexDict.get(currentVertex).prodType == endingProductionType):
        foundEnding[0] = True

    if foundEnding[0]:
        return True # found an ending from vertex

    for vId in neighboursIds:
        if foundEnding[0]:
            return True

        if vId not in visitedList:
            return dfsToEnding(vertexDict,edgeDict,visitedList,foundEnding,vId)

    if foundEnding[0]:
        return True # found an ending from vertex


    return False


def read_edges_vertex_from_drawing(drawingFile, vertexListToFill, edgeListToFill, edgeDictToFill, mainStoryPropsToFill, testResultDict, notAllowedShapesList):
    if "root" not in drawingFile:
        drawingFile = decompress_diagram(drawingFile)

    tree = ET.ElementTree(ET.fromstring(drawingFile))


    root = tree.getroot()
    parser = MyHTMLParser()
    mainStoryWidth= 0


    endingProductionType = "ending"

    for elem in root.iter('mxCell'):
        if "edge" in elem.attrib:

            if(("source" not in elem.attrib ) or ("target" not in elem.attrib)):
                if elem.attrib["id"] not in testResultDict:
                    testResultDict[elem.attrib["id"]] = defaultdict()  # było [] POPRAWKA IGG
                edge_x = 0
                edge_y = 0
                for geometry in elem.iter('mxGeometry'):
                    for point in geometry.iter('mxPoint'):
                        edge_x = point.attrib["x"]
                        edge_y = point.attrib["y"]



                message = "Edge with id " + str(elem.attrib["id"]) +"is not connected to source or target properly, coordinates: (" + str(edge_x) + "," + str(edge_y) +")"
                fill_dict(testResultDict, str(elem.attrib["id"]), "EDGE", message, "ERROR")
                # foundAtLeastBadEdge = True
                continue

            if("source" in elem.attrib ) and ("target" in elem.attrib):
                edgeListToFill.append(Edge(
                    elem.attrib["source"],
                    elem.attrib["target"],
                    elem.attrib["id"]
                ))




            if not bool(edgeDictToFill.get(elem.attrib["source"])):
                edgeDictToFill[elem.attrib["source"]] = []
                edgeDictToFill[elem.attrib["source"]].append(
                    Edge(
                        elem.attrib["source"],
                        elem.attrib["target"],
                        elem.attrib["id"]
                    ))
                continue

            edgeDictToFill[elem.attrib["source"]].append(
                Edge(
                    elem.attrib["source"],
                    elem.attrib["target"],
                    elem.attrib["id"]
                ))
            continue




        if "vertex" in elem.attrib:

            allowedShape = True
            for s in notAllowedShapesList:
                if s in elem.attrib["style"]:

                    message = str(s)+" Vertex shape is not allowed, skipping this vertex in checkups"
                    fill_dict(testResultDict, str(elem.attrib["id"]),"SHAPE" , message, "ERROR")

                    foundAtLeastBadOneVertex = True
                    continue





            if "ellipse" in elem.attrib["style"]:

                # move getting positions to method later, here and in normal vertex
                for geometry in elem.iter('mxGeometry'):
                    if 'x' in geometry.attrib:
                        xPos = geometry.attrib['x']
                        hasX = True
                    if 'y' in geometry.attrib:
                        yPos = geometry.attrib['y']
                        hasY = True
                    if 'width' in geometry.attrib:
                        width = geometry.attrib['width']
                        hasWidth = True
                    if 'height' in geometry.attrib:
                        height = geometry.attrib['height']
                        hasHeight = True
                if not (hasX and hasY and hasWidth and hasHeight):
                    hasX = False
                    hasY = False
                    hasWidth = False
                    hasHeight = False
                    foundAtLeastBadOneVertex = True

                    message = str(elem.attrib[
                            "id"]) + ' is not proper FINAL vertex, has no x or y position or no width, skipping this vertex in later checkups'

                    fill_dict(testResultDict, str(elem.attrib["id"]), "FINAL", message, "ERROR")

                if "value" in elem.attrib and not elem.attrib["id"] == "":
                    if( bool(re.search("\s?[1-9][0-9]?\s?",elem.attrib["value"]))):
                        vertexListToFill.append(
                            Vertex(elem.attrib["id"],
                                   elem.attrib["value"].replace("<br>","\n"),
                                   endingProductionType,
                                   parseColor(elem.attrib["style"]),
                                   parse_font(elem.attrib["style"]),
                                   float(xPos),
                                   float(yPos),
                                   float(width),
                                   float(height)
                                   ))
                else:

                    message = str(elem.attrib[
                                      "id"]) + ' Unexpected value in ending production (not a mission number)'

                    fill_dict(testResultDict, str(elem.attrib["id"]), "FINAL", message, "ERROR")




                vertexListToFill.append(
                    Vertex(elem.attrib["id"],
                           "",
                           endingProductionType,
                           parseColor(elem.attrib["style"]),
                           parse_font(elem.attrib["style"]),
                           float(xPos),
                           float(yPos),
                           float(width),
                           float(height)
                           )
                )

                continue # to not vertex it again

            if "#fff2cc" in elem.attrib["style"].lower() and mainStoryWidth==0 and ("ellipse" not in elem.attrib["style"]):
                for geometry in elem.iter('mxGeometry'):
                    mainStoryPropsToFill.x = float(geometry.attrib['x'])
                    mainStoryPropsToFill.y = float(geometry.attrib['y'])
                    mainStoryPropsToFill.width = float(geometry.attrib['width'])
                    mainStoryPropsToFill.height = float(geometry.attrib['height'])
                    mainStoryPropsToFill.endX = float(mainStoryPropsToFill.x + mainStoryPropsToFill.width/2 )
                    mainStoryPropsToFill.endY = float(mainStoryPropsToFill.y + mainStoryPropsToFill.height)
                continue



            hasX = False
            hasY= False


            parser.feed(elem.attrib["value"].replace("<br>","\n"))
            for geometry in elem.iter('mxGeometry'):

                if 'x' in geometry.attrib:
                    xPos = geometry.attrib['x']
                    hasX = True
                if 'y' in geometry.attrib:
                    yPos = geometry.attrib['y']
                    hasY = True
                if 'width' in geometry.attrib:
                    width = geometry.attrib['width']
                    hasWidth = True
                if 'height' in geometry.attrib:
                    height = geometry.attrib['height']
                    hasHeight= True
            if not (hasX and hasY and hasWidth and hasHeight):
                hasX=False
                hasY=False
                hasWidth = False
                hasHeight= False
                foundAtLeastBadOneVertex = True

                message = str(elem.attrib["value"]) + ' is not proper vertex, has no x or y position or no width, skipping this vertex in later checkups'

                fill_dict(testResultDict, str(elem.attrib["id"]), str(elem.attrib["value"]), message, "ERROR")

                continue


            vertexListToFill.append(
                Vertex(elem.attrib["id"],
                       reduce(lambda a,b: a+b,parser.return_data()),
                       "type",
                       parseColor(elem.attrib["style"]),
                       parse_font(elem.attrib["style"]),
                       float(xPos),
                       float(yPos),
                       float(width),
                       float(height)
                       )
            )

            continue

def checkVertexAlignmentInMainStory(vertexList:List[Vertex],mainStoryProps:MainStoryProps,testResultDict):
    """
    Checks if Vertexes inside main story area are alligned by middle axis
    Before this method call readEdgesAndVertexFromXml, so MainStoryProps is filled

    :param vertexList: list of vertexes to check, ones inside area are verified
    :param mainStoryProps: entity of MainStoryProps, which is used for verification
    :param testResultDict: dictionary to be filled with potential errors
    """
    # fix this method
    mainStoryFirstXValue = []
    for x in vertexList:
        if ( x.x > mainStoryProps.x) and ( x.y > mainStoryProps.y) and ( x.x < mainStoryProps.endX) and (x.y < mainStoryProps.endY):
            if len(mainStoryFirstXValue) == 0:
                mainStoryFirstXValue.append(x.x)

            if len(mainStoryFirstXValue) >0:
                if x.x != mainStoryFirstXValue[0]:

                    message = "Check if vertexes are alligned in main story"

                    fill_dict(testResultDict, str(x.id), str(x.content), message, "WARNING")

def checkIfVertexesAreIntersecting(vertexList:List[Vertex],testResultDict):
    """
    Checks if vertexes on list are intersecting, if two are, test dict at key "INTERSECTING" is appended

    :param vertexList: list of Vertex entities to verify
    :param testResultDict: dict to be appended with errors

    """
    endingProductionType = "ending"

    for v in vertexList:
        for v2 in vertexList:

            if (v != v2):
                if (v2.x >= v.x and v2.x <= v.x + v.width) and ((v2.y + v2.height > v.y and v2.y + v2.height < v.y + v.height) or (v2.y > v.y  and v2.y < v.y + v.height)):

                    # if str("INTERSECTING") not in testResultDict:
                    #     testResultDict["INTERSECTING"] = []

                    if(v.prodType == endingProductionType):
                        vDesc = "Ending production at (" + str(v.x) + "," + str(v.y) + ")"
                    else:
                        vDesc = v.content + " at (" + str(v.x) + "," + str(v.y) + ")"

                    if(v2.prodType == endingProductionType):
                        v2Desc = "Ending production at (" + str(v2.x) + "," + str(v2.y) + ")"
                    else:
                        v2Desc = v2.content + " at (" + str(v2.x) + "," + str(v2.y) + ")"

                    message = vDesc+ ' is intersecting with ' +v2Desc

                    fill_dict(testResultDict, v.id, v.content, message, "ERROR")
                    fill_dict(testResultDict, v2.id, v2.content, message, "ERROR")

def check_production_types_by_regex(vertexList:List[Vertex],testResultDict):
    """
    Checks production type with regexes,
    if type is known, then type is assigned to Vertex entity
    otherwise test result list is appended with proper error

    TYPE ASSIGNED HERE IS USED IN OTHER CHECKS.

    TO BE USED BEFORE FOLLOWING: checkVertexListColors(), checkIfDetailedVertexesAreAllowed(vertexList,allowedDetailedProductionList,testResultDict), checkIfGenericVertexesAreAllowed()

    :param vertexList: list of Vertex entities to verify
    :param testResultDict: dict to be appended with errors

    """
    missionProductionType= "mission"
    genericProductionType = "generic"
    detailedProductionType = "detailed"
    endingProductionType = "ending"
    missionProductionRegex = "^\(\s?(\w\s*)+[?|!]?\s?,\s?Q[0-9]+\s?(\)\s?)$"
    detailedProductionRegex = "s?([0-9A-z_-’`',]+\s)+\s?/\s?([0-9A-ząćĆęłŁńóÓśŚżŻźŹ\-_’`',]+\s?)+"

    for x in vertexList:


        if(mayBeGeneric(x.content)):
            x.prodType = genericProductionType
            continue

        if(bool(re.search(missionProductionRegex,x.content))):
            x.prodType = missionProductionType
            continue

        if(bool(re.match(detailedProductionRegex,x.content)) and "(" not in x.content and ";" not in x.content):

            x.prodType = detailedProductionType
            continue

        if( x.prodType != endingProductionType and "!" in x.content):

            message = "Production name does not seem to fit any proper format of production, check '!'"
            fill_dict(testResultDict, x.id, str(x.content), message, "ERROR")


        elif( x.prodType != endingProductionType):

            message = "Production name does not seem to fit any proper format of production"
            fill_dict(testResultDict, x.id, str(x.content), message, "ERROR")


def copy_vertex_list_to_dict(vertexList:List[Vertex],vertexDict):
    """
    Fills dict with vertexes on list, by following schema:
    key: vertex id, value: Vertex entity

    :param vertexList: list of Vertex entities to verify
    :param vertexDict: default dict to be filled with key: vertex id, value: Vertex entity

    """
    for v in vertexList:
        vertexDict[v.id] = v

def checkVertexListColors(vertexList, testResultDict,allowedColorDictionary):
    """
    Verifies if color from dictionary fits production type in entity

    :param vertexList: list of Vertex entities to verify
    :param testResultDict: dict to be appended with errors
    :param allowedColorDictionary: dict with key: prod type, value: list of allowed colors

    """

    missionProductionType= "mission"
    detailedProductionType = "detailed"
    endingProductionType = "ending"
    genericProductionType = "generic"

    vertexTypesList = [missionProductionType,detailedProductionType,endingProductionType,genericProductionType]

    for x in vertexList:
        if x.prodType == "type":
            message = "Skipped color check as production type was not recognized"
            fill_dict(testResultDict, x.id, str(x.content), message, "WARNING")

        elif not isVertexColorCorrect(x,vertexTypesList,allowedColorDictionary) and (x.color.lower() in allowedColorDictionary[genericProductionType] ):

            message = "Found color in production" + x.color + ", make sure its generic production(generic colors are none or #ffffff). If it is, ignore warning"
            fill_dict(testResultDict, x.id, str(x.content), message, "WARNING")

        elif not isVertexColorCorrect(x,vertexTypesList,allowedColorDictionary):

            message = "Color " + x.color+" in production of type "+x.prodType +" is not on allowed list: " + str(allowedColorDictionary[x.prodType])
            fill_dict(testResultDict, x.id, str(x.content), message, "ERROR")

def check_font(vertexList, testResultDict, allowedFontsDict):
    missionProductionType = "mission"
    detailedProductionType = "detailed"
    endingProductionType = "ending"
    genericProductionType = "generic"
    vertexTypesList = [missionProductionType, detailedProductionType, endingProductionType, genericProductionType]

    for x in vertexList:
        if x.prodType == "type":
            message = "Skipped FONT check as production type was not recognized"
            fill_dict(testResultDict, x.id, str(x.content), message, "WARNING")

        elif not font_correct(x, vertexTypesList, allowedFontsDict) and (
                x.font.lower() in allowedFontsDict[genericProductionType]):

            message = "Found FONT in production" + x.font + ", make sure its generic production(generic FONT is Helvetica). If it is, ignore warning"
            fill_dict(testResultDict, x.id, str(x.content), message, "WARNING")

        elif not font_correct(x, vertexTypesList, allowedFontsDict):

            message = "Font " + x.font + " in production of type " + x.prodType + " is not allowed: " + str(
            allowedFontsDict[x.prodType])
            fill_dict(testResultDict, x.id, str(x.content), message, "ERROR")

def checkIfGenericVertexesAreAllowed(vertexList, allowedGenericProductionList, charactersList, itemsList, locationsList, testResultDict):
    """
    loop for calling isGenericProductionAllowed()

    :param vertexList: list of Vertex entities to verify
    :param allowedGenericProductionList: allowed generic productions, read from json
    :param charactersList: allowed characters list
    :param itemsList: allowed items list
    :param locationsList: allowed locations list
    :param testResultDict: reference for test dict

    """
    genericProductionType = "generic"

    for x in vertexList:
        if(x.prodType == genericProductionType):
            isGenericProductionAllowed(x,allowedGenericProductionList,charactersList, itemsList, locationsList, testResultDict)


def checkOutgoingEdgesCorrectness(vertexDict,edgeDict,testResultDict):
    """
    checks if vertexes have outgoing edges

    :param vertexDict
    :param edgeDict
    :param testResultDict: dict w err
    """
    endingProductionType = "ending"
    for v in vertexDict.values():

        if not bool(edgeDict.get(v.id)):
            if v.prodType != endingProductionType:

                message = "No outgoing edges from non-ending vertex"
                fill_dict(testResultDict, v.id, str(v.content), message, "ERROR")


        if bool(edgeDict.get(v.id)) and v.prodType == endingProductionType:

            message = "Ending should not have outgoing edges"
            fill_dict(testResultDict, v.id, "ENDING", message, "ERROR")

# block 1 t2
def check_start_edges(vertexList, vertexDict,edgeList, edgeDict,testResultDict):
    """
    checks if there is starting edge by 2 criteria, first - not having incoming edges, second - having all vertex that are sources to incoming edges below

    :param vertexList
    :param edgeList
    :param vertexDict
    :param edgeDict
    :param testResultDict
    """
    suspectedStartingVertex = []

    suspectedStartingVertex = list(edgeDict.keys())

    # checking vertex with no incoming edge
    for edgeList in edgeDict.values():

        for edge in edgeList:

            for suspect in suspectedStartingVertex:
                if suspect == edge.target:
                    suspectedStartingVertex.remove(suspect)




    # second part, ones with incoming vertexes
    for v in vertexList:
        isStarting = False
        for e in edgeList:
            if e.target == v.id:
                if vertexDict[e.target].y < v.y:
                    isStarting = True
                else:
                    isStarting = False
                    break # breaking loop as one incoming edge is higher


        if isStarting:
            suspectedStartingVertex.append(suspectedStartingVertex)

    # end of starting finding validation


    if (len(suspectedStartingVertex )== 0 ):

        message = "Could not find staring point, make sure that it is higher than any vertex pointing to it or has no incoming edges"
        fill_dict(testResultDict, "START", "START", message, "ERROR")



    if(len(suspectedStartingVertex) > 1):

        message = "More than one vertex is a starting point (no incoming edges or its higher than all incoming edges), please check if there should be more than one starting points"
        fill_dict(testResultDict, "START", "START", message, "WARNING")

def getNeighboursIds(vertexId, edgeDict):
    """
    Finds list of neighbouring ids of vertex of given id, based on edge dictionary
    Dictionary can be filled with readEdgesAndVertexFromXml()

    :param vertexId: string id of vertex
    :param edgeDict: dictionary of key: source vertex id string, value: Edge entities, for which this id is source

    :return list of stirng ids of neighbours
    """

    neigboursList = edgeDict.get(vertexId)
    neigboursIdList = []

    if bool(neigboursList):
        for e in neigboursList:
            neigboursIdList.append(e.target)
    else:
        neigboursIdList = []

    return neigboursIdList

# foundEnding = [False] # to keep reference
def dfsToEnding(vertexDict, edgeDict, visitedIdList, foundEnding, currentVertexId):
    """
    Checks if there is any ending using pseudo DFS search, use only on non ending vertexes
    :param vertexDictdictionary of key: vertexId value: Vertex entity
    :param edgeDict: dictionary of key: vertexId value: list of Edge entities, which source is vertex of id key

    :param visitedList: list of already visited vertex ids, should be empty at first
    :param foundEnding: List containing Boolean value if ending was found, list is there to keep reference value in recursion, use of this param should be done with [False], so search is done
    :param currentVertex - string id of current vertex, use one where you want to start

    :return Boolean
    """
    endingProductionType = "ending"


    visitedIdList.append(currentVertexId)

    neighboursIds = getNeighboursIds(currentVertexId,edgeDict)


    if( vertexDict.get(currentVertexId).prodType == endingProductionType):
        foundEnding[0] = True

    if foundEnding[0]:
        return True # found an ending from vertex

    for vId in neighboursIds:
        if foundEnding[0]:
            return True

        if vId not in visitedIdList:
            return dfsToEnding(vertexDict,edgeDict,visitedIdList,foundEnding,vId)

    if foundEnding[0]:
        return True # found an ending from vertex


    return False

# block 1 t3
def check_any_ending_from_every_vertex(vertexList,vertexDict,edgeDict, testResultDict, foundAtLeastOneBadVertex):
    """
    Checks if there is any ending using pseudo DFS search, use only on non ending vertexes
    :param vertexDictdictionary of key: vertexId value: Vertex entity
    :param edgeDict: dictionary of key: vertexId value: list of Edge entities, which source is vertex of id key

    :param visitedList: list of already visited vertex ids, should be empty at first
    :param foundEnding: List containing Boolean value if ending was found, list is there to keep reference value in recursion, use of this param should be done with [False], so search is done
    :param currentVertex - string id of current vertex, use one where you want to start

    :return Boolean
    """
    endingProductionType = "ending"



    foundEnding = [False] # to keep reference
    visitedList = []
    foundEnding = [False]
    if not foundAtLeastOneBadVertex:

        for v in vertexList:
            visitedList = []
            foundEnding = [False]

            if v.prodType != endingProductionType:
                foundEnding = [False]
                if not dfsToEnding(vertexDict,edgeDict,visitedList,foundEnding,v.id):

                    message = "Could not reach any ending from vertex, check connections"
                    fill_dict(testResultDict, v.id, v.content, message, "ERROR")

    else:

        message = "Skipped ending search from each vertex"
        fill_dict(testResultDict, "SKIPPED DFS", "SKIPPED DFS", message, "WARNING")

#def diagram_validator(diagram_file_path: str, gameplay_file_path: str) -> Tuple[List[str], List[str]]:
#    diagram_err = []
#    diagram_warn = []
#    file_dravio = open(diagram_file_path, encoding="utf-8").read()
#    validate_drawing(type_call, file_dravio, allowedCharactersList, allowedItemsList, allowedLocationsList,
#                     allowedGenericProductionList, allowedDetailedProductionList, allowedAutomaticProductionList)
#    # gameplay_file_path
#
#    return diagram_err, diagram_warn

#def cheks_appearance(vertexList: dict = None, testResultDict: dict = None, allowedColorDictionary, allowedFontsDict) -> \
#        Tuple[List[str], List[str]]:
#    appearance_err = []
#    appearance_warn = []
#    checkVertexListColors(vertexList, testResultDict, allowedColorDictionary)
#    return appearance_err, appearance_warn

#type_call
def validate_drawing(drawingFile, allowedCharactersList, allowedItemsList, allowedLocationsList,
                     allowedGenericProductionList, allowedDetailedProductionList, allowedAutomaticProductionList):

    """
    validates drawing file (opened, not path) passed in args, based on allowed lists. Example of usage in validator.py

    :param drawingFile: already opened xml file with compressed or uncompressed drawing
    :param allowedCharactersList: characters list, already read from json
    :param allowedItemsList: items list, already read from json
    :param allowedLocationsList: locations list, already read from json
    :param allowedGenericProductionList: generic productions list, already read from json
    :param allowedDetailedProductionList: detailed productions list, already read from json
    :param allowedAutomaticProductionList: automatic productionslist, already read from json

    :return test result dictionary, K: Identifying name (vertex content/edge id) V: list of warnings and errors for key
    """


    # DEFINIOWANIE WARTOŚCI OBIEKTÓW
    missionProductionType = "mission"
    genericProductionType = "generic"
    detailedProductionType = "detailed"
    endingProductionType = "ending"
    allowedColorDictionary = defaultdict()
    allowedColorDictionary[missionProductionType] = "#e1d5e7"
    allowedColorDictionary[genericProductionType] = {"#ffffff", "none"}
    allowedColorDictionary[detailedProductionType] = "#ffe6cc"
    allowedColorDictionary[endingProductionType] = {"#fff2cc", "#000000", "#f5f5f5", "#e1d5e7", "none", "none;"}

     # fontFamily, fontSize, align
    allowedFontsDict = defaultdict()
    font_name = "Helvetica"
    allowedFontsDict["mission"] = font_name
    allowedFontsDict["generic"] = font_name
    allowedFontsDict["detailed"] = font_name
    allowedFontsDict["ending"] = ""
    notAllowedShapesList = ["rhombus", "process", "parallelogram", "hexagon", "cloud"]

    mainStoryProps = MainStoryProps(0, 0, 0, 0, 0, 0)

    # INICJALIZOWANIE STRUKTUR
    vertexList = []
    vertexDict = defaultdict()
    edgeList = []
    edgeDict = defaultdict()
    testResultDict = defaultdict()

    # LOADING PART
    read_edges_vertex_from_drawing(drawingFile, vertexList, edgeList, edgeDict, mainStoryProps, testResultDict,
                                        notAllowedShapesList)

    copy_vertex_list_to_dict(vertexList, vertexDict)

    check_production_types_by_regex(vertexList, testResultDict)

    #TODO block 2 - to separating---
    # TYPE RELATED CHECK PART
    # depends on check_production_types_by_regex(), types are assigned there
    # block 2 t6
    checkVertexListColors(vertexList, testResultDict, allowedColorDictionary)
    # block 2 t7
    # check_font(vertexList, testResultDict, allowedFontsDict)
                         
    # depends on check_production_types_by_regex(), types are assigned there
    checkIfDetailedOrAutomaticVertexesAreAllowed(vertexList, allowedDetailedProductionList,
                                                 allowedAutomaticProductionList, testResultDict)

    # depends on check_production_types_by_regex(), types are assigned there
    checkIfGenericVertexesAreAllowed(vertexList, allowedGenericProductionList, allowedCharactersList, allowedItemsList,
                                     allowedLocationsList, testResultDict)

    # CONNECTION-SPATIAL CHECK PART

    # depends on readEdgesAndVertexFromXml() main story props
    checkVertexAlignmentInMainStory(vertexList, mainStoryProps, testResultDict)

    checkIfVertexesAreIntersecting(vertexList, testResultDict)

    checkOutgoingEdgesCorrectness(vertexDict, edgeDict, testResultDict)
    # block 1 t2
    check_start_edges(vertexList, vertexDict, edgeList, edgeDict, testResultDict)
    # block 1 t3
    check_any_ending_from_every_vertex(vertexList, vertexDict, edgeDict, testResultDict, False)

    # print("RESULTS\n\n")

    # for t in testResultDict.keys():
    #     print("\n\nFound in\n", t, ":\n")
    #     for e in testResultDict[t]:
    #         print("-", e)

    return testResultDict


def create_counter():
    return {"counter": 1}


def update_counter(counter):
    counter["counter"] += 1
    return counter


def validate_jb(drawing_file, allowed_characters, allowed_items, allowed_locations, allowed_generic_productions,
                allowed_detailed_productions, allowed_automatic_productions):

    """
    validates drawing file based on allowed lists.

    :param drawing_file: already opened xml file with compressed or decompressed drawing
    :param allowed_characters: characters list from json
    :param allowed_items: items list from json
    :param allowed_locations: locations list from json
    :param allowed_generic_productions: generic productions list from json
    :param allowed_detailed_productions: detailed productions list from json
    :param allowed_automatic_productions: automatic productions list from json

    :return result dictionary
    """
    # testResultDict = defaultdict()
    #testResultDict = [dict(), dict(), dict()]

    if "root" not in drawing_file:
        drawing_file = decompress_diagram(drawing_file)

    drawing_file = drawing_file.replace("&amp;nbsp;", " ")
    drawing_file = drawing_file.replace("&nbsp;", " ")

    drawing_file = ET.fromstring(drawing_file)
    root = drawing_file.find('.//root')

    counter_vertexes = create_counter()
    counter_edges = create_counter()
    counter_other = create_counter()
    dict_vertexes = {}
    dict_edges = {}
    dict_other = {}

    for x in root.iter('mxCell'):
        x_id = x.get("id")
        if x_id and x.get("style") is None:
            dict_other[f"{counter_other['counter']}"] = add_to_dict(['id', 'value', 'style', 'id_source', 'id_target'], [x_id, x.get("value"), x.get("style"), x.get("source"), x.get("target")])
            counter_other = update_counter(counter_other)
            continue
        if "rounded=0" in x.attrib["style"]:
            if x.get('vertex') == "1":
                style_dict = parse_style(x.get("style"))
                value_dict = parse_value(x.get("value"))
                if x is not None:
                    geometry_node = x.find('.//mxGeometry')
                    geometry = {
                        'x': geometry_node.get("x"),
                        'y': geometry_node.get("y"),
                        'width': int(geometry_node.get("width")),
                        'height': int(geometry_node.get("height")),
                        'as': geometry_node.get("as"),
                    }
                dict_vertexes[f"{counter_vertexes['counter']}"] = add_to_dict(['id', 'value', 'style', 'geometry'],
                                                                              [x_id, value_dict, style_dict, geometry])
                counter_vertexes = update_counter(counter_vertexes)
            if x.get('edge') == "1":
                style_dict = parse_style(x.get("style"))
                geometry = parse_geometry(x_id, root)
                dict_edges[f"{counter_edges['counter']}"] = add_to_dict(['id', 'style', 'id_source', 'id_target', 'geometry'],
                                                                        [x_id, style_dict, x.get("source"), x.get("target"), geometry])
                counter_edges = update_counter(counter_edges)
        else:
            style_dict = parse_style(x.get("style"))
            geometry = parse_geometry(x_id, root)
            dict_other[f"{counter_other['counter']}"] = add_to_dict(['id', 'value', 'style', 'id_source', 'id_target', 'geometry'],
                                                                    [x_id, x.get("value"), style_dict, x.get("source"), x.get("target"), geometry])
            counter_other = update_counter(counter_other)

    main_dict = collect_data(dict_vertexes, dict_edges, dict_other)
    all_errors = all_checks(main_dict)
    display_errors(all_errors)
    return main_dict
    # return testResultDict


def add_to_dict(keys, values):
    def_dict = dict.fromkeys(keys, '')
    def_dict.update(zip(keys, values))
    return def_dict


def collect_data(dict_vertexes, dict_edges, dict_other):

    main_dict = {
        'Vertexes': dict_vertexes,
        'Edges': dict_edges,
        'Other': dict_other
    }
    return main_dict


def all_checks(main_dict):
    diagram_err = {'errors': {}, 'warnings': {'counter': 0}}

    zero_check(main_dict, diagram_err)
    check_source_target(main_dict, diagram_err)
    check_vertex_coordinates(main_dict, diagram_err)
    check_font(main_dict, diagram_err)
    return diagram_err


def zero_check(main_dict, diagram_err):
    vertexes = main_dict['Vertexes']
    template_width = 260
    template_height = 40

    for key, item in vertexes.items():
        if 'geometry' in item:
            geometry = item['geometry']
            if not (geometry.get('width') == template_width and geometry.get('height') == template_height):
                add_error_to_diagram_err(diagram_err, 'error', 'struktura', item.get('id'), geometry,
                                         f"Element does not corresponds to the pattern: width={template_width}, height={template_height}")
    return diagram_err


def check_source_target(main_dict, diagram_err):
    dictionary = main_dict['Edges']

    for key in ['id_source', 'id_target']:
        if key not in dictionary:
            add_error_to_diagram_err(diagram_err, 'error', 'struktura', dictionary.get('id'), {key}, f'There is no {key}')
        elif not dictionary[key]:
            add_error_to_diagram_err(diagram_err, 'error', 'struktura', dictionary.get('id'), {key}, f'{key} is empty')
    return diagram_err


def check_vertex_coordinates(main_dict, diagram_err):
    dictionary = main_dict['Vertexes']

    for vertex_id, vertex_data in dictionary.items():
        geometry = vertex_data.get('geometry', {})
        x_coordinate = geometry.get('x')
        y_coordinate = geometry.get('y')

        if x_coordinate is None and y_coordinate is None:
            add_error_to_diagram_err(diagram_err, 'error', 'struktura', {vertex_id}, geometry, f"{vertex_id}: both x and y are empty")
        elif x_coordinate is None:
            add_error_to_diagram_err(diagram_err, 'error', 'struktura', {vertex_id}, geometry, f"{vertex_id}: x is empty")
        elif y_coordinate is None:
            add_error_to_diagram_err(diagram_err, 'error', 'struktura', {vertex_id}, geometry, f"{vertex_id}: y is empty")
        else:
            continue
    return diagram_err


def check_font(main_dict, diagram_err):
    dictionary = main_dict['Vertexes']
    expected_values = {'fontSize': '14', 'fontFamily': 'Helvetica', 'align': 'center'}

    if 'style' not in dictionary:
        add_error_to_diagram_err(diagram_err, 'error', 'wygląd', dictionary.get('id'), '', 'There is no style')
    else:
        style_attr = dictionary['style']
        for attr, expected_value in expected_values.items():
            if attr not in style_attr or style_attr[attr] != expected_value:
                add_error_to_diagram_err(diagram_err, 'error', 'wygląd', dictionary.get('id'), style_attr.get(attr),
                                         f'There is no {attr} or its value is not equal {expected_value}')
    #print(diagram_err)
    return diagram_err


def search_name(istr):
    pattern = re.compile('<.*?>')
    return re.sub(pattern, '', istr)


def parse_style(style_dict):
    pattern = r'(\w+)=(\w+|"[^"]*")'
    matches = re.findall(pattern, style_dict)

    result_dict = {key: eval(value) if value.startswith('"') else value for key, value in matches}
    return result_dict


def parse_value(x):
    name = [x.strip() for x in search_name(x.strip().replace('<br>', ';')).split(';')]
    name = list(filter(lambda x: x != "", name))
    return name


def parse_geometry(target_cell_id, root):

    target_cell = None

    for cell in root.findall('.//mxCell'):
        if cell.get('id') == target_cell_id:
            target_cell_v = cell
            break

    if target_cell is not None:
        mx_geometry = target_cell.find('.//mxGeometry')

        result = {}

        # attributes
        for attr in mx_geometry.attrib:
            result[attr] = mx_geometry.attrib[attr]

        # mxPoints
        mx_points = []
        for mx_point_elem in mx_geometry.findall(".//mxPoint"):
            mx_point = {}
            for attr in mx_point_elem.attrib:
                mx_point[attr] = mx_point_elem.attrib[attr]
            mx_points.append(mx_point)

        if mx_points:
            result["mxPoints"] = mx_points

        return result


def printTestDict1(main_dict):
    for category, sub_dict in main_dict.items():
        print(f"{category}:")
        for key, value in sub_dict.items():
            print(f"  {key}: {value}")
        print()


def add_error_to_diagram_err(diagram_data, e_w_type, type_error, object_id, object_content, message):

    if 'errors' not in diagram_data:
        diagram_data['errors'] = {}
    if 'warnings' not in diagram_data:
        diagram_data['warnings'] = {}

    error_type = 'errors' if e_w_type == 'error' else 'warnings'

    if error_type not in diagram_data:
        diagram_data[error_type] = {}

    if 'counter' not in diagram_data[error_type]:
        diagram_data[error_type]['counter'] = 1
    else:
        diagram_data[error_type]['counter'] += 1

    error_id = f"{error_type}_{diagram_data[error_type]['counter']}"

    error_data = {
        'e_w_type': e_w_type,
        'type_error': type_error,
        'object_id': object_id,
        'object_content': object_content,
        'message': message
    }

    diagram_data[error_type][error_id] = error_data
    #print(error_data)


def display_errors(errors):
    if not errors or not errors.get('errors'):
        print("No errors or warnings to display.")
        return

    error_counter = errors['errors']['counter']
    warning_counter = errors['warnings']['counter']

    if error_counter:
        print("Errors:")
    elif warning_counter:
        print("Warnings:")
    else:
        return

    for error_id in range(1, error_counter + 1):
        error_key = f'errors_{error_id}'
        error_data = errors['errors'].get(error_key)

        if error_data:
            print(f"{error_id}:")
            print("  - Object ID:", error_data.get('object_id', 'N/A'))
            print("    Type:", error_data.get('type_error', 'N/A'))
            print("    Object content:", error_data.get('object_content', 'N/A'))
            print("    Message:", error_data.get('message', 'N/A'))
            print()


def filter_diagram_err(diagram_err, error=None, type_error=None, vertex_id=None):
    filtered_errors = {}

    for error_id, error_data in diagram_err.items():
        if (error is None or error_data['error'] == error) and \
           (type_error is None or error_data['type_error'] == type_error) and \
           (vertex_id is None or error_data['vertex_id'] == vertex_id):
            filtered_errors[error_id] = error_data

    return filtered_errors
