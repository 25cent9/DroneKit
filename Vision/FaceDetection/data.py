#!/usr/bin/env python3.5
import random
import os
import math

import h5py
import cv2
import numpy as np
import sqlite3

from util import static_vars
from FaceDetection import DEBUG

POSITIVE_IMAGE_DATABASE_FOLDER = r'aflw/data/'
POSITIVE_IMAGE_FOLDER = POSITIVE_IMAGE_DATABASE_FOLDER + 'flickr/'
POSITIVE_IMAGE_DATABASE_FILE = os.path.join(POSITIVE_IMAGE_DATABASE_FOLDER, 'aflw.sqlite')
FACE_DATABASE_PATHS = ('face12.hdf', 'face24.hdf', 'face48.hdf')

DATASET_LABEL = 'data'
LABELS_LABEL = 'labels'
BATCH_SIZE = 32

NEGATIVE_IMAGE_FOLDER = r'Negative Images/images/'
NEGATIVE_DATABASE_PATHS = ('neg12.hdf', 'neg24.hdf', 'neg48.hdf')
TARGET_NUM_NEGATIVES_PER_IMG = 40
TARGET_NUM_NEGATIVES = 200000
MIN_FACE_SCALE = 80
OFFSET = 4

SCALES = ((12,12),(24,24),(48,48))

CALIBRATION_DATABASE_PATHS = {SCALES[0][0]:'calib12.hdf',SCALES[1][0]:'calib24.hdf',SCALES[2][0]:'calib48.hdf'}
TARGET_NUM_CALIBRATION_SAMPLES = None
SN = (.83, .91, 1, 1.1, 1.21)
XN = (-.17, 0, .17)
YN = XN
CALIB_PATTERNS = [(sn, xn, yn) for sn in SN for xn in XN for yn in YN]

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

def numDetectionWindowsAlongAxis(size, stageIdx = 0):
    return (size-SCALES[stageIdx][0])//OFFSET+1

@static_vars(faces = [])
def getFaceAnnotations(dbPath = POSITIVE_IMAGE_DATABASE_FILE, posImgFolder = POSITIVE_IMAGE_FOLDER):
    if len(getFaceAnnotations.faces) == 0:
        with sqlite3.connect(dbPath) as conn:
            c = conn.cursor()

            select_string = "faceimages.filepath, facerect.x, facerect.y, facerect.w, facerect.h"
            from_string = "faceimages, faces, facepose, facerect"
            where_string = "faces.face_id = facepose.face_id and faces.file_id = faceimages.file_id and faces.face_id = facerect.face_id"
            query_string = "SELECT " + select_string + " FROM " + from_string + " WHERE " + where_string

            for row in c.execute(query_string):
                imgPath = os.path.join(posImgFolder, str(row[0]))

                if os.path.isfile(imgPath):
                    getFaceAnnotations.faces.append((imgPath, *row[1:]))

    return getFaceAnnotations.faces

def squashCoords(img, x, y, w, h):
    y = min(max(0, y), img.shape[0])
    x = min(max(0, x), img.shape[1])
    h = min(img.shape[0]-y, h)
    w = min(img.shape[1]-x, w)
    return (x, y, w, h)

def debug_showImage(img):
    cv2.imshow('debug', img)
    cv2.waitKey()

def createFaceDataset(stageIdx, debug = DEBUG):
    fileName = FACE_DATABASE_PATHS[stageIdx]
    resizeTo = SCALES[stageIdx]
    faceAnnotations = getFaceAnnotations()
    images = np.zeros((len(faceAnnotations), resizeTo[1], resizeTo[0], 3), dtype = np.uint8)
    curImg = None
    prevImgPath = None

    for i, (imgPath, x, y, w, h) in enumerate(faceAnnotations):
        if imgPath != prevImgPath:
            curImg = cv2.imread(imgPath)

        x, y, w, h = squashCoords(curImg, x, y, w, h)
        images[i] = cv2.resize(curImg[y:y+h,x:x+w], resizeTo)
        prevImgPath = imgPath

        if debug:
            debug_showImage(images[i])

    with h5py.File(fileName, 'w') as out:
        out.create_dataset(DATASET_LABEL, data = images, chunks = (BATCH_SIZE, *images.shape[1:]))



def createNegativeDataset(stageIdx, negImgFolder = NEGATIVE_IMAGE_FOLDER, numNegatives = TARGET_NUM_NEGATIVES, numNegativesPerImg = TARGET_NUM_NEGATIVES_PER_IMG, debug = DEBUG):
    fileName = NEGATIVE_DATABASE_PATHS[stageIdx]
    resizeTo = SCALES[stageIdx]
    negativeImagePaths = [os.path.join(negImgFolder, fileName) for fileName in os.listdir(negImgFolder)]
    images = np.zeros((numNegatives, resizeTo[1], resizeTo[0], 3), dtype = np.uint8)
    negIdx = 0
    numNegativesRetrievedFromImg = 0

    for i in np.random.permutation(len(negativeImagePaths)):
        if negIdx >= numNegatives: break
        img = cv2.resize(cv2.imread(negativeImagePaths[i]), None, fx = resizeTo[0]/MIN_FACE_SCALE, fy = resizeTo[1]/MIN_FACE_SCALE)

        for xOffset in np.random.permutation(numDetectionWindowsAlongAxis(img.shape[1], stageIdx)):
            if negIdx >= numNegatives or numNegativesRetrievedFromImg >= numNegativesPerImg: break

            for yOffset in np.random.permutation(numDetectionWindowsAlongAxis(img.shape[0], stageIdx)):
                if negIdx >= numNegatives or numNegativesRetrievedFromImg >= numNegativesPerImg: break
                x, y, w, h = squashCoords(img, resizeTo[0]*xOffset, resizeTo[1]*yOffset, *resizeTo)

                if (w == resizeTo[0] and h == resizeTo[1]):
                    images[negIdx] = img[y:y+h,x:x+w]
                    negIdx += 1
                    numNegativesRetrievedFromImg += 1

                    if debug:
                        debug_showImage(images[negIdx-1])

        numNegativesRetrievedFromImg = 0

    if negIdx < len(images)-1:
        images = np.delete(images, np.s_[negIdx:], 0)
        if debug: print(images.shape)

    with h5py.File(fileName, 'w') as out:
        out.create_dataset(DATASET_LABEL, data = images, chunks = (BATCH_SIZE, *images.shape[1:]))

def createCalibrationDataset(stageIdx, numCalibrationSamples = TARGET_NUM_CALIBRATION_SAMPLES if not DEBUG else BATCH_SIZE*2, calibPatterns = CALIB_PATTERNS, debug = DEBUG):
    numCalibrationSamples = math.inf if numCalibrationSamples is None else numCalibrationSamples
    faceAnnotations = getFaceAnnotations()

    resizeTo = SCALES[stageIdx]
    datasetLen = len(faceAnnotations)*len(calibPatterns) if numCalibrationSamples == math.inf else numCalibrationSamples
    dataset = np.zeros((datasetLen, resizeTo[1], resizeTo[0], 3), np.uint8)
    labels = np.zeros((datasetLen, 1))
    sampleIdx = 0

    fileName = CALIBRATION_DATABASE_PATHS.get(resizeTo[0])

    curImg = None
    prevImgPath = None
    
    for i, (imgPath, x, y, w, h) in enumerate(faceAnnotations):
        if sampleIdx >= numCalibrationSamples: break

        if imgPath != prevImgPath:
            curImg = cv2.imread(imgPath)

        for n, (sn, xn, yn) in enumerate(CALIB_PATTERNS):
            if sampleIdx >= numCalibrationSamples: break
            box = squashCoords(curImg, x + int(xn*w), y + int(yn*h), int(w*sn), int(h*sn))

            if box[2] > 0 and box[3] > 0:
                (box_x, box_y, box_w, box_h) = box
                dataset[sampleIdx] = cv2.resize(curImg[box_y:box_y+box_h,box_x:box_x+box_w], resizeTo)
                if debug: debug_showImage(dataset[sampleIdx])
                labels[sampleIdx] = n 
                sampleIdx += 1

    if sampleIdx < datasetLen:
        labels = np.delete(labels, np.s_[sampleIdx:], 0)
        dataset = np.delete(dataset, np.s_[sampleIdx:], 0)

    if debug: print(dataset.shape, labels.shape)

    with h5py.File(fileName, 'w') as out:
        out.create_dataset(LABELS_LABEL, data = labels, chunks = (BATCH_SIZE, 1))
        out.create_dataset(DATASET_LABEL, data = dataset, chunks = (BATCH_SIZE, resizeTo[1], resizeTo[0], 3))
