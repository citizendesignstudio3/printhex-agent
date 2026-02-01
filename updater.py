import os
import time
import requests
import subprocess
import sys

UPDATE_URL = "https://python.printhex.in/api/agent/latest"

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
            exe_url = r.get("exe_url")

            # ✅ Update available
            if latest and latest != VERSION:
                print("✅ Update found:", latest)

                new_file = current_exe + ".new"

                # Download new exe
                data = requests.get(exe_url, timeout=20).content
                with open(new_file, "wb") as f:
                    f.write(data)

                print("✅ New version downloaded")

                # ✅ Create update script
                bat_path = os.path.join(os.path.dirname(current_exe), "update.bat")

                with open(bat_path, "w") as bat:
                    bat.write(f"""
@echo off
timeout /t 2 /nobreak >nul

del "{current_exe}"
rename "{new_file}" "{os.path.basename(current_exe)}"

start "" "{current_exe}"
del "%~f0"
""")

                # ✅ Run updater script and exit
                subprocess.Popen(
                    ["cmd", "/c", bat_path],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )

                os._exit(0)

        except Exception as e:
            print("Updater error:", e)

        # ✅ Check every 5 minutes
        time.sleep(300)
