from multiprocessing import Process, Array, Value
from flask import Flask, render_template, Response, request, send_from_directory
from datetime import datetime, timedelta
import time
import threading
import imutils
from imutils.video import FPS
import ctypes
import cv2
import re
import base64

import asyncio
import io
import glob
import os
import sys
import uuid
import requests
from urllib.parse import urlparse
from io import BytesIO

from PIL import Image, ImageDraw
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials

import numpy as np
import json

from multiprocessing import Process, Array
import threading

from dotenv import load_dotenv
load_dotenv()

GPU_AVAILABLE = False
MAX_FPS = 25
CONFIDENCE_ = 0.5
NMS_THRESH_ = 0.3
VERBOSE = False

app = Flask(__name__)

class FaceRecognition():
    CAMARA_SOURCE = 0
    AZURE_KEY = os.getenv("AZURE_KEY1")
    AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
    BACK_ENDPOINT = os.getenv("BACK_ENDPOINT")
    BACK_ENABLE = False if os.getenv("BACK_ENABLE") == "False" else True
    
    def __init__(self, inputFrame, frameShape):
        self.inputFrame = inputFrame
        self.camaraSrc = FaceRecognition.CAMARA_SOURCE
        self.frameShape = frameShape

        # Create an authenticated FaceClient.
        self.face_client = FaceClient(FaceRecognition.AZURE_ENDPOINT, CognitiveServicesCredentials(FaceRecognition.AZURE_KEY))
        self.face_list_id = 'camara0'
        self.face_list_count = 0
        self.deleteFaceList()
        self.initDeployment()

    def deleteFaceList(self):
        self.face_client.face_list.delete(self.face_list_id, custom_headers=None, raw=False)

    def initDeployment(self):
        self.listCheck()
        self.runModel()

    def listCheck(self):
        currentLists = self.face_client.face_list.list()
        for currentList in currentLists:
            if currentList.face_list_id == self.face_list_id:
                currentList = self.face_client.face_list.get(self.face_list_id)
                if currentList.persisted_faces == None:
                    self.face_list_count = 0
                else:
                    self.face_list_count = len(currentList.persisted_faces)
                return
        
        self.face_client.face_list.create(self.face_list_id, name = self.face_list_id)

    def runModel(self):
        # Free Trail 20 callsPerMinute
        callsPerMinute = 6
        callsInterval = 60 / callsPerMinute
        
        timeStart = time.time()

        while True:
            if time.time() - timeStart >= callsInterval:
                detatecionThread = threading.Thread(target=self.callDetection, args=())
                detatecionThread.start()
                timeStart = time.time()
            
    def callDetection(self):
        sharedFrame = np.frombuffer(self.inputFrame, dtype=np.uint8)
        sharedFrame = sharedFrame.reshape(self.frameShape)

        img_data = cv2.imencode('.jpg', sharedFrame)[1].tobytes()

        detected_faces = self.face_client.face.detect_with_stream(image=io.BytesIO(img_data), detectionModel='detection_02')
        
        if not detected_faces:
            return

        def getRectangleList(detected_face):
            rect = detected_face.face_rectangle
            left = rect.left
            top = rect.top
            width = rect.width
            height = rect.height
            
            return [left, top, width, height]

        def getRectangle(detected_face):
            rect = detected_face.face_rectangle
            left = rect.left
            top = rect.top
            right = left + rect.width
            bottom = top + rect.height
            
            return ((left, top), (right, bottom))
        
        def getCropRectangle(detected_face, frameShape):
            rect = detected_face.face_rectangle
            left = rect.left
            top = rect.top
            right = left + rect.width
            bottom = top + rect.height
            oldLeft = left
            oldTop = top
            oldRight = right
            oldBottom = bottom
            left = max(left - ((oldRight - oldLeft) / 2), 0)
            right = min(right + ((oldRight - oldLeft) / 2), frameShape[1])
            top = max(top - ((oldBottom - oldTop) / 2), 0)
            bottom = min(bottom + ((oldBottom - oldTop) / 2), frameShape[0])
            return (left, top, right, bottom)
        
        for face in detected_faces:
            face_id = face.face_id
            target_face = getRectangleList(face)

            persisted_face_id = None
            if self.face_list_count > 0 :
                candidates = self.face_client.face.find_similar(face_id, self.face_list_id, max_num_of_candidates_returned=1)
                for candidate in candidates:
                    persisted_face_id = candidate.persisted_face_id

            if persisted_face_id == None:
                response = self.face_client.face_list.add_face_from_stream(self.face_list_id, image = io.BytesIO(img_data), target_face = target_face)
                self.face_list_count += 1

                persisted_face_id = response.persisted_face_id
                img = Image.open(BytesIO(img_data))
                img = img.crop(getCropRectangle(face, self.frameShape))
                img.save("faces/" + persisted_face_id + ".jpg")
                img.show()
                print("New Face:", persisted_face_id)
                self.postPerson(persisted_face_id)
            else:
                print("Exisiting Face:", persisted_face_id)
            self.postRecord(persisted_face_id)

    def postRecord(self, persisted_face_id):
        if not FaceRecognition.BACK_ENABLE:
            return

        url = FaceRecognition.BACK_ENDPOINT + "/api/v1/records/"
        data = {'id': persisted_face_id}
        
        response = requests.post(url, json = data)
        if (response.status_code != 200):
            print("Request Records StatusCode", response.status_code)
        response = response.json()
        
        if response['status'] != 1:
            print(response['msg'])
    
    def postPerson(self, persisted_face_id):
        if not FaceRecognition.BACK_ENABLE:
            return

        url = FaceRecognition.BACK_ENDPOINT + "/api/v1/persons/"
        data = {'id': persisted_face_id}
        response = requests.post(url, json = data)
        if (response.status_code != 200):
            print("Request Records StatusCode", response.status_code)
        response = response.json()
        if response['status'] != 1:
            print(response['msg'])

class CamaraRead:
    def __init__(self, source, originalFrame, originalFrameShape, stampedFrame, stampedFrameShape):
        self.source = source
        self.originalFrame = originalFrame
        self.originalFrameShape = originalFrameShape
        self.stampedFrame = stampedFrame
        self.stampedFrameShape = stampedFrameShape

        # Frame FileName Variables
        self.lastRequest = None
        self.secondId = None
        self.lastPath = None

        self.mainLoop()
    
    @staticmethod
    def addText(frame, size, now):
        font       = cv2.FONT_HERSHEY_SIMPLEX
        position   = (int(size[1]-100),int(size[0]-50))
        fontScale  = 0.5
        fontColor  = (255,255,255)
        lineType   = 2
        
        cv2.rectangle(frame, (position[0], position[1] - 15), (position[0] + 80, position[1] + 5), (0,0,0), -1)
        cv2.putText(frame, 
                    "Camara 1", 
                    position, 
                    font, 
                    fontScale,
                    fontColor,
                    lineType)

        position   = (20,20)

        cv2.rectangle(frame, (position[0], position[1] - 15), (position[0] + 210, position[1] + 5), (0,0,0), -1)
        date = now.strftime("%B %d, %Y %H:%M:%S")
        cv2.putText(frame, 
                    date,
                    position, 
                    font, 
                    fontScale,
                    fontColor,
                    lineType)
    
    def getFilename(self):
        now = datetime.now()
        date = now.strftime("%m_%d_%Y")
        hour = now.strftime("%H")
        minute = now.strftime("%M")
        if (self.lastRequest == now.strftime("%m_%d_%Y_%H_%M_%S")):
            self.secondId += 1
        else:
            self.secondId = 1
        self.lastRequest = now.strftime("%m_%d_%Y_%H_%M_%S")

        path = 'images/' + date + '/' + hour + '/' + minute + '/'
        if not os.path.exists(path):
            os.makedirs(path)
        
        if self.lastPath is not None and self.lastPath != path:
            joinThread = threading.Thread(target=self.joinMinute, args=(self.lastPath,))
            joinThread.start()

        if self.lastPath is None or self.lastPath != path:
            self.lastPath = path

        return path + now.strftime("%S") + "_" + str(self.secondId)

    def joinMinute(self, path):
        os.system('joinFiles.sh ' + path)

    def mainLoop(self):
        source = self.source
        originalFrame = self.originalFrame
        originalFrameShape = self.originalFrameShape
        stampedFrame = self.stampedFrame
        stampedFrameShape = self.stampedFrameShape

        print("[INFO] opening video file...", source)
        vs = cv2.VideoCapture(source)
        while vs.read()[0] == False:
            vs = cv2.VideoCapture(self.source)
        # vs.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))

        originalFrame_ = np.frombuffer(originalFrame, dtype=np.uint8)
        originalFrame_ = originalFrame_.reshape(originalFrameShape)

        stampedFrame_ = np.frombuffer(stampedFrame, dtype=np.uint8)
        stampedFrame_ = stampedFrame_.reshape(stampedFrameShape)

        while True:
            lastTime = time.time()
            status, frame = vs.read()

            if not status:
                vs = cv2.VideoCapture(source)
                vs.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
                continue

            frameStamped = frame.copy()
            CamaraRead.addText(frameStamped, stampedFrameShape, datetime.now())
            
            # Display the resulting frame
            if VERBOSE:
                cv2.imshow('Stream', frameStamped)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 75]
            cv2.imencode('.jpg', frameStamped, encode_param)[1].tofile(self.getFilename() + '.jpg')
            # cv2.imwrite(self.getFilename() + '.jpg', frameStamped)
            # cv2.imwrite(self.getFilename() + '.jpg', frameStamped, [int(cv2.IMWRITE_JPEG_QUALITY), 50])	
            
            frame = imutils.resize(frame, width=500)

            originalFrame_[:] = frame
            stampedFrame_[:] = frameStamped

            while time.time() - lastTime  < 1 / MAX_FPS:
                pass

@app.route('/camara')
def camaraStream():
    deltaDays = int(request.args.get("deltaDays"))
    deltaHours = int(request.args.get("deltaHours"))
    deltaMinutes = int(request.args.get("deltaMinutes"))
    deltaSeconds = int(request.args.get("deltaSeconds"))
    deltaFPS = int(request.args.get("deltaFPS"))
    #Video streaming route. Put this in the src attribute of an img tag
    return Response(showFrame(deltaDays, deltaHours, deltaMinutes, deltaSeconds, deltaFPS), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/faces/<path:filename>')
def image(filename):
    return send_from_directory('faces/', filename)

def showFrame(deltaDays, deltaHours, deltaMinutes, deltaSeconds, deltaFPS):
    outputFrame = np.frombuffer(stampedFrame, dtype=np.uint8)
    outputFrame = outputFrame.reshape(stampedFrameShape)
    lastPath = None
    frameStatus = None
    lastSecond = None
    lastSecondId = 0
    secondCache = []
    lastTime = None
    while True:
        lastTime = time.time()
        if deltaDays != 0 or deltaHours != 0 or deltaMinutes != 0 or deltaSeconds != 0:
            frame = None
            dateRequested = datetime.now() + timedelta(days=-deltaDays, hours=-deltaHours, minutes=-deltaMinutes, seconds=-deltaSeconds)
            date = dateRequested.strftime("%m_%d_%Y")
            hour = dateRequested.strftime("%H")
            minute = dateRequested.strftime("%M")
            second = dateRequested.strftime("%S")
            miliseconds = dateRequested.strftime("%f")
            path = 'images/' + date + '/' + hour + '/' + minute + '/'
            if os.path.exists(path):
                if lastPath is None or path != lastPath or not frameStatus:
                    cap = cv2.VideoCapture(path + "out.mp4")
                    lastPath = path
                    totalExpectedFrames = 25 * 60
                    totalFrames = cap.get(7)
                    secondsNotRecorded = int(round((totalFrames - totalExpectedFrames) / 25))

                if int(second) >= secondsNotRecorded:
                    lastSecondId = min((int(second) - secondsNotRecorded) * 25 + int(round(int(miliseconds) * 25 / 999999)), totalFrames)
                    cap.set(1, lastSecondId)
                    frameStatus, frame = cap.read()

            if frame is None:
                frame = np.zeros((stampedFrameShape[0], stampedFrameShape[1], 3), np.uint8)
                CamaraRead.addText(frame, stampedFrameShape, dateRequested)

            ret, buffer = cv2.imencode('.jpg', frame)
        else:
            ret, buffer = cv2.imencode('.jpg', outputFrame)
        
        frame_ready = buffer.tobytes()
        yield (b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n\r\n' + frame_ready + b'\r\n')  # concat frame one by one and show result
        
        while time.time() - lastTime  < 1 / max(MAX_FPS + deltaFPS, 1):
                pass

@app.route('/')
def index():
    """Video streaming home page."""
    return render_template('index.html')

# Start Init
if __name__  == "__main__":
    source = 0
    originalFrame = None
    originalFrameShape = None
    stampedFrame = None
    stampedFrameShape = None

    cap = cv2.VideoCapture(source)
    ret, frame = cap.read()
    stampedFrameShape = frame.shape
    frame = imutils.resize(frame, width=500)
    originalFrameShape = frame.shape
    cap.release()

    originalFrame = Array(ctypes.c_uint8, originalFrameShape[0] * originalFrameShape[1] * originalFrameShape[2], lock=False)
    stampedFrame = Array(ctypes.c_uint8, stampedFrameShape[0] * stampedFrameShape[1] * stampedFrameShape[2], lock=False)

    if True:
        processAReference = Process(target=CamaraRead, args=(source, originalFrame, originalFrameShape, stampedFrame, stampedFrameShape))
        processAReference.start()

        processBReference = Process(target=FaceRecognition, args=(originalFrame, originalFrameShape))
        processBReference.start()

    from waitress import serve

    app.debug=True
    app.use_reloader=False
    serve(app, host="0.0.0.0", port=8081)
    print("Server 0.0.0.0:8081")
