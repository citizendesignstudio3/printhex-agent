import os
import time
import requests
import subprocess
import sys

UPDATE_URL = "https://python.printhex.in/api/agent/latest"

# ✅ Update Check Interval (Fast)
CHECK_INTERVAL = 300   # 5 min (change to 60 for 1 min)

def check_update_loop():
    while True:
        try:
            # ✅ Current running exe
            current_exe = sys.executable

            # ✅ Current version
            from version import VERSION

            # ✅ Server response
            r = requests.get(UPDATE_URL, timeout=5).json()

            latest = r.get("version")

            # ✅ Now server should return installer URL
            installer_url = r.get("installer_url")

            # ----------------------------
            # ✅ Update Available
            # ----------------------------
            if latest and latest != VERSION:
                print("✅ Update found:", latest)

                # ✅ Download installer into TEMP
                installer_file = os.path.join(
                    os.getenv("TEMP"),
                    f"PrintHexAgentSetup_{latest}.exe"
                )

                print("⬇ Downloading installer...")

                data = requests.get(installer_url, timeout=60).content
                with open(installer_file, "wb") as f:
                    f.write(data)

                print("✅ Installer downloaded:", installer_file)

                # ----------------------------
                # ✅ Run Silent Installer Update
                # ----------------------------
                print("⚙ Running silent upgrade...")

                subprocess.Popen([
                    installer_file,
                    "/VERYSILENT",
                    "/SUPPRESSMSGBOXES",
                    "/NORESTART"
                ])

                # ✅ Exit current agent (installer will replace files)
                os._exit(0)

        except Exception as e:
            print("Updater error:", e)

        # ✅ Check every 1 minutes
        time.sleep(60)
