import cv2
import numpy as np
import os
import math

from crop import crop

RED = (0,0,255)

ANNOTATIONS_FOLDER = r'C:\Users\Christopher\Documents\Face Datasets\Annotated Faces in the Wild\FDDB-folds'
ANNOTATION_FILE_NAME_ID = 'ellipseList.txt'
POSITIVE_IMAGES_FOLDER = r'C:\Users\Christopher\Documents\Face Datasets\Annotated Faces in the Wild\originalPics'

annotationFileNames = [name for name in os.listdir(ANNOTATIONS_FOLDER) if name.endswith(ANNOTATION_FILE_NAME_ID)]

class RectangleAnnotation( ):
    def __init__( self, w, h, center_x, center_y ):
        self.w = w
        self.h = h
        self.center_x = center_x
        self.center_y = center_y
        self.dx = int(self.w/2)
        self.dy = int(self.h/2)
        self.top_left = np.array([self.center_x - self.dx, self.center_y - self.dy])
        self.bottom_right = np.array([self.center_x + self.dx, self.center_y + self.dy])
        self.area = w*h

    def draw( self, mat, color = RED, thickness = 3):
        cv2.rectangle(mat, tuple(self.top_left), tuple(self.bottom_right), color, thickness)

    def cropOut( self, mat, newW = None, newH = None ):
        return crop(mat, tuple(self.top_left), tuple(self.bottom_right), newW, newH)

    def computeIoU( self, rect ):
        int_top_left = np.array([max(self.top_left[0], rect.top_left[0]), max(self.top_left[1], rect.top_left[1])])
        int_bottom_right = np.array([min(self.bottom_right[0], rect.bottom_right[0]), min(self.bottom_right[1], rect.bottom_right[1])])
        size = int_bottom_right - int_top_left
        intersectionArea = 0 if (size < 0).any() else np.prod(size)
        unionArea = self.area + rect.area - intersectionArea
        return intersectionArea/unionArea
        

class EllipseAnnotation( ):
    def __init__( self, major_axis_radius, minor_axis_radius, angle, center_x, center_y ):
        self.major_axis = int(float(major_axis_radius))
        self.minor_axis = int(float(minor_axis_radius))
        self.angle = float(angle)
        self.center_x = int(float(center_x))
        self.center_y = int(float(center_y))

    def draw( self, mat, color = RED, thickness = 3):
        cv2.ellipse(mat, (self.center_x, self.center_y), (self.major_axis, self.minor_axis), math.degrees(self.angle), 0, 360, color, thickness)

    def drawAsRect( self, mat, color = RED, thickness = 3):
        self.toRect().draw(mat)

    def toRect( self ):
        w = abs(int(round(self.minor_axis*math.sin(self.angle)))) * 2
        h = abs(int(round(self.major_axis*math.sin(self.angle)))) * 2
        return RectangleAnnotation(w, h, self.center_x, self.center_y)

class Faces( ):
    def __init__( self ):
        self.faces = {}
    
    def _insert(self, imgPath, annotation):
        if imgPath not in self.faces:
            self.faces[imgPath] = []

        self.faces[imgPath].insert( -1, annotation )

    def load( self, file, imgFolder ):
        imgPath = None
        numFaces = None

        for line in file:
            line = line.rstrip()

            if '/' in line:
                imgPath = r'%s\%s.jpg' % (imgFolder, line)
            else:
                try:
                    numFaces = int(line)
                except ValueError as e:
                    pass
                else:
                    for i in range(numFaces):
                        if imgPath not in self.faces:
                            self.faces[imgPath] = []
                        self.faces[imgPath].insert(-1, EllipseAnnotation(*next(file).split()[:-1]).toRect())

    def keys(self):
        return self.faces.keys()

    def getAnnotations(self,key):
        return self.faces.get(key)


def getFaceAnnotations():
    faceAnnotations = Faces()

    for fileName in annotationFileNames:
        with open( r'%s\%s' % ( ANNOTATIONS_FOLDER, fileName ) ) as file:
            faceAnnotations.load(file, POSITIVE_IMAGES_FOLDER)

    return faceAnnotations