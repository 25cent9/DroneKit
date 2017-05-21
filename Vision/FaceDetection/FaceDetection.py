import data
from visualize import cv2Window

import cv2

WINDOW_TITLE = '12_net_test'
TEST = False

from detect import TWELVE_CALIB_NET_FILE_NAME, TWELVE_NET_FILE_NAME
TRAIN = True
TRAIN_CALIB = True
TRAIN_CLASSIFIER = False

if __name__ == '__main__':
    if TEST:
        from detect import stage1_predict
        
        with cv2Window( WINDOW_TITLE ) as window:
            annotations = data.getFaceAnnotations()
            posImgPaths = tuple(annotations.keys())
            i = 0
            key = ''
            
            while key != 'q':
                img = cv2.imread(posImgPaths[i])
                
                for detection in stage1_predict(img):
                    detection.draw(img)
                
                window.show(img)
                key = window.getKey()
                
                while key not in 'npq':
                    key = window.getKey()
                
                if key == 'n':
                    i = ( i + 1 ) % len(posImgPaths)
                elif key == 'p':
                    i = i - 1 if i > 0 else len(posImgPaths)-1

    elif TRAIN:
        from train import train

        if TRAIN_CLASSIFIER:
            train(TWELVE_NET_FILE_NAME, 12, False)
        if TRAIN_CALIB:
            train(TWELVE_CALIB_NET_FILE_NAME, 12, True, True)
    