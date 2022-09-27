import os
import sys
import random
import win32gui
import win32api
import win32con
import threading
import subprocess
import productdb_pb2
from time import sleep
import PySimpleGUI as sg
from datetime import datetime
from imagesearch import imagesearch, click_image, imagesearch_numLoop
from screeninfo import get_monitors

def main():
    """
    Automate WoW classic logins and stay in
    """
    layout = [[sg.Button('Start', key="startbutton"), sg.Button('Stop', key="stopbutton")],
              [sg.Input(key='sleeptime', size=(5, 1), default_text='5'), sg.Text('Time to wait for Battle.net window (seconds)')],
              [sg.Multiline(size=(70, 21),
                            write_only=True,
                            key='_OUTPUT_',
                            reroute_stdout=True,
                            echo_stdout_stderr=True,
                            reroute_cprint=True)]]
    global window
    window = sg.Window('Auto Stay In', layout, finalize=True)
    t1 = Automator()
    while True:
        event, values = window.Read()
        if event is None:
            break
        sleeptime = int(values['sleeptime'])
        if event == 'startbutton':
            if t1.is_alive():
                t1.sleeptime(sleeptime)
                t1.resume()
            else:
                t1.sleeptime(sleeptime)
                t1.start()
            window.Element('startbutton').Update('Restart')
        if event == 'stopbutton':
            t1.pause()
            window.Element('startbutton').Update('Start')
    window.Close()


class Automator(threading.Thread):
    """
    Main thread
    """
    def __init__(self):
        super(Automator, self).__init__()
        self.paused = True
        self.state = threading.Condition()
        self.daemon = True
        self.waittime = 5
        self.base_path = getattr(sys, '_MEIPASS', '.') + '/data/'
        self.wow_classic_path, self.bnet_launcher_path = self.installpath()
        self.logmsg("WoW Classic path: {}".format(self.wow_classic_path))
        self.logmsg("Battle.net Launcher path: {}".format(self.bnet_launcher_path))
        # Check for 1080/1440p/4k
        for m in get_monitors():
            if m.is_primary is True:
                self.monitor_width = m.width
                self.monitor_height = m.height
        if self.monitor_height == 1080:
            self.logmsg("Detected 1080p monitor")
        elif self.monitor_height == 1440:
            self.logmsg("Detected 1440p monitor")
        elif self.monitor_height == 2160:
            self.logmsg("Detected 4k monitor")
        else:
            self.logmsg("Detected unsupported monitor resolution")
            sys.exit()
        self.play_img = self.base_path + "play.png"
        self.update_img = self.base_path + "update.png"
        self.change_realm_img = "{}change_realm_{}.png".format(self.base_path, self.monitor_height)
        self.enter_world_img = "{}enter_world_{}.png".format(self.base_path, self.monitor_height)
        self.okay_img = "{}okay_{}.png".format(self.base_path, self.monitor_height)
        self.reconnect_img = "{}reconnect_{}.png".format(self.base_path, self.monitor_height)
        self.wow_img = "{}wow_{}.png".format(self.base_path, self.monitor_height)

    def run(self):
        self.resume()
        loggedmsg = False
        while True:
            with self.state:
                if self.paused:
                    self.logmsg("Stopped")
                    self.state.wait()  # Wait until notified
                    loggedmsg = False
                    continue
            # Make sure wow is not running
            if process_exists("World of Warcraft"):
                self.logmsg("Killing WoW for fresh start")
                subprocess.Popen(["taskkill", "/f", "/im", "WowClassic.exe"])
            # Start battle.net launcher
            self.logmsg("Run Battle.net launcher/get in focus")
            cmd = '"{}" --game="wow_enus" --gamepath="{}" --productcode="wow_classic"'.format(self.bnet_launcher_path,
                                                                                              self.wow_classic_path)
            subprocess.Popen(cmd, shell=True)
            # Wait for play button
            self.click_play()
            self.sleep(5)
            # Enter world
            self.logmsg("Waiting for character select")
            while True:
                with self.state:
                    if self.paused:
                        break
                if not process_exists("World of Warcraft"):
                    self.logmsg("Can't find WoW window.. Restarting")
                    break
                pos = imagesearch(self.change_realm_img)
                if pos[0] != -1:
                    # Fuck there's queue...
                    if loggedmsg is False:
                        self.logmsg("Queue detected.. waiting..")
                        loggedmsg = True
                    self.sleep(20)
                    continue
                loggedmsg = False
                pos = imagesearch(self.enter_world_img)
                if pos[0] != -1:
                    self.logmsg("Enter WoW")
                    # Enter world button is there!
                    click_image(self.enter_world_img, pos, "left", 0.2, offset=5)
                    self.sleep(5)
                    break

            # Ok now we are hopefully in the game !
            self.logmsg("In game!")
            while True:
                with self.state:
                    if self.paused:
                        break
                if not process_exists("World of Warcraft"):
                    self.logmsg("Can't find WoW window.. Restarting")
                    break
                pos = imagesearch(self.wow_img)
                if pos[0] != -1:
                    self.logmsg("Not in game anymore.")
                    # We are not in game anymore..
                    # Checking for Enter World
                    self.logmsg("Checking for Enter World")
                    pos = imagesearch(self.enter_world_img)
                    if pos[0] != -1:
                        # Enter world button is there!
                        self.logmsg("Char select, in again")
                        click_image(self.enter_world_img, pos, "left", 0.2, offset=5)
                        self.logmsg("In game!")
                        continue
                    else:
                        # Checking for reconnect button
                        posreconnect = imagesearch(self.reconnect_img)
                        if posreconnect[0] != -1:
                            # Reconnect button is there!
                            self.logmsg("Reconnect!")
                            pos = imagesearch(self.okay_img)
                            if pos[0] != -1:
                                self.logmsg("Found okay button pressing before reconnect")
                                click_image(self.okay_img, pos, "left", 0.2, offset=5)
                            self.sleep(1)
                            click_image(self.reconnect_img, posreconnect, "left", 0.2, offset=5)
                            # Wait for char select
                            self.logmsg("wait for char select for 90 secs max")
                            pos = imagesearch_numLoop(self.enter_world_img, 1, 90)
                            if pos[0] != -1:
                                click_image(self.enter_world_img, pos, "left", 0.2, offset=5)
                                self.logmsg("In game!")
                                continue
                    self.logmsg("Didn't see any buttons to press .. restart time.")
                    break

                # Randomize recheck to not be consistent bot behaviour
                self.sleep(random.randint(3, 8))

    def sleep(self, secs):
        """
        Sleeps for x seconds, but pause thread if we get stopped.
        """
        for i in range(secs):
            with self.state:
                if self.paused:
                    break
            sleep(1)

    def sleeptime(self, secs):
        """
        Time we wait for Battle.net GUI to render
        """
        self.waittime = secs

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

    def click_play(self):
        """
        Click on the play button.
        """
        while True:
            with self.state:
                if self.paused:
                    break
            button_loc_x = 0
            hwnd = win32gui.FindWindow(None, "Battle.net")
            if hwnd == 0:
                sleep(0.3)
                continue
            try:
                rect = win32gui.GetWindowRect(hwnd)
                x = rect[0]
                y = rect[1]
                w = rect[2] - x
                h = rect[3] - y
                button_loc_x = (x + 100)
                button_loc_y = (y + h - 100)
            except BaseException:
                self.logmsg("Error getting Battle.net window size trying again")
                self.sleep(1)
                continue
            if button_loc_x != 0:
                self.logmsg("Found Battle.net window waiting for gui render for {} secs".format(self.waittime))
                self.sleep(self.waittime)
                break
        self.logmsg("Clicking play button")
        try:
            win32api.SetCursorPos((button_loc_x, button_loc_y))
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, button_loc_x, button_loc_y, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, button_loc_x, button_loc_y, 0, 0)
        except BaseException:
            self.logmsg("Permission error, are you running as administrator?")

    def logmsg(self, msg):
        window.Element('_OUTPUT_').Update("{} {}\n".format(datetime.now().strftime("%H:%M:%S"), msg), append=True)

    def pause(self):
        with self.state:
            self.paused = True  # Block self.

    def resume(self):
        with self.state:
            self.paused = False
            self.state.notify()  # Unblock self if waiting.


def process_exists(title_name):
    """
    Check if a process is running.
    """
    hwnd = win32gui.FindWindow(None, title_name)
    if hwnd == 0:
        return False
    else:
        return True

if __name__ == '__main__':
    main()
