#!/usr/bin/env python
"""
SPRSUN-Modbus Heat Pump. The Python plugin for Domoticz
Original Author: Sateetje

Works with SPRSUN HeatPump CGK0x0V2.

Requirements:
    1.python module pymodbus -> https://pymodbus.readthedocs.io
        (pi@raspberrypi:~$ sudo pip3 install pymodbus)
    2.Communication module Modbus USB to RS485 or Modbus TCP to RS485
        tested with ZLAN 5143D using RTU-over-TCP
"""
"""
<plugin key="SPRSUN" name="SPRSUN-Modbus" version="2" author="Sateetje">
    <params>
        <param field="SerialPort" label="Modbus Port" width="200px" required="false" default="/dev/ttyUSB0" />
        <param field="Address" label="IP Address" width="200px" required="false" default="127.0.0.1" />
        <param field="Port" label="TCP Port" width="200px" required="false" default="4196" />
        <param field="Mode1" label="Baud rate" width="40px" required="false" default="19200" />
        <param field="Mode2" label="Device ID" width="40px" required="true" default="1" />
        <param field="Mode3" label="Method" width="120px">
            <options>
                <option label="RTU-Serial" value="serial"/>
                <option label="RTU-TCP" value="tcp"  default="true" />
                <option label="RTU-UDP" value="udp" />
            </options>
        </param>
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>
    </params>
</plugin>

"""

import Domoticz                          #tested on Python 3.9.2 in Domoticz 2023.2
import pymodbus.client as ModbusClient   #tested with 3.6.2
import time
from pymodbus import ExceptionResponse,Framer,ModbusException,pymodbus_apply_logging_config
from pymodbus.payload import BinaryPayloadDecoder,BinaryPayloadBuilder
from pymodbus.constants import Endian

class SettingToWrite:
    def __init__(self, register, value, decimalPlaces, isBit):
        self.register = register
        self.value = value
        self.decimalPlaces = decimalPlaces
        self.isBit = isBit

class BasePlugin:
    def __init__(self):
        self.runInterval = 1
        self.settingsToWrite = []
        return

    def onStart(self):
        devicecreated = []
        Domoticz.Log("SPRSUN-Modbus plugin start")
        self.runInterval = 1

        #https://github.com/domoticz/domoticz/blob/master/hardware/hardwaretypes.h
        if 1 not in Devices:
            Domoticz.Device(Name="Return water temperature",Unit=1,Type=80,Subtype=5,Used=1).Create()
        if 2 not in Devices:
            Domoticz.Device(Name="Outlet temperature",Unit=2,Type=80,Subtype=5,Used=1).Create()
        if 3 not in Devices:
            Domoticz.Device(Name="Ambient temperature",Unit=3,Type=80,Subtype=5,Used=1).Create()
        if 4 not in Devices:
            Domoticz.Device(Name="Hot water temperature",Unit=4,Type=80,Subtype=5,Used=1).Create()
        if 5 not in Devices:
            Domoticz.Device(Name="Unit on",Unit=5,Type=244,Subtype=73,Switchtype=0,Image=9,Used=1).Create()
        if 6 not in Devices:
            Domoticz.Device(Name="Fan output",Unit=6,Type=243,Subtype=6,Used=0).Create()
        if 7 not in Devices:
            Domoticz.Device(Name="Pump output",Unit=7,Type=243,Subtype=6,Used=0).Create()
        if 8 not in Devices:
            Domoticz.Device(Name="Required cap",Unit=8,Type=243,Subtype=6,Used=1).Create()
        if 9 not in Devices:
            Domoticz.Device(Name="Actual cap",Unit=9,Type=243,Subtype=6,Used=1).Create()
        if 10 not in Devices:
            Domoticz.Device(Name="BLDC Motor power",Unit=10,Type=248,Subtype=1,Used=0).Create()
        if 11 not in Devices:
            Domoticz.Device(Name="BLDC Motor voltage",Unit=11,Type=243,Subtype=8,Used=0).Create()
        if 12 not in Devices:
            Domoticz.Device(Name="BLDC Motor current",Unit=12,Type=243,Subtype=23,Used=0).Create()
        Options={}
        #can be used after release 2023.02: Options={'ValueStep':'0.5';' ValueMin':'10.0';'ValueMax':'55.0';'ValueUnit':'°C';}
        if 13 not in Devices:
            Domoticz.Device(Name="Setpoint hot water",Unit=13,Type=242,Subtype=1,Options=Options,Used=1).Create()
        Options={}
        #can be used after release 2023.02: Options={'ValueStep':'0.5';' ValueMin':'10.0';'ValueMax':'55.0';'ValueUnit':'°C';}
        if 14 not in Devices:
            Domoticz.Device(Name="Setpoint heating",Unit=14,Type=242,Subtype=1,Options=Options,Used=1).Create()
        Options = {"LevelActions": "|| ||", "LevelNames": "Off|Cooling|Heating|Hot Water|Hot Water + Cooling|Hot Water + Heating", "LevelOffHidden": "true", "SelectorStyle": "1"}
        if 15 not in Devices:
            Domoticz.Device(Name="Mode",Unit=15,TypeName="Selector Switch",Options=Options,Image=15,Used=1).Create()
        if 16 not in Devices:
            Domoticz.Device(Name="Status",Unit=16,Type=243,Subtype=19,Used=1).Create()
        if 17 not in Devices:
            Domoticz.Device(Name="Three-way valve",Unit=17,Type=244,Subtype=73,Switchtype=0,Used=0).Create()
        if 18 not in Devices:
            Domoticz.Device(Name="Heater",Unit=18,Type=244,Subtype=73,Switchtype=0,Image=15,Used=0).Create()
        if 19 not in Devices:
            Domoticz.Device(Name="AC Linkage",Unit=19,Type=244,Subtype=73,Switchtype=2,Used=0).Create()
        Options = {"LevelActions": "|| ||", "LevelNames": "Off|Daytime|Night|Eco|Pressure", "LevelOffHidden": "true", "SelectorStyle": "1"}
        if 20 not in Devices:
            Domoticz.Device(Name="Fan mode",Unit=20,TypeName="Selector Switch",Options=Options,Image=7,Used=1).Create()
        Options={}
        #can be used after release 2023.02: Options={'ValueStep':'0.5';' ValueMin':'1.0';'ValueMax':'15.0';'ValueUnit':'°C';}
        if 21 not in Devices:
            Domoticz.Device(Name="Temp diff hot water",Unit=21,Type=242,Subtype=1,Options=Options,Used=0).Create()
        Options={}
        #can be used after release 2023.02: Options={'ValueStep':'0.5';' ValueMin':'1.0';'ValueMax':'15.0';'ValueUnit':'°C';}
        if 22 not in Devices:
            Domoticz.Device(Name="Temp diff cooling/heating",Unit=22,Type=242,Subtype=1,Options=Options,Used=0).Create()
        if 23 not in Devices:
            Domoticz.Device(Name="Eco mode cooling X1",Unit=23,Type=80,Subtype=5,Used=0).Create()
        if 24 not in Devices:
            Domoticz.Device(Name="Eco mode cooling X2",Unit=24,Type=80,Subtype=5,Used=0).Create()
        if 25 not in Devices:
            Domoticz.Device(Name="Eco mode cooling X3",Unit=25,Type=80,Subtype=5,Used=0).Create()
        if 26 not in Devices:
            Domoticz.Device(Name="Eco mode cooling X4",Unit=26,Type=80,Subtype=5,Used=0).Create()
        if 27 not in Devices:
            Domoticz.Device(Name="Eco mode cooling Y1",Unit=27,Type=80,Subtype=5,Used=0).Create()
        if 28 not in Devices:
            Domoticz.Device(Name="Eco mode cooling Y2",Unit=28,Type=80,Subtype=5,Used=0).Create()
        if 29 not in Devices:
            Domoticz.Device(Name="Eco mode cooling Y3",Unit=29,Type=80,Subtype=5,Used=0).Create()
        if 30 not in Devices:
            Domoticz.Device(Name="Eco mode cooling Y4",Unit=30,Type=80,Subtype=5,Used=0).Create()
        if 31 not in Devices:
            Domoticz.Device(Name="Eco mode heating X1",Unit=31,Type=80,Subtype=5,Used=0).Create()
        if 32 not in Devices:
            Domoticz.Device(Name="Eco mode heating X2",Unit=32,Type=80,Subtype=5,Used=0).Create()
        if 33 not in Devices:
            Domoticz.Device(Name="Eco mode heating X3",Unit=33,Type=80,Subtype=5,Used=0).Create()
        if 34 not in Devices:
            Domoticz.Device(Name="Eco mode heating X4",Unit=34,Type=80,Subtype=5,Used=0).Create()
        if 35 not in Devices:
            Domoticz.Device(Name="Eco mode heating Y1",Unit=35,Type=80,Subtype=5,Used=0).Create()
        if 36 not in Devices:
            Domoticz.Device(Name="Eco mode heating Y2",Unit=36,Type=80,Subtype=5,Used=0).Create()
        if 37 not in Devices:
            Domoticz.Device(Name="Eco mode heating Y3",Unit=37,Type=80,Subtype=5,Used=0).Create()
        if 38 not in Devices:
            Domoticz.Device(Name="Eco mode heating Y4",Unit=38,Type=80,Subtype=5,Used=0).Create()
        if 39 not in Devices:
            Domoticz.Device(Name="Eco mode hot water X1",Unit=39,Type=80,Subtype=5,Used=0).Create()
        if 40 not in Devices:
            Domoticz.Device(Name="Eco mode hot water X2",Unit=40,Type=80,Subtype=5,Used=0).Create()
        if 41 not in Devices:
            Domoticz.Device(Name="Eco mode hot water X3",Unit=41,Type=80,Subtype=5,Used=0).Create()
        if 42 not in Devices:
            Domoticz.Device(Name="Eco mode hot water X4",Unit=42,Type=80,Subtype=5,Used=0).Create()
        if 43 not in Devices:
            Domoticz.Device(Name="Eco mode hot water Y1",Unit=43,Type=80,Subtype=5,Used=0).Create()
        if 44 not in Devices:
            Domoticz.Device(Name="Eco mode hot water Y2",Unit=44,Type=80,Subtype=5,Used=0).Create()
        if 45 not in Devices:
            Domoticz.Device(Name="Eco mode hot water Y3",Unit=45,Type=80,Subtype=5,Used=0).Create()
        if 46 not in Devices:
            Domoticz.Device(Name="Eco mode hot water Y4",Unit=46,Type=80,Subtype=5,Used=0).Create()
        if 47 not in Devices:
            Domoticz.Device(Name="Setpoint cooling eco mode",Unit=47,Type=80,Subtype=5,Used=1).Create()
        if 48 not in Devices:
            Domoticz.Device(Name="Setpoint heating eco mode",Unit=48,Type=80,Subtype=5,Used=1).Create()
        if 49 not in Devices:
            Domoticz.Device(Name="Setpoint hot water eco mode",Unit=49,Type=80,Subtype=5,Used=1).Create()
        Options={}
        #can be used after release 2023.02: Options={'ValueStep':'0.5';' ValueMin':'5.0';'ValueMax':'40.0';'ValueUnit':'°C';}
        if 50 not in Devices:
            Domoticz.Device(Name="Setpoint cooling",Unit=50,Type=242,Subtype=1,Options=Options,Used=1).Create()
        Options = {"LevelActions": "|| ||", "LevelNames": "Off|Normal|Demand|Interval", "LevelOffHidden": "true", "SelectorStyle": "1"}
        if 51 not in Devices:
            Domoticz.Device(Name="Pump mode",Unit=51,TypeName="Selector Switch",Options=Options,Image=11,Used=1).Create()
    def onStop(self):
        Domoticz.Log("SPRSUN-Modbus plugin stop")

    def onHeartbeat(self):
        self.runInterval -=1;
        if self.runInterval <= 0:
            PV_Return_Water_Temperature = 0 #  Declare these to keep the debug section at the bottom from complaining.
            PV_Outlet_Temperature = 0
            PV_Ambient_Temperature = 0
            PV_Hot_Water_Temperature = 0
            Unit_On = 0
            PV_Fan_Output = 0
            PV_Pump_Output = 0
            PV_Required_Cap = 0
            PV_Actual_Cap = 0
            PV_Power = 0
            PV_Voltage = 0
            PV_Current = 0
            SP_Hot_Water = 0
            SP_Heating = 0
            Mode = 0
            Status = 0
            StatusText = "Unknown"
            ThreeWayValve = 0
            Heater = 0
            AC_Linkage = 0
            Fan_Mode = 0
            SP_TempDiff_Hot_Water = 0
            SP_TempDiff_Cooling_Heating = 0
            Eco_Mode_Cooling_X1 = 0
            Eco_Mode_Cooling_X2 = 0
            Eco_Mode_Cooling_X3 = 0
            Eco_Mode_Cooling_X4 = 0
            Eco_Mode_Cooling_Y1 = 0
            Eco_Mode_Cooling_Y2 = 0
            Eco_Mode_Cooling_Y3 = 0
            Eco_Mode_Cooling_Y4 = 0
            Eco_Mode_Heating_X1 = 0
            Eco_Mode_Heating_X2 = 0
            Eco_Mode_Heating_X3 = 0
            Eco_Mode_Heating_X4 = 0
            Eco_Mode_Heating_Y1 = 0
            Eco_Mode_Heating_Y2 = 0
            Eco_Mode_Heating_Y3 = 0
            Eco_Mode_Heating_Y4 = 0
            Eco_Mode_Hot_Water_X1 = 0
            Eco_Mode_Hot_Water_X2 = 0
            Eco_Mode_Hot_Water_X3 = 0
            Eco_Mode_Hot_Water_X4 = 0
            Eco_Mode_Hot_Water_Y1 = 0
            Eco_Mode_Hot_Water_Y2 = 0
            Eco_Mode_Hot_Water_Y3 = 0
            Eco_Mode_Hot_Water_Y4 = 0
            SP_Cooling_Eco_Mode = 0
            SP_Heating_Eco_Mode = 0
            SP_Hot_Water_Eco_Mode = 0
            SP_Cooling = 0
            Pump_Mode = 0

            # Get data from SPRSUN
            if Parameters["Mode6"] == 'Debug':
                pymodbus_apply_logging_config("DEBUG")

            comm = Parameters["Mode3"]
            hostAddress = Parameters["Address"]
            port = int(Parameters["Port"])
            serialPort = Parameters["SerialPort"]
            baudrate = int(Parameters["Mode1"])
            deviceID = int(Parameters["Mode2"])

            try:
                if comm == "tcp":
                    client = ModbusClient.ModbusTcpClient(
                        host=hostAddress,
                        port=port,
                        framer=Framer.RTU,
                        # timeout=10,
                        # retries=3,
                        # retry_on_empty=False,y
                        # close_comm_on_error=False,
                        # strict=True,
                        # source_address=("localhost", 0),
                    )
                elif comm == "udp":
                    client = ModbusClient.ModbusUdpClient(
                        host=hostAddress,
                        port=port,
                        framer=Framer.RTU,
                        # timeout=10,
                        # retries=3,
                        # retry_on_empty=False,
                        # close_comm_on_error=False,
                        # strict=True,
                        # source_address=None,
                    )
                elif comm == "serial":
                    client = ModbusClient.ModbusSerialClient(
                        port=serialPort,
                        framer=Framer.RTU,
                        # timeout=10,
                        # retries=3,
                        # retry_on_empty=False,
                        # close_comm_on_error=False,.
                        # strict=True,
                        baudrate=baudrate,
                        bytesize=8,
                        parity="N",
                        stopbits=1,
                        # handle_local_echo=False,
                    )
                else:  # pragma no cover
                    print(f"Unknown client {comm} selected")
                    return

                client.connect()

                # To avoid this error message: AttributeError: 'ModbusIOException' object has no attribute 'registers'
                time.sleep(1)

                # Write settings first
                for setting in self.settingsToWrite:
                    Domoticz.Log('Writing to register {0} with value {1}'.format(setting.register,setting.value))
                    if setting.isBit == True:
                        self.writeToModbus(client,deviceID,5,setting.register,setting.value,0)
                    else:
                        self.writeToModbus(client,deviceID,6,setting.register,setting.value,setting.decimalPlaces)

                self.settingsToWrite.clear()

                PV_Return_Water_Temperature = self.readFromModbus(client, deviceID, 3, 188, 1)
                PV_Outlet_Temperature = self.readFromModbus(client, deviceID, 3, 189, 1)
                PV_Ambient_Temperature = self.readFromModbus(client, deviceID, 3, 190, 1)
                PV_Hot_Water_Temperature = self.readFromModbus(client, deviceID, 3, 195, 1)
                Unit_On = self.readFromModbus(client, deviceID, 1, 40, 0)
                PV_Fan_Output = self.readFromModbus(client, deviceID, 3, 197, 1)
                PV_Pump_Output = self.readFromModbus(client, deviceID, 3, 198, 1)
                PV_Required_Cap = self.readFromModbus(client, deviceID, 3, 203, 1)
                PV_Actual_Cap = self.readFromModbus(client, deviceID, 3, 204, 1)
                PV_Power = self.readFromModbus(client, deviceID, 3, 333, 1) * 1000 #kW to W
                PV_Voltage = self.readFromModbus(client, deviceID, 3, 334, 0)
                PV_Current = self.readFromModbus(client, deviceID, 3, 335, 1)
                SP_Hot_Water = self.readFromModbus(client, deviceID, 3, 3, 1)
                SP_Heating = self.readFromModbus(client, deviceID, 3, 1, 1)
                Mode = self.readFromModbus(client, deviceID, 3, 0, 0)
                Status = self.readFromModbus(client, deviceID, 3, 217, 0)
                ThreeWayValve = self.readFromModbus(client, deviceID, 2, 11, 0)
                Heater = self.readFromModbus(client, deviceID, 2, 12, 0)
                AC_Linkage = self.readFromModbus(client, deviceID, 2, 3, 0)
                Fan_Mode = self.readFromModbus(client, deviceID, 3, 12, 0)
                SP_TempDiff_Hot_Water = self.readFromModbus(client, deviceID, 3, 4, 1)
                SP_TempDiff_Cooling_Heating = self.readFromModbus(client, deviceID, 3, 6, 1)
                Eco_Mode_Cooling_X1 = self.readFromModbus(client, deviceID, 3, 276, 1)
                Eco_Mode_Cooling_X2 = self.readFromModbus(client, deviceID, 3, 277, 1)
                Eco_Mode_Cooling_X3 = self.readFromModbus(client, deviceID, 3, 278, 1)
                Eco_Mode_Cooling_X4 = self.readFromModbus(client, deviceID, 3, 279, 1)
                Eco_Mode_Cooling_Y1 = self.readFromModbus(client, deviceID, 3, 336, 1)
                Eco_Mode_Cooling_Y2 = self.readFromModbus(client, deviceID, 3, 288, 1)
                Eco_Mode_Cooling_Y3 = self.readFromModbus(client, deviceID, 3, 289, 1)
                Eco_Mode_Cooling_Y4 = self.readFromModbus(client, deviceID, 3, 290, 1)
                Eco_Mode_Heating_X1 = self.readFromModbus(client, deviceID, 3, 280, 1)
                Eco_Mode_Heating_X2 = self.readFromModbus(client, deviceID, 3, 281, 1)
                Eco_Mode_Heating_X3 = self.readFromModbus(client, deviceID, 3, 282, 1)
                Eco_Mode_Heating_X4 = self.readFromModbus(client, deviceID, 3, 283, 1)
                Eco_Mode_Heating_Y1 = self.readFromModbus(client, deviceID, 3, 291, 1)
                Eco_Mode_Heating_Y2 = self.readFromModbus(client, deviceID, 3, 292, 1)
                Eco_Mode_Heating_Y3 = self.readFromModbus(client, deviceID, 3, 293, 1)
                Eco_Mode_Heating_Y4 = self.readFromModbus(client, deviceID, 3, 337, 1)
                Eco_Mode_Hot_Water_X1 = self.readFromModbus(client, deviceID, 3, 284, 1)
                Eco_Mode_Hot_Water_X2 = self.readFromModbus(client, deviceID, 3, 285, 1)
                Eco_Mode_Hot_Water_X3 = self.readFromModbus(client, deviceID, 3, 286, 1)
                Eco_Mode_Hot_Water_X4 = self.readFromModbus(client, deviceID, 3, 287, 1)
                Eco_Mode_Hot_Water_Y1 = self.readFromModbus(client, deviceID, 3, 294, 1)
                Eco_Mode_Hot_Water_Y2 = self.readFromModbus(client, deviceID, 3, 295, 1)
                Eco_Mode_Hot_Water_Y3 = self.readFromModbus(client, deviceID, 3, 296, 1)
                Eco_Mode_Hot_Water_Y4 = self.readFromModbus(client, deviceID, 3, 338, 1)
                SP_Cooling = self.readFromModbus(client, deviceID, 3, 2, 1)
                Pump_Mode = self.readFromModbus(client, deviceID, 3, 11, 0)

                client.close()

                #Convert State to Text
                if Status == 0:
                    StatusText = "Unit not Ready"
                elif Status == 1:
                    StatusText = "Unit ON"
                elif Status == 2:
                    StatusText = "OFF by Alarm"
                elif Status == 3:
                    StatusText = "OFF by Timezone"
                elif Status == 4:
                    StatusText = "OFF by SuperV"
                elif Status == 5:
                    StatusText = "OFF by Linkage"
                elif Status == 6:
                    StatusText = "OFF by Keyboad"
                elif Status == 7:
                    StatusText = "Manual Mode"
                elif Status == 8:
                    StatusText = "Anti Freeze"
                elif Status == 9:
                    StatusText = "OFF by AC Linkage"
                elif Status == 10:
                    StatusText = "OFF by Change"
                else:
                    StatusText == "Unknown"

                #Calculate setpoint for eco mode interpolate
                #Cooling:
                if PV_Ambient_Temperature <= Eco_Mode_Cooling_X1:
                    SP_Cooling_Eco_Mode = Eco_Mode_Cooling_Y1
                elif PV_Ambient_Temperature <= Eco_Mode_Cooling_X2:
                    StepValue = (Eco_Mode_Cooling_Y2 - Eco_Mode_Cooling_Y1) / (Eco_Mode_Cooling_X2 - Eco_Mode_Cooling_X1)
                    Steps = PV_Ambient_Temperature - Eco_Mode_Cooling_X1
                    SP_Cooling_Eco_Mode = Eco_Mode_Cooling_Y1 + (Steps * StepValue)
                elif PV_Ambient_Temperature <= Eco_Mode_Cooling_X3:
                    StepValue = (Eco_Mode_Cooling_Y3 - Eco_Mode_Cooling_Y2) / (Eco_Mode_Cooling_X3 - Eco_Mode_Cooling_X2)
                    Steps = PV_Ambient_Temperature - Eco_Mode_Cooling_X2
                    SP_Cooling_Eco_Mode = Eco_Mode_Cooling_Y2 + (Steps * StepValue)
                elif PV_Ambient_Temperature <= Eco_Mode_Cooling_X4:
                    StepValue = (Eco_Mode_Cooling_Y4 - Eco_Mode_Cooling_Y3) / (Eco_Mode_Cooling_X4 - Eco_Mode_Cooling_X3)
                    Steps = PV_Ambient_Temperature - Eco_Mode_Cooling_X3
                    SP_Cooling_Eco_Mode = Eco_Mode_Cooling_Y3 + (Steps * StepValue)
                else:
                    SP_Cooling_Eco_Mode = Eco_Mode_Cooling_Y4
                SP_Cooling_Eco_Mode = round(SP_Cooling_Eco_Mode, 1)

                #Heating:
                if PV_Ambient_Temperature <= Eco_Mode_Heating_X1:
                    SP_Heating_Eco_Mode = Eco_Mode_Heating_Y1
                elif PV_Ambient_Temperature <= Eco_Mode_Heating_X2:
                    StepValue = (Eco_Mode_Heating_Y2 - Eco_Mode_Heating_Y1) / (Eco_Mode_Heating_X2 - Eco_Mode_Heating_X1)
                    Steps = PV_Ambient_Temperature - Eco_Mode_Heating_X1
                    SP_Heating_Eco_Mode = Eco_Mode_Heating_Y1 + (Steps * StepValue)
                elif PV_Ambient_Temperature <= Eco_Mode_Heating_X3:
                    StepValue = (Eco_Mode_Heating_Y3 - Eco_Mode_Heating_Y2) / (Eco_Mode_Heating_X3 - Eco_Mode_Heating_X2)
                    Steps = PV_Ambient_Temperature - Eco_Mode_Heating_X2
                    SP_Heating_Eco_Mode = Eco_Mode_Heating_Y2 + (Steps * StepValue)
                elif PV_Ambient_Temperature <= Eco_Mode_Heating_X4:
                    StepValue = (Eco_Mode_Heating_Y4 - Eco_Mode_Heating_Y3) / (Eco_Mode_Heating_X4 - Eco_Mode_Heating_X3)
                    Steps = PV_Ambient_Temperature - Eco_Mode_Heating_X3
                    SP_Heating_Eco_Mode = Eco_Mode_Heating_Y3 + (Steps * StepValue)
                else:
                    SP_Heating_Eco_Mode = Eco_Mode_Heating_Y4
                SP_Heating_Eco_Mode = round(SP_Heating_Eco_Mode, 1)

                #Hot_Water:
                if PV_Ambient_Temperature <= Eco_Mode_Hot_Water_X1:
                    SP_Hot_Water_Eco_Mode = Eco_Mode_Hot_Water_Y1
                elif PV_Ambient_Temperature <= Eco_Mode_Hot_Water_X2:
                    StepValue = (Eco_Mode_Hot_Water_Y2 - Eco_Mode_Hot_Water_Y1) / (Eco_Mode_Hot_Water_X2 - Eco_Mode_Hot_Water_X1)
                    Steps = PV_Ambient_Temperature - Eco_Mode_Hot_Water_X1
                    SP_Hot_Water_Eco_Mode = Eco_Mode_Hot_Water_Y1 + (Steps * StepValue)
                elif PV_Ambient_Temperature <= Eco_Mode_Hot_Water_X3:
                    StepValue = (Eco_Mode_Hot_Water_Y3 - Eco_Mode_Hot_Water_Y2) / (Eco_Mode_Hot_Water_X3 - Eco_Mode_Hot_Water_X2)
                    Steps = PV_Ambient_Temperature - Eco_Mode_Hot_Water_X2
                    SP_Hot_Water_Eco_Mode = Eco_Mode_Hot_Water_Y2 + (Steps * StepValue)
                elif PV_Ambient_Temperature <= Eco_Mode_Hot_Water_X4:
                    StepValue = (Eco_Mode_Hot_Water_Y4 - Eco_Mode_Hot_Water_Y3) / (Eco_Mode_Hot_Water_X4 - Eco_Mode_Hot_Water_X3)
                    Steps = PV_Ambient_Temperature - Eco_Mode_Hot_Water_X3
                    SP_Hot_Water_Eco_Mode = Eco_Mode_Hot_Water_Y3 + (Steps * StepValue)
                else:
                    SP_Hot_Water_Eco_Mode = Eco_Mode_Hot_Water_Y4
                SP_Hot_Water_Eco_Mode = round(SP_Hot_Water_Eco_Mode, 1)

            except Exception as err:
                Domoticz.Log(f"Unexpected {err=}, {type(err)=}")
                Domoticz.Heartbeat(1)   # set Heartbeat to 1 second to get us back here for quick retry.
                self.runInterval = 1    # call again in 1 second
            else:
                #Update devices
                Devices[1].Update(0,str(PV_Return_Water_Temperature))
                Devices[2].Update(0,str(PV_Outlet_Temperature))
                Devices[3].Update(0,str(PV_Ambient_Temperature))
                Devices[4].Update(0,str(PV_Hot_Water_Temperature))
                Devices[5].Update(Unit_On,"")
                Devices[6].Update(0,str(PV_Fan_Output))
                Devices[7].Update(0,str(PV_Pump_Output))
                Devices[8].Update(0,str(PV_Required_Cap))
                Devices[9].Update(0,str(PV_Actual_Cap))
                Devices[10].Update(0,str(PV_Power))
                Devices[11].Update(0,str(PV_Voltage))
                Devices[12].Update(0,str(PV_Current))
                Devices[13].Update(nValue=int(SP_Hot_Water),sValue=str(SP_Hot_Water))
                Devices[14].Update(nValue=int(SP_Heating),sValue=str(SP_Heating))
                Devices[15].Update(nValue=int((Mode+1)*10),sValue=str((Mode+1)*10))
                Devices[16].Update(0,StatusText)
                Devices[17].Update(ThreeWayValve,"")
                Devices[18].Update(Heater,"")
                Devices[19].Update(AC_Linkage,"")
                Devices[20].Update(nValue=int((Fan_Mode+1)*10),sValue=str((Fan_Mode+1)*10))
                Devices[21].Update(nValue=int(SP_TempDiff_Hot_Water),sValue=str(SP_TempDiff_Hot_Water))
                Devices[22].Update(nValue=int(SP_TempDiff_Cooling_Heating),sValue=str(SP_TempDiff_Cooling_Heating))
                Devices[23].Update(nValue=int(Eco_Mode_Cooling_X1),sValue=str(Eco_Mode_Cooling_X1))
                Devices[24].Update(nValue=int(Eco_Mode_Cooling_X2),sValue=str(Eco_Mode_Cooling_X2))
                Devices[25].Update(nValue=int(Eco_Mode_Cooling_X3),sValue=str(Eco_Mode_Cooling_X3))
                Devices[26].Update(nValue=int(Eco_Mode_Cooling_X4),sValue=str(Eco_Mode_Cooling_X4))
                Devices[27].Update(nValue=int(Eco_Mode_Cooling_Y1),sValue=str(Eco_Mode_Cooling_Y1))
                Devices[28].Update(nValue=int(Eco_Mode_Cooling_Y2),sValue=str(Eco_Mode_Cooling_Y2))
                Devices[29].Update(nValue=int(Eco_Mode_Cooling_Y3),sValue=str(Eco_Mode_Cooling_Y3))
                Devices[30].Update(nValue=int(Eco_Mode_Cooling_Y4),sValue=str(Eco_Mode_Cooling_Y4))
                Devices[31].Update(nValue=int(Eco_Mode_Heating_X1),sValue=str(Eco_Mode_Heating_X1))
                Devices[32].Update(nValue=int(Eco_Mode_Heating_X2),sValue=str(Eco_Mode_Heating_X2))
                Devices[33].Update(nValue=int(Eco_Mode_Heating_X3),sValue=str(Eco_Mode_Heating_X3))
                Devices[34].Update(nValue=int(Eco_Mode_Heating_X4),sValue=str(Eco_Mode_Heating_X4))
                Devices[35].Update(nValue=int(Eco_Mode_Heating_Y1),sValue=str(Eco_Mode_Heating_Y1))
                Devices[36].Update(nValue=int(Eco_Mode_Heating_Y2),sValue=str(Eco_Mode_Heating_Y2))
                Devices[37].Update(nValue=int(Eco_Mode_Heating_Y3),sValue=str(Eco_Mode_Heating_Y3))
                Devices[38].Update(nValue=int(Eco_Mode_Heating_Y4),sValue=str(Eco_Mode_Heating_Y4))
                Devices[39].Update(nValue=int(Eco_Mode_Hot_Water_X1),sValue=str(Eco_Mode_Hot_Water_X1))
                Devices[40].Update(nValue=int(Eco_Mode_Hot_Water_X2),sValue=str(Eco_Mode_Hot_Water_X2))
                Devices[41].Update(nValue=int(Eco_Mode_Hot_Water_X3),sValue=str(Eco_Mode_Hot_Water_X3))
                Devices[42].Update(nValue=int(Eco_Mode_Hot_Water_X4),sValue=str(Eco_Mode_Hot_Water_X4))
                Devices[43].Update(nValue=int(Eco_Mode_Hot_Water_Y1),sValue=str(Eco_Mode_Hot_Water_Y1))
                Devices[44].Update(nValue=int(Eco_Mode_Hot_Water_Y2),sValue=str(Eco_Mode_Hot_Water_Y2))
                Devices[45].Update(nValue=int(Eco_Mode_Hot_Water_Y3),sValue=str(Eco_Mode_Hot_Water_Y3))
                Devices[46].Update(nValue=int(Eco_Mode_Hot_Water_Y4),sValue=str(Eco_Mode_Hot_Water_Y4))
                Devices[47].Update(nValue=int(SP_Cooling_Eco_Mode),sValue=str(SP_Cooling_Eco_Mode))
                Devices[48].Update(nValue=int(SP_Heating_Eco_Mode),sValue=str(SP_Heating_Eco_Mode))
                Devices[49].Update(nValue=int(SP_Hot_Water_Eco_Mode),sValue=str(SP_Hot_Water_Eco_Mode))
                Devices[50].Update(nValue=int(SP_Cooling),sValue=str(SP_Cooling))
                Devices[51].Update(nValue=int((Pump_Mode+1)*10),sValue=str((Pump_Mode+1)*10))

                self.runInterval = 1    # Success so call again in 1x10 seconds.
                Domoticz.Heartbeat(10)  # Sucesss so set Heartbeat to 10 second intervals.

            if Parameters["Mode6"] == 'Debug':
                Domoticz.Log("SPRSUN Modbus Data")
                Domoticz.Log('Return water temperature: {0:.1f} C'.format(PV_Return_Water_Temperature))
                Domoticz.Log('Outlet temperature: {0:.1f} C'.format(PV_Outlet_Temperature))
                Domoticz.Log('Ambient temperature: {0:.1f} C'.format(PV_Ambient_Temperature))
                Domoticz.Log('Hot water temperature: {0:.1f} C'.format(PV_Hot_Water_Temperature))
                Domoticz.Log('Unit on: {0}'.format(Unit_On))
                Domoticz.Log('Fan output: {0:.1f}'.format(PV_Fan_Output))
                Domoticz.Log('Pump output: {0:.1f}'.format(PV_Pump_Output))
                Domoticz.Log('Required cap: {0:.1f}'.format(PV_Required_Cap))
                Domoticz.Log('Actual cap: {0:.1f}'.format(PV_Actual_Cap))
                Domoticz.Log('Power: {0:.1f}'.format(PV_Power))
                Domoticz.Log('Voltage: {0}'.format(PV_Voltage))
                Domoticz.Log('Current: {0:.1f}'.format(PV_Current))
                Domoticz.Log('Hot water setpoint: {0:.1f}'.format(SP_Hot_Water))
                Domoticz.Log('Heating setpoint: {0:.1f}'.format(SP_Heating))
                Domoticz.Log('Mode: {0}'.format(Mode))
                Domoticz.Log('Status: ' + StatusText)
                Domoticz.Log('Three-way valve: {0}'.format(ThreeWayValve))
                Domoticz.Log('Heater: {0}'.format(Heater))
                Domoticz.Log('AC_Linkage: {0}'.format(AC_Linkage))
                Domoticz.Log('Fan mode: {0}'.format(Fan_Mode))
                Domoticz.Log('Temp diff hot water: {0:.1f}'.format(SP_TempDiff_Hot_Water))
                Domoticz.Log('Temp diff cooling/heating: {0:.1f}'.format(SP_TempDiff_Cooling_Heating))
                Domoticz.Log('Eco_Mode_Cooling_X1: {0:.1f}'.format(Eco_Mode_Cooling_X1))
                Domoticz.Log('Eco_Mode_Cooling_X2: {0:.1f}'.format(Eco_Mode_Cooling_X2))
                Domoticz.Log('Eco_Mode_Cooling_X3: {0:.1f}'.format(Eco_Mode_Cooling_X3))
                Domoticz.Log('Eco_Mode_Cooling_X4: {0:.1f}'.format(Eco_Mode_Cooling_X4))
                Domoticz.Log('Eco_Mode_Cooling_Y1: {0:.1f}'.format(Eco_Mode_Cooling_Y1))
                Domoticz.Log('Eco_Mode_Cooling_Y2: {0:.1f}'.format(Eco_Mode_Cooling_Y2))
                Domoticz.Log('Eco_Mode_Cooling_Y3: {0:.1f}'.format(Eco_Mode_Cooling_Y3))
                Domoticz.Log('Eco_Mode_Cooling_Y4: {0:.1f}'.format(Eco_Mode_Cooling_Y4))
                Domoticz.Log('Eco_Mode_Heating_X1: {0:.1f}'.format(Eco_Mode_Heating_X1))
                Domoticz.Log('Eco_Mode_Heating_X2: {0:.1f}'.format(Eco_Mode_Heating_X2))
                Domoticz.Log('Eco_Mode_Heating_X3: {0:.1f}'.format(Eco_Mode_Heating_X3))
                Domoticz.Log('Eco_Mode_Heating_X4: {0:.1f}'.format(Eco_Mode_Heating_X4))
                Domoticz.Log('Eco_Mode_Heating_Y1: {0:.1f}'.format(Eco_Mode_Heating_Y1))
                Domoticz.Log('Eco_Mode_Heating_Y2: {0:.1f}'.format(Eco_Mode_Heating_Y2))
                Domoticz.Log('Eco_Mode_Heating_Y3: {0:.1f}'.format(Eco_Mode_Heating_Y3))
                Domoticz.Log('Eco_Mode_Heating_Y4: {0:.1f}'.format(Eco_Mode_Heating_Y4))
                Domoticz.Log('Eco_Mode_Hot_Water_X1: {0:.1f}'.format(Eco_Mode_Hot_Water_X1))
                Domoticz.Log('Eco_Mode_Hot_Water_X2: {0:.1f}'.format(Eco_Mode_Hot_Water_X2))
                Domoticz.Log('Eco_Mode_Hot_Water_X3: {0:.1f}'.format(Eco_Mode_Hot_Water_X3))
                Domoticz.Log('Eco_Mode_Hot_Water_X4: {0:.1f}'.format(Eco_Mode_Hot_Water_X4))
                Domoticz.Log('Eco_Mode_Hot_Water_Y1: {0:.1f}'.format(Eco_Mode_Hot_Water_Y1))
                Domoticz.Log('Eco_Mode_Hot_Water_Y2: {0:.1f}'.format(Eco_Mode_Hot_Water_Y2))
                Domoticz.Log('Eco_Mode_Hot_Water_Y3: {0:.1f}'.format(Eco_Mode_Hot_Water_Y3))
                Domoticz.Log('Eco_Mode_Hot_Water_Y4: {0:.1f}'.format(Eco_Mode_Hot_Water_Y4))
                Domoticz.Log('Setpoint cooling eco mode: {0:.1f}'.format(SP_Cooling_Eco_Mode))
                Domoticz.Log('Setpoint heating eco mode: {0:.1f}'.format(SP_Heating_Eco_Mode))
                Domoticz.Log('Setpoint hot water eco mode: {0:.1f}'.format(SP_Hot_Water_Eco_Mode))
                Domoticz.Log('Cooling setpoint: {0:.1f}'.format(SP_Cooling))
                Domoticz.Log('Pump mode: {0}'.format(Pump_Mode))

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("Something changed for " + Devices[Unit].Name + ", DeviceID = " + str(Unit) + ". New setpoint: " + str(Level) + ". New Command: " + Command)

        sValue=str(Level)
        nValue=int(Level)

        if Unit == 5:
            #Unit On
            if Command == "On":
                nValue=1
                self.settingsToWrite.append(SettingToWrite(40,1,0,True))
            else:
                nValue=0
                self.settingsToWrite.append(SettingToWrite(40,0,0,True))
            sValue=Command
        elif Unit == 13:
            #Hot water setpoint
            nValue=int(Level)
            self.settingsToWrite.append(SettingToWrite(3,float(Level),1,False))
        elif Unit == 14:
            #Heating setpoint
            nValue=int(Level)
            self.settingsToWrite.append(SettingToWrite(1,float(Level),1,False))
        elif Unit == 15:
            #Mode, when switching mode, need to turn the unit off and on again
            if Devices[5].nValue == 1:
                self.settingsToWrite.append(SettingToWrite(40,0,0,True))

            self.settingsToWrite.append(SettingToWrite(0,int((Level/10)-1),0,False))

            #if Unit was on, turn back on
            if Devices[5].nValue == 1:
                self.settingsToWrite.append(SettingToWrite(40,1,0,True))
        elif Unit == 20:
            #Fan mode
            self.settingsToWrite.append(SettingToWrite(12,int((Level/10)-1),0,False))
        elif Unit == 21:
            #Temp diff hot water
            nValue=int(Level)
            self.settingsToWrite.append(SettingToWrite(4,float(Level),1,False))
        elif Unit == 22:
            #Temp diff cooling/heating
            nValue=int(Level)
            self.settingsToWrite.append(SettingToWrite(6,float(Level),1,False))
        elif Unit == 50:
            #Cooling setpoint
            nValue=int(Level)
            self.settingsToWrite.append(SettingToWrite(2,float(Level),1,False))
        elif Unit == 51:
            #Pump mode
            self.settingsToWrite.append(SettingToWrite(11,int((Level/10)-1),0,False))

        Devices[Unit].Update(nValue=nValue, sValue=sValue)
        Devices[Unit].Refresh()

    def readFromModbus(self, client, deviceID, type, register, decimalPlaces = 0):
        #Read coils (code 0x01):             read_coils(address: int, count: int = 1, slave: int = 0, **kwargs: Any)
        #Read discrete inputs (code 0x02):   read_discrete_inputs(address: int, count: int = 1, slave: int = 0, **kwargs: Any)
        #Read holding registers (code 0x03): read_holding_registers(address: int, count: int = 1, slave: int = 0, **kwargs: Any)
        #Read input registers (code 0x04):   read_input_registers(address: int, count: int = 1, slave: int = 0, **kwargs: Any)
        try:
            if (type == 1):
                rr = client.read_coils(register,1,slave=deviceID)
                return rr.bits[0]
            elif type == 2:
                rr = client.read_discrete_inputs(register,1,slave=deviceID)
                return rr.bits[0]
            else:
                if type == 3:
                    rr = client.read_holding_registers(register,1,slave=deviceID)
                else:
                    rr = client.read_input_registers(register,1,slave=deviceID)
                decoder = BinaryPayloadDecoder.fromRegisters(rr.registers, byteorder=Endian.BIG, wordorder=Endian.BIG)
                value = decoder.decode_16bit_int()
                if decimalPlaces == 0:
                    value = int(value)
                else:
                    value = float(value/(10**decimalPlaces))
                return value
        except ModbusException as exc:
            Domoticz.Log(f"Received ModbusException({exc}) from library")
            client.close()
            return
        if rr.isError():  # pragma no cover
            Domoticz.Log(f"Received Modbus library error({rr})")
            client.close()
        if isinstance(rr, ExceptionResponse):  # pragma no cover
            Domoticz.Log(f"Received Modbus library exception ({rr})")
            # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
            client.close()
        return 0

    def writeToModbus(self, client, deviceID, type, register, value, decimalPlaces = 0, isBit = False):
        #Write single coil (code 0x05): write_coil(address: int, value: bool, slave: int = 0, **kwargs: Any)
        #Write register (code 0x06):    write_register(address: int, value: int, slave: int = 0, **kwargs: Any)
        try:
            if type == 5:
                rr = client.write_coil(register, value, slave=deviceID)
            else:
                builder = BinaryPayloadBuilder(wordorder=Endian.BIG, byteorder=Endian.BIG)
                builder.add_16bit_int(int(value*(10**decimalPlaces)))
                registers = builder.to_registers()
                rr = client.write_registers(register, registers, slave=deviceID)
        except ModbusException as exc:
            Domoticz.Log(f"Received ModbusException({exc}) from library")
            client.close()
            return
        if rr.isError():  # pragma no cover
            Domoticz.Log(f"Received Modbus library error({rr})")
            client.close()
        if isinstance(rr, ExceptionResponse):  # pragma no cover
            Domoticz.Log(f"Received Modbus library exception ({rr})")
            # THIS IS NOT A PYTHON EXCEPTION, but a valid modbus message
            client.close()

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def onStop():
    global _plugin
    _plugin.onStop()

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

def onCommand(Unit, Command, Level, Hue):
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)
