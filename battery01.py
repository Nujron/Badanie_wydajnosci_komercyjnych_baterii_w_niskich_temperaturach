import pyvisa
import os
import serial
import time
from serial.tools.list_ports import comports
import battery_bib as batt
from battery_bib import save_data
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

#######################################################################################
#################################   SET PARAMETERS HERE ###############################
batt_name = 'GCAA'
batt_type = 'NiMH'
Method_of_measurement = '01'
No_of_measurement = '01'
directory_name = 'data'
# ZRÓB, ŻEBY NIE DAŁO SIĘ NADPISAĆ ISTNIEJĄCEGO PLIKU
sep = ',' # datafile separator

time_between_measurements = 10 # [s]
ramp_rate = 0.1 # [K/min]
highest_setpoint = 300 # [K]
lowest_setpoint = 150 # [K]
valleyDuration = 1 # hours

# ports:
portLakeshore = 'COM7'
portHP = 'COM4' # voltage
portFluke = 'COM3' # current
#######################################################################################
#######################################################################################


filename = directory_name + '/' + batt_name + '_' + batt_type + '_' + Method_of_measurement + No_of_measurement + '.dat'
print(filename)
date = datetime.now().strftime("%Y-%m-%d")

# seting up instruments
Lakeshore = batt.comm(port=portLakeshore, baudrate= 57600, bytesize= serial.SEVENBITS, stopbits= serial.STOPBITS_ONE, parity= serial.PARITY_ODD, timeout= 1)
Lakeshore.behest('RANGE 1,3')

HP = batt.comm(port=portHP, timeout= 1, parity= serial.PARITY_NONE)
HP.behest('SYST:REM', delay = 1)

Fluke = batt.comm(port=portFluke, timeout= 1, parity= serial.PARITY_NONE)
Fluke.behest('SYST:REM')   
    
# opening data file
batt.opening_file(filename= filename)  

# datafile header
save_data( filename, f'# highest_setpoint = {highest_setpoint} K\n' )
save_data( filename, f'# lowest_setpoint = {lowest_setpoint} K\n' )
save_data( filename, f'# ramp_rate = {ramp_rate} K/min\n' )
save_data( filename, f'# date = {date}\n' )
save_data( filename, 'TemperatureA'+ sep + 'TemperatureB' + sep +
            'Voltage' + sep + 'Current' + sep + 'Setpoint' + sep + 
            'pwr' + sep + 'mnumber' + sep + 'Time' + '\n')

Measurement = batt.measurement(Lakeshore= Lakeshore, HP= HP, Fluke= Fluke)
Measurement.go_to_setpoint(setpoint= highest_setpoint, plus= 3)

# COOLING
Lakeshore.behest( f"SETP 1, {lowest_setpoint}", delay= 1 )
Lakeshore.behest( f"RAMP 1,1,{ramp_rate}", delay= 1 )
while True:
    startTime = time.time()
    save_data( filename, Measurement.summary_measurement() ) # takes measurement and saves data to file
    batt.await_for( startTime, time_between_measurements )#time.sleep(time_between_measurements) # awaits
    print('schoodzi')
    #
    #print('xd', Measurement.starting_voltage, np.array(Measurement.last_measurements['Volt']))
    #
    print('to i to', np.mean(np.array(Measurement.last_measurements['Volt'])), Measurement.starting_voltage, len(Measurement.last_measurements['Volt']))
    print('tempa', np.mean(np.array(Measurement.last_measurements['TempA'])))
    if np.mean(np.array(Measurement.last_measurements['Volt'])) < 0.001*Measurement.starting_voltage and Measurement.starting_voltage !=0:
        break

print('setpoint w dolinie: ', Measurement.msetp)
Lakeshore.behest( f"SETP 1, {Measurement.msetp}", delay= 1 )
# WAITING
print('czekamy w dolince')
startTimeValley = time.time()
Lakeshore.behest( f"SETP 1, {Measurement.TemperatureA}", delay= 1 )
while True:
    startTime = time.time()
    if (startTime - startTimeValley) > valleyDuration*3600:
        break
    save_data( filename, Measurement.summary_measurement() ) # takes measurement and saves data to file
    Lakeshore.behest( f"RAMP 1,1,{ (Measurement.TemperatureA - Measurement.msetp)/(valleyDuration*60) }", delay= 1 )
    batt.await_for( startTime, time_between_measurements )#time.sleep(time_between_measurements) # awaits
    
# HEATING
print('lecimy w góre')
Lakeshore.behest(f"SETP 1, {highest_setpoint + 3}", delay= 1)
Lakeshore.behest(f"RAMP 1,1,{ramp_rate}", delay= 1)
while (np.mean(np.array(Measurement.last_measurements['TempA'])) < highest_setpoint):
    startTime = time.time()
    save_data( filename, Measurement.summary_measurement() ) # takes measurement and saves data to file
    batt.await_for( startTime, time_between_measurements )#time.sleep(time_between_measurements) # awaits
    
save_data( filename, '# MEASUREMENT ENDED\n' )
print('MEASUREMENT ENDED\n')
    
batt.closeInstruments( Lakeshore, HP, Fluke )

