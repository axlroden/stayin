import os
import sys
import time
import random
import pyautogui
import subprocess
from imagesearch import imagesearch, click_image
from datetime import datetime
import PySimpleGUI as sg
from threading import Thread
try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract
import numpy as np
import cv2

#####################################
#####################################
# WORK IN PROGRESS
#####################################
#####################################
def main():
    """
    Automate WoW classic logins and stay in
    """
    layout = [[sg.Button('Start', key="startbutton")],
              [sg.Button('Stop', key="stopbutton")],
              [sg.Text('_' * 30, justification='center')],
              [sg.Text('', size=(20, 2), font=('Helvetica', 10), justification='center', key='_OUTPUT_')]]
    global window
    window = sg.Window('Queue Monitor', layout)
    global running
    t1 = Thread(target=automator)
    while True:
        event, values = window.Read()
        if event is None:
            break
        if event == 'startbutton':
            running = True
            t1.start()
            window.Element('startbutton').Update('Restart')
        if event == 'stopbutton':
            running = False
            window.Element('startbutton').Update('Start')
            window.Element('_OUTPUT_').Update("Idle")
    window.Close()

def img2text(img):
    """
    Converts yellow queue text to string
    """
    # Convert BGR to HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # yellow
    lower_val = np.array([20, 100, 100])
    upper_val = np.array([30, 255, 255])

    # Threshold the HSV image to get only yellow colors
    mask = cv2.inRange(hsv, lower_val, upper_val)

    # invert the mask to get black letters on white background
    res = cv2.bitwise_not(mask)
    # blur a bit
    res = cv2.medianBlur(res, 3)

    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract'
    config = ("-l eng --oem 1 --psm 6")
    return pytesseract.image_to_string(res, config=config)

def automator():
    global window
    while running is True:
        # Make sure wow is not running
        window.Element('_OUTPUT_').Update("Killing WoW")
        os.system('taskkill /f /im WowClassic.exe')

        base_path = getattr(sys, '_MEIPASS', '.') + '/data/'

        # Launch wow without login from battle.net launcher
        window.Element('_OUTPUT_').Update("Launching WoW Classic")
        subprocess.call(base_path + '/bnetlauncher.exe wowclassic')

        # Enter world
        window.Element('_OUTPUT_').Update("Waiting for queue or Char Select")
        while running is True:
            pos = imagesearch(base_path + "change_realm.png")
            if pos[0] != -1:
                # queue...
                im = pyautogui.screenshot('test.png', region=(pos[0] - 42, pos[1] - 110, 420, 43))
                img = cv2.cvtColor(np.array(im), cv2.COLOR_RGB2BGR)
                print(img2text(img))
                time.sleep(10)
                print(img2text(img))
                os.system('taskkill /f /im WowClassic.exe')
                time.sleep(301)
                break
            pos = imagesearch(base_path + "enter_world.png")
            if pos[0] != -1:
                window.Element('_OUTPUT_').Update("Enter WoW")
                # Enter world button is there!
                print("No Queue")
                time.sleep(30)
                break


if __name__ == '__main__':
    main()
