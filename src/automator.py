import os
import sys
import random
import pyautogui  # needed for automating logout/login later
import threading
import subprocess
import productdb_pb2
from time import sleep
import PySimpleGUI as sg
from datetime import datetime
from imagesearch import imagesearch, click_image, imagesearch_numLoop


def main():
    """
    Automate WoW classic logins and stay in
    """
    layout = [[sg.Button('Start', key="startbutton")],
              [sg.Button('Stop', key="stopbutton")],
              [sg.Multiline(size=(70, 21),
                            write_only=True,
                            key='_OUTPUT_',
                            reroute_stdout=True,
                            echo_stdout_stderr=True,
                            reroute_cprint=True)]]

    global running
    global window
    window = sg.Window('Auto Stay In', layout, finalize=True)
    t1 = automator()
    while True:
        event, values = window.Read()
        if event is None:
            break
        if event == 'startbutton':
            if t1.is_alive():
                running = False
                # wait for termination
                t1.join()
            running = True
            t1.start()
            window.Element('startbutton').Update('Restart')
        if event == 'stopbutton':
            running = False
            t1.join()
            window.Element('startbutton').Update('Start')
    window.Close()


class automator(threading.Thread):
    """
    Main loop
    """
    def __init__(self):
        threading.Thread.__init__(self)
        self.base_path = getattr(sys, '_MEIPASS', '.') + '/data/'
        self.wow_classic_path, self.bnet_launcher_path = self.installpath()
        self.logmsg("WoW Classic path: {}".format(self.wow_classic_path))
        self.logmsg("Battle.net Launcher path: {}".format(self.bnet_launcher_path))

    def run(self):
        while running is True:
            # Make sure wow is not running
            self.logmsg("Killing WoW for fresh start")
            os.system('taskkill /f /im WowClassic.exe')

            # Launch wow
            self.logmsg("Run Battle.net launcher if not already open")
            cmd = '"{}" --game="wow_enus" --gamepath="{}" --productcode="wow_classic"'.format(self.bnet_launcher_path,
                                                                                              self.wow_classic_path)

            subprocess.Popen(cmd, shell=True)
            # Wait for play button
            self.logmsg("Waiting for play button")
            pos = imagesearch_numLoop(self.base_path + "play.png", 3, 7)
            if pos[0] != -1:
                click_image(self.base_path + "play.png", pos, "left", 0.2, offset=5)
            else:
                self.logmsg("Is there an Update button?")
                pos = imagesearch_numLoop(self.base_path + "update.png", 3, 2)
                if pos[0] != -1:
                    click_image(self.base_path + "update.png", pos, "left", 0.2, offset=5)
                    self.logmsg("Updating..")
                    pos = imagesearch_numLoop(self.base_path + "play.png", 3, 40)
                    self.logmsg("Waiting for play button")
                    if pos[0] != -1:
                        click_image(self.base_path + "play.png", pos, "left", 0.2, offset=5)
                    else:
                        self.logmsg("Play button not found after a long time.. try again.")
                        break
                else:
                    self.logmsg("Play button not found, \nmake sure Battle.net client is visibile and try again.")
                    break

            # Enter world
            self.logmsg("Waiting for character select")
            while running is True:
                pos = imagesearch(self.base_path + "change_realm.png")
                if pos[0] != -1:
                    # Fuck there's queue...

                    self.sleep(20)
                    continue
                pos = imagesearch(self.base_path + "enter_world.png")
                if pos[0] != -1:
                    self.logmsg("Enter WoW")
                    # Enter world button is there!
                    click_image(self.base_path + "enter_world.png", pos, "left", 0.2, offset=5)
                    self.sleep(5)
                    break

            # Ok now we are hopefully in the game !
            self.logmsg("In game!")
            while running is True:
                pos = imagesearch(self.base_path + "wow.png")
                if pos[0] != -1:
                    self.logmsg("Not in game anymore.")
                    # Fuck we are not in game anymore..
                    # Checking for Enter World
                    self.logmsg("Checking for Enter World")
                    pos = imagesearch(self.base_path + "enter_world.png")
                    if pos[0] != -1:
                        # Enter world button is there!
                        self.logmsg("Char select, in again")
                        click_image(self.base_path + "enter_world.png", pos, "left", 0.2, offset=5)
                        self.logmsg("In game!")
                    else:
                        # Checking for reconnect button
                        pos = imagesearch(self.base_path + "reconnect.png")
                        if pos[0] != -1:
                            # Reconnect button is there!
                            self.logmsg("Reconnect!")
                            pos = imagesearch(self.base_path + "okay.png")
                            if pos[0] != -1:
                                self.logmsg("Found okay button pressing before reconnect")
                                click_image(self.base_path + "okay.png", pos, "left", 0.2, offset=5)
                            self.sleep(3)
                            click_image(self.base_path + "reconnect.png", pos, "left", 0.2, offset=5)
                            # Wait for char select
                            self.logmsg("wait for char select for 20 secs max")
                            pos = imagesearch_numLoop(self.base_path + "enter_world.png", 1, 20)
                            if pos[0] != -1:
                                click_image(self.base_path + "enter_world.png", pos, "left", 0.2, offset=5)
                                self.logmsg("In game!")
                            else:
                                self.logmsg("Didn't see it .. restart time.")
                                break

                # Randomize recheck to not be consistent bot behaviour
                self.sleep(random.randint(10, 40))

    def sleep(self, secs):
        """
        Sleeps for x seconds, but kill thread if we stop running.
        """
        for i in range(secs):
            if running is False:
                sys.exit()
            sleep(1)

    def installpath(self):
        productdb_path = os.getenv('ALLUSERSPROFILE') + "\\Battle.net\\Agent\\product.db"
        if os.path.exists(productdb_path):
            f = open(productdb_path, "rb")
            db = productdb_pb2.Database()
            db.ParseFromString(f.read())
            f.close()
            productinstalls = db.productInstall
            for entry in productinstalls:
                if entry.productCode == "wow_classic":
                    wow_classic_path = entry.settings.installPath.replace("/", "\\")
                if entry.productCode == "bna":
                    bnet_launcher_path = entry.settings.installPath
                    bnet_launcher_path = bnet_launcher_path + "/Battle.net Launcher.exe".replace("/", "\\")
            return wow_classic_path, bnet_launcher_path
        else:
            self.logmsg("No product.db file found I can't determine your install dir.")

    def logmsg(self, msg):
        window.Element('_OUTPUT_').Update("{} {}\n".format(datetime.now().strftime("%H:%M:%S"), msg), append=True)

if __name__ == '__main__':
    main()
