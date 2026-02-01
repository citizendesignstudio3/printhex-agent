import os

class FlexParser:
    """
    Flex Printer Log Parser (Complete Version)
    Updates:
    1. Detects Power On/Off (Start/Stop)
    2. Detects Smart Status (Ready, Busy, Moving, Initializing)
    3. Detects Job Percentage (Printing Progress)
    """

    def parse(self, line: str):

        # ==========================================
        # 1. POWER STATUS (Start / Stop)
        # ==========================================
        # Log: ProceedKernelMessage kParam=Power_On;lParam=1  (Machine Start)
        # Log: ProceedKernelMessage kParam=Power_On;lParam=0  (Machine Stop)
        if "kParam=Power_On" in line:
            try:
                if "lParam=1" in line:
                    return {
                        "event": "POWER_STATUS",
                        "payload": {
                            "status": "ON",
                            "raw_log": line
                        }
                    }
                elif "lParam=0" in line:
                    return {
                        "event": "POWER_STATUS",
                        "payload": {
                            "status": "OFF",
                            "raw_log": line
                        }
                    }
            except Exception:
                pass

        # Log: ==========Status_Change = PowerOff
        if "Status_Change = PowerOff" in line:
            return {
                "event": "POWER_STATUS",
                "payload": {
                    "status": "OFF",
                    "raw_log": line
                }
            }

        # ==========================================
        # 2. SMART STATUS CHANGE (Ready, Busy, Moving, etc.)
        # ==========================================
        # Log: ==========Status_Change = Moving
        # Log: ==========Status_Change = Busy
        # Log: ==========Status_Change = Ready
        if "==========Status_Change =" in line:
            try:
                # "=" ke baad jo bhi status likha h (e.g. "Moving"), use nikal lo
                status_text = line.split("==========Status_Change =")[1].strip()
                
                # Agar status 'PowerOff' hai to use ignore karein (kyunki upar handle ho gaya)
                if status_text.lower() == "poweroff":
                    return None

                return {
                    "event": "MACHINE_STATUS",
                    "payload": {
                        "status": status_text,
                        "raw_log": line
                    }
                }
            except Exception:
                pass

        # ==========================================
        # 3. JOB PERCENTAGE / PROGRESS
        # ==========================================
        # Log: ProceedKernelMessage kParam=Percentage;lParam=25
        if "kParam=Percentage" in line:
            try:
                parts = line.split("lParam=")
                if len(parts) > 1:
                    # 'lParam=25' me se 25 nikalo
                    percent_val = parts[1].split(';')[0].strip()
                    percentage = int(percent_val)
                    
                    return {
                        "event": "JOB_PROGRESS",
                        "payload": {
                            "percentage": percentage,
                            "raw_log": line
                        }
                    }
            except Exception:
                pass

        # ==========================================
        # 4. JOB START (File Name)
        # ==========================================
        # Log: CreatFinished start Printing job=D:\rip file\...\star.prt
        if "start Printing job=" in line:
            try:
                job_path = line.split("start Printing job=")[1].strip()
                return {
                    "event": "JOB_INFO",
                    "payload": {
                        "job_name": os.path.basename(job_path),
                        "status": "Started",
                        "raw_log": line
                    }
                }
            except Exception as e:
                pass

        # ==========================================
        # 5. JOB END / FINISHED
        # ==========================================
        # Log: ProceedKernelMessage kParam=Job_End;lParam=1
        if "Job_End" in line or "Finsh_Printing" in line:
            return {
                "event": "JOB_STATUS",
                "payload": {
                    "status": "Finished",
                    "raw_log": line
                }
            }

        # -------------------------
        # No Match
        # -------------------------
        return None