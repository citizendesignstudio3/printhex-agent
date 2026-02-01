# parsers/SnmpParser.py
import time
from pysnmp.hlapi import *

class SnmpParser:
    """
    Konica Minolta / Universal SNMP Parser
    Retrieves: Status, Counters, Toner Levels (C,M,Y,K), and Device Info.
    """
    def __init__(self, ip_address, community='public'):
        self.ip = ip_address
        self.community = community
        self.last_counter = 0
        self.last_status = "UNKNOWN"

    def fetch_oid(self, oid):
        """Helper to get single value"""
        try:
            iterator = getCmd(SnmpEngine(),
                              CommunityData(self.community, mpModel=1), # SNMP v2c
                              UdpTransportTarget((self.ip, 161), timeout=2, retries=1),
                              ContextData(),
                              ObjectType(ObjectIdentity(oid)))
            errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
            
            if errorIndication or errorStatus: return None
            return varBinds[0][1]
        except:
            return None

    def walk_oid(self, root_oid):
        """Helper to get lists (like Toner Tables)"""
        results = []
        try:
            iterator = nextCmd(SnmpEngine(),
                               CommunityData(self.community, mpModel=1),
                               UdpTransportTarget((self.ip, 161), timeout=2, retries=1),
                               ContextData(),
                               ObjectType(ObjectIdentity(root_oid)),
                               lexicographicMode=False)
            for errorIndication, errorStatus, errorIndex, varBinds in iterator:
                if errorIndication or errorStatus: break
                results.append(varBinds[0][1])
        except:
            pass
        return results

    def parse(self, line=None):
        # Note: SNMP doesn't read 'lines', it polls. This method is called by Agent loop.
        
        data_packet = {
            "event": "FULL_MACHINE_DATA", # Server will store everything
            "payload": {
                "timestamp": time.time(),
                "ip": self.ip
            }
        }

        # 1. GET STATUS (hrDeviceStatus)
        # 2=unknown, 3=running, 4=warning, 5=testing, 1=down
        raw_status = self.fetch_oid('1.3.6.1.2.1.25.3.2.1.5.1') 
        status_map = {1: "OFFLINE", 2: "UNKNOWN", 3: "RUNNING", 4: "WARNING", 5: "TESTING"}
        
        current_status = status_map.get(int(raw_status or 0), "OFFLINE")
        data_packet['payload']['status'] = current_status
        data_packet['payload']['raw_status_code'] = int(raw_status or 0)

        # 2. GET TOTAL COUNTER (Billing Counter)
        # prtMarkerLifeCount
        counter = self.fetch_oid('1.3.6.1.2.1.43.10.2.1.4.1.1')
        if counter:
            current_count = int(counter)
            data_packet['payload']['total_counter'] = current_count
            
            # Logic: If counter increased, it means a job finished
            if self.last_counter > 0 and current_count > self.last_counter:
                diff = current_count - self.last_counter
                data_packet['payload']['job_finished'] = True
                data_packet['payload']['pages_printed'] = diff
            
            self.last_counter = current_count

        # 3. GET TONER LEVELS (Complex Table Walk)
        # We fetch Max Capacity and Current Level to calculate Percentage
        try:
            max_levels = self.walk_oid('1.3.6.1.2.1.43.11.1.1.8.1') # Max
            curr_levels = self.walk_oid('1.3.6.1.2.1.43.11.1.1.9.1') # Current
            colors = ["Black", "Cyan", "Magenta", "Yellow"] # Usually in this order or similar
            
            supplies = {}
            for i in range(len(curr_levels)):
                if i < len(max_levels) and int(max_levels[i]) > 0:
                    pct = int((int(curr_levels[i]) / int(max_levels[i])) * 100)
                    # Generic naming (Supply 1, Supply 2...) or mapped if known
                    name = colors[i] if i < 4 else f"Supply_{i+1}"
                    supplies[name] = pct
            
            data_packet['payload']['supplies'] = supplies
        except:
            data_packet['payload']['supplies'] = {}

        # Return Logic
        events = []
        
        # A. Send Full Dump (Server decides what to keep)
        events.append(data_packet)

        # B. If Status Changed -> Send Specific Event for UI update
        if current_status != self.last_status:
            events.append({
                "event": "MACHINE_STATUS",
                "payload": { "status": current_status }
            })
            self.last_status = current_status

        # C. If Supplies Found -> Send Supply Event
        if data_packet['payload'].get('supplies'):
             events.append({
                "event": "SUPPLY_LEVELS",
                "payload": data_packet['payload']['supplies']
            })

        # D. If Job Finished -> Send Job Event
        if data_packet['payload'].get('job_finished'):
             events.append({
                "event": "JOB_STATUS",
                "payload": { 
                    "status": "Finished", 
                    "pages_printed": data_packet['payload']['pages_printed'] 
                }
            })

        return events # Return list of events