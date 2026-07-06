import pyvisa
import os
import serial
import time
from datetime import datetime
from serial.tools.list_ports import comports
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

############################################
# METODS:
# behest() - instead of write
# query()
# available() - prints available ports
############################################

class comm(serial.Serial):
    def __init__(self, port = None, baudrate = 9600, bytesize = 8, parity = "N", stopbits = 1, timeout = None, xonxoff = False, rtscts = False, write_timeout = None, dsrdtr = False, inter_byte_timeout = None, exclusive = None):
        super().__init__(port, baudrate, bytesize, parity, stopbits, timeout, xonxoff, rtscts, write_timeout, dsrdtr, inter_byte_timeout, exclusive)
        
    def query(self, command:str, type:str = 'string', encoding:str = "utf-8", delay:int = 0.1) -> str:      
        self.write(bytes(command,encoding) + b'\r\n')
        time.sleep(delay)
        if type == 'float':
            return float(self.readline().decode().replace('\r\n', ''))
        return self.readline().decode().replace('\r\n', '')
    
    def behest(self, command:str, encoding:str = "utf-8", delay:float = 0.1):
        self.write(bytes(command, encoding) + b'\r\n')
        time.sleep(delay)
        
        
class measurement:
    def __init__(self, Lakeshore, HP, Fluke, mnum = 0):
        self.LS = Lakeshore
        self.HP = HP
        self.FL = Fluke
        self.mnum = mnum
        self.power, self.TemperatureA, self.TemperatureB, self.msetp, self.Voltage, self.Current = 0, 0, 0, 0, 0, 0
        self.Time = datetime.now().strftime("%d/%m/%Y-%H:%M:%S")
        self.last_measurements = {'TempA': [],
                          'TempB': [],
                          'Volt': [],
                          'Curr': [],
                          'Time': []}
        self.first100voltage = []
        self.starting_voltage = 0
        self.ranges = [.1, 1, 10, 100, 1000]
        self.proc_of_range = [.0035, .0007, .0005, .0006, .001]
        self.range_errors = {}
        for i in range(len(self.ranges)):
            self.range_errors[self.ranges[i]] = self.ranges[i]*self.proc_of_range[i]/100 
        self.take_measurement()

    def take_measurement(self, increase_mnum = True) -> None:
        self.power = self.LS.query("HTR? 1")
        self.TemperatureA = float(self.LS.query('KRDG? A'))
        self.TemperatureB = float(self.LS.query('KRDG? B'))
        self.msetp = float(self.LS.query("SETP?"))
        self.Voltage= float(self.HP.query('MEAS:volt:dc?', delay = 1))
        self.Current= float(self.FL.query('MEAS:curr:dc?'))
        self.Time = datetime.now().strftime("%d/%m/%Y-%H:%M:%S") #round(time.time() - start_time,2)
        if increase_mnum: self.mnum += 1
        
        self.last_measurements['TempA'].append(self.TemperatureA)
        self.last_measurements['TempB'].append(self.TemperatureB)
        self.last_measurements['Volt'].append(self.Voltage)
        self.last_measurements['Curr'].append(self.Current)
        self.last_measurements['Time'].append(self.Time)
        if len(self.last_measurements[next(iter(self.last_measurements))]) > 100:
            for i in self.last_measurements:
                del self.last_measurements[i][0]
                
        if increase_mnum:
            if len(self.first100voltage) < 100:
                self.first100voltage.append(self.Voltage)
            elif self.starting_voltage == 0:
                self.starting_voltage = np.mean(np.array(self.first100voltage))

    def summary_measurement(self, update_measurement = True, show_results = True) -> str:
        if update_measurement: self.take_measurement()        
        dataline = (f'{self.TemperatureA},{self.TemperatureB}' + f',{self.Voltage}' 
        + f',{self.Current}' + f',{self.msetp},{self.power},{self.mnum},{self.Time}\n')
        if show_results: print(dataline, end = '')
        return dataline
    
    def go_to_setpoint(self, setpoint, plus = 1, heater = True, sign = 1):
        self.LS.behest(f"SETP 1,{setpoint + plus}", delay= 1)
        self.LS.behest(f"RAMP 1,1,{10}", delay = 1)
        print('xd', abs( self.TemperatureB-(setpoint+plus) ))
        while abs( self.TemperatureB-(setpoint+plus) ) > 0.1:
            self.take_measurement(increase_mnum = False)
            self.summary_measurement(update_measurement = False)
            time.sleep(15)
            print('czeka aż grzałka osiągnie 303')
        print(f'grzałka osiagneła temp. {setpoint + plus}')
        while self.TemperatureA < setpoint:
            self.take_measurement(increase_mnum = False)
            self.summary_measurement(update_measurement = False)
            time.sleep(15)
            print('czeka aż bateria osiągnie 300')
        print(f'bateria przekroczyła temp. {setpoint}')
        self.LS.behest(f"SETP 1,{setpoint}", delay= 1)
        self.LS.behest(f"RAMP 1,1,{0.5}", delay = 1)
        while abs( self.TemperatureB-setpoint ) > 0.1:
            self.take_measurement(increase_mnum = False)
            self.summary_measurement(update_measurement = False)
            time.sleep(15)
            print('czeka aż grzałka osiągnie 300')
        print(f'grzałka osiagneła temp. {setpoint}')
        startTime = time.time()
        while time.time() < startTime + 30*60:
            self.take_measurement(increase_mnum = False)
            self.summary_measurement(update_measurement = False)
            time.sleep(15)
            print('czeka aż upłunie 30min')
        print("STARTING TEMPERATURE REACHED")

            
# ANOTHER FUNCTIONS
def save_data(filename, dataline) -> None:
    datafile = open(filename,'a')
    datafile.write(dataline)
    datafile.close()
    
def await_for(startT, deltaT):
    while time.time() < startT + deltaT:
        pass
            
def opening_file(filename:str):
    try:
        f = open(filename, 'w')
        f.close
    except Exception:
        pass

def closeInstruments(Lakeshore, HP, Fluke):
    Lakeshore.behest('RANGE 1,3', delay = 1) # turn off heater
    Lakeshore.behest('SETP 1, 300', delay = 1)
    Lakeshore.behest(f"RAMP 1,1,0")
    Lakeshore.close()  
    HP.behest('SYST:LOC')
    HP.close()
    Fluke.behest('SYST:LOC')
    Fluke.close()
    
def available() -> None:
    ports = comports()
    for i in ports:
        print(i)
