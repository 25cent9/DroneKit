import numpy as np
import cv2
import os
import math

ROOMBA_POSITIVES_FOLDER_PATH = 'Roomba Dataset/Positives'

class cv2Window( ):
    def __init__( self, name, type = cv2.WINDOW_AUTOSIZE ):
        self.name = name
        self.title = name
        self.type = type

    def __enter__( self ):
        cv2.namedWindow( self.name, self.type )
        return self

    def __exit__( self, *args ):
        cv2.destroyWindow( self.name )

    def getTitle(self):
        return self.title

    def setTitle(self, new_title):
        self.title = new_title
        cv2.setWindowTitle(self.name, self.title)

    def isKeyDown(self, key):
        return cv2.waitKey( 1 ) & 0xFF == ord(key)

    def getKey(self):
        return chr(cv2.waitKey( 1 ) & 0xFF)

    def show( self, mat ):
        cv2.imshow( self.name, mat )

def visualizer(images, callback = None, win_title = 'Visualizer'):
    quit = False
    length = len(images)
    i = 0
    img = None

    with cv2Window( win_title ) as window:
        while not quit:
            if type(images[i]) is np.ndarray:
                img = images[i]
            elif type(images[i]) is str:
                img = cv2.imread(images[i])

            if callback:
                callback(img)

            window.show(img)
            key = window.getKey()

            while key not in 'npq':
                key = window.getKey()

            if key == 'n':
                i = ( i + 1 ) % length
            elif key == 'p':
                i = i - 1 if i > 0 else length-1
            elif key == 'q':
                quit = True

def getRoombaProposals(img):
    THRESHOLD_MIN = 130
    THRESHOLD_MAX = 255
    MIN_AREA = 50
    GROW_RECTANGLE_BY = 1.5
    GOLDEN_RATIO = (1 + 5**.5)/2

    hsvImage = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    ret, thresholded = cv2.threshold(hsvImage[:,:,1], THRESHOLD_MIN, THRESHOLD_MAX, cv2.THRESH_BINARY)
    erosion = cv2.erode(thresholded, np.ones((11,11), np.uint8))
    closing = cv2.morphologyEx(erosion, cv2.MORPH_CLOSE, np.ones((15,15), np.uint8), iterations = 5)
    
    modifiedImg, contours, hierarchy = cv2.findContours(closing, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
        area = cv2.contourArea(contour)

        if area >= MIN_AREA:
            x, y, w, h = cv2.boundingRect(contour)
            dimensions = np.array([w, h])
            topLeft = np.array([x, y]) - MIN_AREA*GOLDEN_RATIO
            bottomRight = np.array([x, y]) + dimensions + MIN_AREA*GOLDEN_RATIO
            cv2.rectangle(img, tuple(topLeft.astype(int)), tuple(bottomRight.astype(int)), (0, 255, 0), 3)

roombaImagePaths = [os.path.join(ROOMBA_POSITIVES_FOLDER_PATH, fileName) for fileName in os.listdir(ROOMBA_POSITIVES_FOLDER_PATH)]
visualizer(roombaImagePaths, getRoombaProposals)