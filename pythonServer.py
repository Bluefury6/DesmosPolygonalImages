from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import base64
import numpy as np
from PIL import Image
import alphashape as AS
from time import time;
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from shapely.geometry import MultiPolygon, Polygon

app = Flask(__name__)
CORS(app)

def generateDesmosFrame(image, pixels, width, height):
    colorDict = {}

    imgPixels = np.array(image)
    colorList = [(int(color[0]), int(color[1]), int(color[2])) for color in np.unique(imgPixels.reshape(-1, imgPixels.shape[-1]), axis=0)]
    counter = 0
    totalColorCount = len(colorList)

    for color in colorList:
        colorDict[color] = {
            'imgObject': Image.new(mode="RGB", size=image.size, color=0),
            'subsets': [],
            'pixels': [],
        }
        colorDict[color]['img'] = colorDict[color]['imgObject'].load()

    for x in range(width):
        for y in range(height):
            color = pixels[x, y]
            colorDict[color]['pixels'].append((x, y))

            surroundingColors = [(0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)]
            if x != width-1:
                surroundingColors[0] = colorDict[color]['img'][x+1, y]
            if x != 0:
                surroundingColors[1] = colorDict[color]['img'][x-1, y]
            if y != height-1:
                surroundingColors[2] = colorDict[color]['img'][x, y+1]
            if y != 0:
                surroundingColors[3] = colorDict[color]['img'][x, y-1]

            if color not in surroundingColors[0:2]:
                if x != width-1:
                    colorDict[color]['pixels'].append((x+0.5, y))
                if x != 0:
                    colorDict[color]['pixels'].append((x-0.5, y))
            if color not in surroundingColors[2:]:
                if y != height-1:
                    colorDict[color]['pixels'].append((x, y+0.5))
                if y != 0:
                    colorDict[color]['pixels'].append((x, y-0.5))

    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(asyncPolygonProcessing, color, colorPixels, height): color for color, colorPixels in [(color, colorDict[color]['pixels']) for color in colorList]}
        for future in as_completed(futures):
            color = futures[future]
            colorDict[color]['subsets'] = future.result()
            counter += 1
            print(f"{color} -- #{counter} of {totalColorCount} images processed for polygonization")

    finalizedPolygonSet = orderedPolygonsForDesmosConversion(colorDict)

    print(time() - startTime)
    return [str(polygon['color']) + "|\\operatorname{polygon}(" + str(polygon['polygon']) + ")\n" for polygon in finalizedPolygonSet]

def asyncPolygonProcessing(color, colorPixels, height):
    currentColoredPixelsSet = colorPixels
    currentColoredPixelsSet = [(pos[0], height-pos[1]) for pos in currentColoredPixelsSet]
    return arrangeForPolygonization(currentColoredPixelsSet)

def orderedPolygonsForDesmosConversion(colorSets):
    unorderedPolygonSet = deque()
    orderedPolygonSet = []
    for color in colorSets:
        for polygon in colorSets[color]['subsets']:
            unorderedPolygonSet.append({'color': color, 'polygon': polygon})

    orderedPolygonSet.append(unorderedPolygonSet.popleft())

    requiredIterations = len(unorderedPolygonSet)

    while len(unorderedPolygonSet) > 0:
        if len(orderedPolygonSet)/requiredIterations % 0.01 < 0.001 and (len(orderedPolygonSet) + 1)/requiredIterations % 0.01 >= 0.001:
            print(f"{round(100*len(orderedPolygonSet)/requiredIterations)}% processed for buffering")
        
        alreadyInserted = False
        polygonInfo = unorderedPolygonSet.popleft()
        polygon = Polygon(polygonInfo['polygon'])
        
        for i in range(len(orderedPolygonSet)-1):
            comparisonPolygon = Polygon(orderedPolygonSet[i]['polygon'])
            if polygon.contains(comparisonPolygon) or not activeSorting:
                if len(list(polygon.exterior.coords)) <= 6:
                    orderedPolygonSet.insert(i, {'color': polygonInfo['color'], 'polygon': list(polygon.buffer(0.5, cap_style='flat', join_style='mitre').exterior.coords)})
                else:
                    orderedPolygonSet.insert(i, {'color': polygonInfo['color'], 'polygon': list(polygon.buffer(0.5, cap_style='square', join_style='mitre').exterior.coords)})
                alreadyInserted = True
                break
        if not alreadyInserted:
            orderedPolygonSet.append({'color': polygonInfo['color'], 'polygon': list(polygon.buffer(0.5, cap_style='square', join_style='mitre').exterior.coords)})

    return orderedPolygonSet


def arrangeForPolygonization(subset):
    convexHull = AS.alphashape(subset, alpha=1)
    polygons = []

    if isinstance(convexHull, MultiPolygon):
        for subPoly in convexHull.geoms:
            polygons.append(list(subPoly.exterior.coords))
    elif isinstance(convexHull, Polygon):
        polygons.append(list(convexHull.exterior.coords))
    
    return polygons        



@app.route('/renderFullVideo')
def renderVideo():
    print("\n\n")
    global frame_number
    global currentTime

    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number - 1)
    if frame_number >= frame_count or frame_number >= finalFrameNum:
        print(frame_number, frame_count)
        updateString = generateStats()
        endRecording()
        return jsonify({"image": None, "updateInfo": updateString, "isFinished": True})

    ret, frame = capture.read()

    if not ret:
        print("Error loading frame")
        return jsonify({"image": None, "updateInfo": updateString, "isFinished": True}) #"error" to retry, "video complete" to end

    updateString = generateStats()
    
    return jsonify({"image": getFrame(frame), "updateInfo": updateString, "isFinished": False})

def generateStats():
    global startTime
    global lastFrameTime

    currentTime = time()
    frameDeltaTime = currentTime - lastFrameTime
    deltaTime = currentTime - startTime
    projectedTime = (deltaTime / 3600)/(frame_number / finalFrameNum)
    projectedRemaining = projectedTime - (deltaTime / 3600)
    updateString = f"""
    Loading frame #{frame_number} of {frame_count}, approx. {round(100*100*frame_number / frame_count) / 100}% complete. {round(100*(100 - (100*frame_number / frame_count))) / 100}% remaining.
    Time since last frame loaded: {round(frameDeltaTime)} seconds
    Average time per frame process: {round(deltaFrame*100*deltaTime / frame_number) / 100} seconds
    Elapsed time: {int(deltaTime / 3600)} hour(s), {int(60*((deltaTime / 3600) % 1))} minutes, {int(60*(60*((deltaTime / 3600) % 1) % 1))} seconds. 
    Projected total: {int(projectedTime)} hour(s), {int(60*(projectedTime % 1))} minutes, {int(60*(60*(projectedTime % 1) % 1))} seconds.
    Projected remaining: {int(projectedRemaining)} hour(s), {int(60*(projectedRemaining % 1))} minutes, {int(60*(60*(projectedRemaining % 1) % 1))} seconds.
    """

    lastFrameTime = time()

    return updateString


def endRecording():
    print("Video rendering ended")
    output_video.release()


def getFrame(frame):
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame)
    print("generating Desmos polygons from image")
    width = image.size[0]
    height = image.size[1]

    if doResize:
        image = image.resize((intendedWidth, int(round(height*(intendedWidth/width)))))

    image = image.convert(mode="RGB").quantize(colors=intendedMaxColorCount, method=Image.Quantize.FASTOCTREE).convert(mode="RGB")
    pixels = image.load()

    width = image.size[0]
    height = image.size[1]

    convertedPolygonSet = generateDesmosFrame(image, pixels, width, height)
    output = [{'color': '#%02x%02x%02x' % (int(line.split("|")[0].split(', ')[0][1:]), int(line.split("|")[0].split(', ')[1]), int(line.split("|")[0].split(', ')[2][:len(line.split("|")[0].split(', ')[2])-1])), 'polygon': line.split("|")[1]} for line in convertedPolygonSet]
    
    return {'polygons': output, 'imgData': {'width': width, 'height': height}}

@app.route("/saveNewFrame", methods=['POST'])
def saveNewFrame():
    data = request.get_json();
    url = data['image']
    global frame_number

    _, image_data = url.split(';base64,')
    img_binary = base64.b64decode(image_data)
    nparr = np.frombuffer(img_binary, np.uint8)
    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    img_np = cv2.resize(img_np, (videoWidth, videoHeight))

    output_video.write(img_np)
    print("frame", frame_number, "compiled to video")
    frame_number += deltaFrame

    return jsonify(frame_number)



@app.route('/getData')
def getData():
    global frame_number
    global currentTime

    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    ret, frame = capture.read()
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame)
    print("generating Desmos polygons from image")
    width = image.size[0]
    height = image.size[1]

    if doResize:
        image = image.resize((intendedWidth, int(round(height*(intendedWidth/width)))))

    image = image.convert(mode="RGB").quantize(colors=100, method=Image.Quantize.MEDIANCUT).convert(mode="RGB")
    pixels = image.load()

    width = image.size[0]
    height = image.size[1]

    convertedPolygonSet = generateDesmosFrame(image, pixels, width, height)
    output = [{'color': '#%02x%02x%02x' % (int(line.split("|")[0].split(', ')[0][1:]), int(line.split("|")[0].split(', ')[1]), int(line.split("|")[0].split(', ')[2][:len(line.split("|")[0].split(', ')[2])-1])), 'polygon': line.split("|")[1]} for line in convertedPolygonSet]
    
    return jsonify({'polygons': output, 'imgData': {'width': width, 'height': height}})

if __name__ == '__main__':
    activeSorting = False
    doResize = True
    intendedWidth = 400
    intendedMaxColorCount = 137

    startTime = time()
    lastFrameTime = time()

    video = None
    capture = None
    finalFrameNum = 9999999 # set to a smaller number if needed, or larger if you want to render more frames

    frame_number = 1
    deltaFrame = 1
    video = "<Your video here>.mp4"
    capture = cv2.VideoCapture(video)

    fps = capture.get(cv2.CAP_PROP_FPS) / deltaFrame
    
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    print("total frame count:", frame_count, "\nfps count:", fps)

    videoWidth = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    videoHeight = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

    output_path = 'output.mp4'
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    output_video = cv2.VideoWriter(output_path, fourcc, fps, (videoWidth, videoHeight))

    capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    app.run(debug=True)