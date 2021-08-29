import asyncio
import io
import glob
import os
import sys
import time
import uuid
import requests
from urllib.parse import urlparse
from io import BytesIO

from PIL import Image, ImageDraw
from azure.cognitiveservices.vision.face import FaceClient
from msrest.authentication import CognitiveServicesCredentials

import cv2
import time
import numpy as np
import json

import ctypes
from multiprocessing import Process, Array
import threading

from dotenv import load_dotenv
load_dotenv()

class FaceRecognition():
    CAMARA_SOURCE = 0
    AZURE_KEY = os.getenv("AZURE_KEY1")
    AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
    BACK_ENDPOINT = os.getenv("BACK_ENDPOINT")
    BACK_ENABLE = False if os.getenv("BACK_ENABLE") == "False" else True
    
    def __init__(self):
        self.camaraSrc = FaceRecognition.CAMARA_SOURCE
        self.camaraShape = None
        self.camaraFrame = None
        self.camaraProcess = None

        # Create an authenticated FaceClient.
        self.face_client = FaceClient(FaceRecognition.AZURE_ENDPOINT, CognitiveServicesCredentials(FaceRecognition.AZURE_KEY))
        self.face_list_id = 'camara0'
        self.face_list_count = 0

    def deleteFaceList(self):
        self.face_client.face_list.delete(self.face_list_id, custom_headers=None, raw=False)

    def initDeployment(self):
        self.listCheck()

        cap = cv2.VideoCapture(self.camaraSrc)
        ret, frame = cap.read()
        if not ret:
            print("No camara Access")
            return
        self.camaraShape = frame.shape
        cap.release()

        self.camaraFrame = Array(ctypes.c_uint8, self.camaraShape[0] * self.camaraShape[1] * self.camaraShape[2], lock=False)
        self.camaraProcess = Process(target=self.startStream, args=(self.camaraFrame, self.camaraShape))
        self.camaraProcess.start()
        
        sharedFrame = np.frombuffer(self.camaraFrame, dtype=np.uint8)
        sharedFrame = sharedFrame.reshape(self.camaraShape)

        self.runModel(sharedFrame)

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

    def runModel(self, sharedFrame):
        # Free Trail 20 callsPerMinute
        callsPerMinute = 6
        callsInterval = 60 / callsPerMinute
        
        timeStart = time.time()

        while True:
            if time.time() - timeStart >= callsInterval:
                detatecionThread = threading.Thread(target=self.callDetection, args=(sharedFrame,))
                detatecionThread.start()
                timeStart = time.time()
            
    def callDetection(self, sharedFrame):
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
        
        def getCropRectangle(detected_face):
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
            right = min(right + ((oldRight - oldLeft) / 2), self.camaraShape[1])
            top = max(top - ((oldBottom - oldTop) / 2), 0)
            bottom = min(bottom + ((oldBottom - oldTop) / 2), self.camaraShape[0])
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
                img = img.crop(getCropRectangle(face))
                img.save("images/" + persisted_face_id + ".jpg")
                print("New Face:", persisted_face_id)
            else:
                print("Exisiting Face:", persisted_face_id)
            self.postInfo(persisted_face_id)

    def postInfo(self, persisted_face_id):
        if not FaceRecognition.BACK_ENABLE:
            return

        url = FaceRecognition.BACK_ENDPOINT + "addFaceAppearance"
        params = "?azure_id=" + persisted_face_id

        response = requests.post(url + params)
        response = json.loads(response.text)

        if response['status'] != 1:
            print(response['msg'])

    def startStream(self, camaraFrame, camaraShape):
        sharedFrame = np.frombuffer(camaraFrame, dtype=np.uint8)
        sharedFrame = sharedFrame.reshape(camaraShape)

        cap = cv2.VideoCapture(0)

        while(True):
            # Capture frame-by-frame
            ret, frame = cap.read()

            #Publish frame in Shared Array
            sharedFrame[:] = frame

            # Display the resulting frame
            cv2.imshow('frame',frame)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # When everything done, release the capture
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    FRInstance = FaceRecognition()
    FRInstance.deleteFaceList()
    FRInstance.initDeployment()
