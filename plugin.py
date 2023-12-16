#!/usr/bin/env python
"""
SPRSUN-Modbus Heat Pump. The Python plugin for Domoticz
Original Author: MFxMF and bbossink and remcovanvugt
Better Error handling and event recovery added by simat-git 2023.
Converted from Eastron SDM120M to SPRSUN plugin by Sateetje 2023.

Works with SPRSUN HeatPump CGK0x0V2.

Requirements:
    1.python module minimalmodbus -> http://minimalmodbus.readthedocs.io/en/master/
        (pi@raspberrypi:~$ sudo pip3 install minimalmodbus)
    2.Communication module Modbus USB to RS485 converter module
"""
"""
<plugin key="SPRSUN" name="SPRSUN-Modbus" version="1" author="Sateetje">
    <params>
        <param field="SerialPort" label="Modbus Port" width="200px" required="true" default="/dev/ttyUSB0" />
        <param field="Mode1" label="Baud rate" width="40px" required="true" default="19200"  />
        <param field="Mode2" label="Device ID" width="40px" required="true" default="1" />
        <param field="Mode6" label="Debug" width="75px">
            <options>
                <option label="True" value="Debug"/>
                <option label="False" value="Normal"  default="true" />
            </options>
        </param>
    </params>
</plugin>

"""

import minimalmodbus    #v2.1.1
import Domoticz         #tested on Python 3.9.2 in Domoticz 2023.2

class SettingToWrite:
    def __init__(self, register, value, decimalPlaces, signed, isBit):
        self.register = register
        self.value = value
        self.decimalPlaces = decimalPlaces
        self.signed = signed
        self.isBit = isBit

class BasePlugin:
    def __init__(self):
        self.runInterval = 1
        self.rs485 = ""
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
            Domoticz.Device(Name="Pomp mode",Unit=51,TypeName="Selector Switch",Options=Options,Image=11,Used=1).Create()

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
            Pomp_Mode = 0

            # Get data from SPRSUN
            try:
                self.rs485 = minimalmodbus.Instrument(Parameters["SerialPort"], int(Parameters["Mode2"]))
                self.rs485.serial.baudrate = Parameters["Mode1"]
                self.rs485.serial.bytesize = 8
                self.rs485.serial.parity = minimalmodbus.serial.PARITY_NONE
                self.rs485.serial.stopbits = 1
                self.rs485.serial.timeout = 1
                self.rs485.serial.exclusive = True # Fix From Forum Member 'lost'
                self.rs485.debug = False
                self.rs485.mode = minimalmodbus.MODE_RTU
                self.rs485.close_port_after_each_call = True

                # Write settings first
                for setting in self.settingsToWrite:
                    Domoticz.Log('Writing to register {0} with value {1}'.format(setting.register,setting.value))
                    if setting.isBit == True:
                        self.rs485.write_bit(setting.register,setting.value,5) # Value 0 or 1
                    else:
                        self.rs485.write_register(setting.register,setting.value,setting.decimalPlaces,6,setting.signed)
                self.settingsToWrite.clear()

                PV_Return_Water_Temperature = self.rs485.read_register(188,1,3,False)
                PV_Outlet_Temperature = self.rs485.read_register(189,1,3,False)
                PV_Ambient_Temperature = self.rs485.read_register(190,1,3,False)
                PV_Hot_Water_Temperature = self.rs485.read_register(195,1,3,False)
                Unit_On = self.rs485.read_bit(40, 1)
                PV_Fan_Output = self.rs485.read_register(197,1,3,False)
                PV_Pump_Output = self.rs485.read_register(198,1,3,False)
                PV_Required_Cap = self.rs485.read_register(203,1,3,False)
                PV_Actual_Cap = self.rs485.read_register(204,1,3,False)
                PV_Power = self.rs485.read_register(333,1,3,False) * 1000 #kW to W
                PV_Voltage = self.rs485.read_register(334,0,3,False)
                PV_Current = self.rs485.read_register(335,1,3,False)
                SP_Hot_Water = self.rs485.read_register(3,1,3,False)
                SP_Heating = self.rs485.read_register(1,1,3,False)
                Mode = self.rs485.read_register(0,0,3,False)
                Status = self.rs485.read_register(217,0,3,False)
                ThreeWayValve = self.rs485.read_bit(11, 2)
                Heater = self.rs485.read_bit(12, 2)
                AC_Linkage = self.rs485.read_bit(3, 2)
                Fan_Mode = self.rs485.read_register(12,0,3,False)
                SP_TempDiff_Hot_Water = self.rs485.read_register(4,1,3,False)
                SP_TempDiff_Cooling_Heating = self.rs485.read_register(6,1,3,False)
                Eco_Mode_Cooling_X1 = self.rs485.read_register(276,1,3,True)
                Eco_Mode_Cooling_X2 = self.rs485.read_register(277,1,3,True)
                Eco_Mode_Cooling_X3 = self.rs485.read_register(278,1,3,True)
                Eco_Mode_Cooling_X4 = self.rs485.read_register(279,1,3,True)
                Eco_Mode_Cooling_Y1 = self.rs485.read_register(336,1,3,True)
                Eco_Mode_Cooling_Y2 = self.rs485.read_register(288,1,3,True)
                Eco_Mode_Cooling_Y3 = self.rs485.read_register(289,1,3,True)
                Eco_Mode_Cooling_Y4 = self.rs485.read_register(290,1,3,True)
                Eco_Mode_Heating_X1 = self.rs485.read_register(280,1,3,True)
                Eco_Mode_Heating_X2 = self.rs485.read_register(281,1,3,True)
                Eco_Mode_Heating_X3 = self.rs485.read_register(282,1,3,True)
                Eco_Mode_Heating_X4 = self.rs485.read_register(283,1,3,True)
                Eco_Mode_Heating_Y1 = self.rs485.read_register(291,1,3,True)
                Eco_Mode_Heating_Y2 = self.rs485.read_register(292,1,3,True)
                Eco_Mode_Heating_Y3 = self.rs485.read_register(293,1,3,True)
                Eco_Mode_Heating_Y4 = self.rs485.read_register(337,1,3,True)
                Eco_Mode_Hot_Water_X1 = self.rs485.read_register(284,1,3,True)
                Eco_Mode_Hot_Water_X2 = self.rs485.read_register(285,1,3,True)
                Eco_Mode_Hot_Water_X3 = self.rs485.read_register(286,1,3,True)
                Eco_Mode_Hot_Water_X4 = self.rs485.read_register(287,1,3,True)
                Eco_Mode_Hot_Water_Y1 = self.rs485.read_register(294,1,3,True)
                Eco_Mode_Hot_Water_Y2 = self.rs485.read_register(295,1,3,True)
                Eco_Mode_Hot_Water_Y3 = self.rs485.read_register(296,1,3,True)
                Eco_Mode_Hot_Water_Y4 = self.rs485.read_register(338,1,3,True)
                SP_Cooling = self.rs485.read_register(2,1,3,False)
                Pomp_Mode = self.rs485.read_register(11,0,3,False)

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

                self.rs485.serial.close()  #  Close that door !
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
                Devices[51].Update(nValue=int((Pomp_Mode+1)*10),sValue=str((Pomp_Mode+1)*10))

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
                Domoticz.Log('Pomp mode: {0}'.format(Pomp_Mode))

    def onCommand(self, Unit, Command, Level, Hue):
        Domoticz.Log("Something changed for " + Devices[Unit].Name + ", DeviceID = " + str(Unit) + ". New setpoint: " + str(Level) + ". New Command: " + Command)

        sValue=str(Level)
        nValue=int(Level)

        if Unit == 5:
            #Unit On
            if Command == "On":
                nValue=1
                self.settingsToWrite.append(SettingToWrite(40,1,0,False,True))
            else:
                nValue=0
                self.settingsToWrite.append(SettingToWrite(40,0,0,False,True))
            sValue=Command
        elif Unit == 13:
            #Hot water setpoint
            nValue=int(Level)
            self.settingsToWrite.append(SettingToWrite(3,float(Level),1,False,False))
        elif Unit == 14:
            #Heating setpoint
            nValue=int(Level)
            self.settingsToWrite.append(SettingToWrite(1,float(Level),1,False,False))
        elif Unit == 15:
            #Mode, when switching mode, need to turn the unit off and on again
            if Devices[5].nValue == 1:
                self.settingsToWrite.append(SettingToWrite(40,0,0,False,True))

            self.settingsToWrite.append(SettingToWrite(0,int((Level/10)-1),0,False,False))

            #if Unit was on, turn back on
            if Devices[5].nValue == 1:
                self.settingsToWrite.append(SettingToWrite(40,1,0,False,True))
        elif Unit == 20:
            #Fan mode
            self.settingsToWrite.append(SettingToWrite(12,int((Level/10)-1),0,False,False))
        elif Unit == 21:
            #Temp diff hot water
            nValue=int(Level)
            self.settingsToWrite.append(SettingToWrite(4,float(Level),1,False,False))
        elif Unit == 22:
            #Temp diff cooling/heating
            nValue=int(Level)
            self.settingsToWrite.append(SettingToWrite(6,float(Level),1,False,False))
        elif Unit == 50:
            #Cooling setpoint
            nValue=int(Level)
            self.settingsToWrite.append(SettingToWrite(2,float(Level),1,False,False))
        elif Unit == 51:
            #Pomp mode
            self.settingsToWrite.append(SettingToWrite(11,int((Level/10)-1),0,False,False))

        Devices[Unit].Update(nValue=nValue, sValue=sValue)
        Devices[Unit].Refresh()

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

# Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug("'" + x + "':'" + str(Parameters[x]) + "'")
            Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
