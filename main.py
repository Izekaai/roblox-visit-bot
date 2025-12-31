import random
import subprocess
import sys
import psutil
import time
import datetime
import requests
from PyQt6 import QtWidgets, QtCore


#monkey🤤🤤🤤🤤

class RobloxBotThread(QtCore.QThread):
    log_signal = QtCore.pyqtSignal(str)

    def __init__(self, place_id, wait_time):
        super().__init__()
        self.place_id = place_id
        self.wait_time = wait_time
        self.running = True
        self.cookies = []

        try:
            with open("cookies.txt", "r") as f:
                for line in f:
                    if line.strip():
                        self.cookies.append(line.strip())
        except Exception as e:
            self.send_log(f"cookie load error: {e}")
            self.running = False

        self.send_log(f"cookies loaded: {len(self.cookies)}")

    def send_log(self, msg):
        now = datetime.datetime.utcnow().strftime("%H:%M:%S")
        self.log_signal.emit(f"[{now}] {msg}")

    def get_csrf(self, session):
        r = session.post("https://auth.roblox.com/v2/logout")
        if "x-csrf-token" not in r.headers:
            return None
        return r.headers["x-csrf-token"]

    def get_auth_ticket(self, session):
        r = session.post(
            "https://auth.roblox.com/v1/authentication-ticket/",
            headers={
                "Content-Type": "application/json",
                "referer": f"https://www.roblox.com/games/{self.place_id}"
            },
            json={}
        )
        return r.headers.get("rbx-authentication-ticket")

    def wait_for_roblox(self, timeout=30):
        start = time.time()
        while time.time() - start < timeout:
            for proc in psutil.process_iter(["name"]):
                if proc.info["name"] == "RobloxPlayerBeta.exe":
                    return True
            time.sleep(1)
        return False

    def run(self):
        while self.running:
            try:
                if not self.cookies:
                    self.send_log("no cookies left")
                    break

                cookie = random.choice(self.cookies)
                session = requests.session()
                session.cookies[".ROBLOSECURITY"] = cookie

                csrf = self.get_csrf(session)
                if not csrf:
                    self.send_log("csrf failed")
                    time.sleep(3)
                    continue

                session.headers["x-csrf-token"] = csrf

                ticket = self.get_auth_ticket(session)
                if not ticket:
                    self.send_log("auth ticket failed")
                    time.sleep(3)
                    continue

                browser_id = random.randint(100000, 9999999)
                launch_cmd = (
                    f"start roblox-player:1+launchmode:play+gameinfo:{ticket}"
                    f"+launchtime:{browser_id}"
                    f"+placelauncherurl:https%3A%2F%2Fassetgame.roblox.com%2Fgame%2FPlaceLauncher.ashx"
                    f"%3Frequest%3DRequestGame%26browserTrackerId%3D{browser_id}"
                    f"%26placeId%3D{self.place_id}%26isPlayTogetherGame%3Dfalse"
                    f"+browsertrackerid:{browser_id}"
                )

                subprocess.run(launch_cmd, shell=True)
                self.send_log("roblox launched")

                if not self.wait_for_roblox():
                    self.send_log("roblox did not start")
                    time.sleep(3)
                    continue

                try:
                    u = session.get("https://users.roblox.com/v1/users/authenticated")
                    name = u.json().get("displayName")
                    self.send_log(f"logged in as {name}")
                except Exception as e:
                    self.send_log(f"name fetch error: {e}")

                time.sleep(self.wait_time)

                subprocess.run(
                    "taskkill /IM RobloxPlayerBeta.exe /F",
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                self.send_log("roblox closed")

            except Exception as e:
                self.send_log(f"runtime error: {e}")

            time.sleep(3)

    def stop(self):
        self.running = False


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Roblox Visit Bot")
        self.resize(600, 500)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        form = QtWidgets.QFormLayout()
        self.game_input = QtWidgets.QLineEdit()
        self.time_input = QtWidgets.QSpinBox()
        self.time_input.setRange(1, 3600)
        self.time_input.setValue(20)

        form.addRow("Game ID:", self.game_input)
        form.addRow("Clean Time:", self.time_input)
        layout.addLayout(form)

        btns = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        btns.addWidget(self.start_btn)
        btns.addWidget(self.stop_btn)
        layout.addLayout(btns)

        self.log_box = QtWidgets.QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box)

        self.thread = None
        self.start_btn.clicked.connect(self.start_bot)
        self.stop_btn.clicked.connect(self.stop_bot)

    def start_bot(self):
        if self.thread:
            return

        gid = self.game_input.text().strip()
        if not gid:
            self.log_box.append("enter game id")
            return

        self.thread = RobloxBotThread(gid, self.time_input.value())
        self.thread.log_signal.connect(self.log_box.append)
        self.thread.start()

    def stop_bot(self):
        if self.thread:
            self.thread.stop()
            self.thread.wait()
            self.thread = None


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
