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

def main():
    #######################################################################################
    #################################   SET PARAMETERS HERE ###############################
    batt_name = 'DCAA'
    batt_type = 'Lion'
    Method_of_measurement = '00'
    No_of_measurement = '05'
    directory_name = 'data'
    # ZRÓB, ŻEBY NIE DAŁO SIĘ NADPISAĆ ISTNIEJĄCEGO PLIKU
    sep = ',' # datafile separator

    time_between_measurements = 10 # [s]
    ramp_rate = 0.2 # [K/min]
    highest_setpoint = 300 # [K]
    lowest_setpoint = 160 # [K]
    end_time = 7 # [min] # instead of stabilisation time
    
    # ports:
    portLakeshore = 'COM7'
    portHP = 'COM4' # voltage
    portFluke = 'COM3' # current
    #######################################################################################
    #######################################################################################
    
    
    
    filename = directory_name + '/' + batt_name + '_' + batt_type + '_' + Method_of_measurement + No_of_measurement + '.dat'
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
    save_data( filename, f'# date = {date} K/min\n' )
    save_data( filename, f'# t0 = {end_time} min\n' )
    save_data( filename, 'TemperatureA'+ sep + 'TemperatureB' + sep +
              'Voltage' + sep + 'Current' + sep + 'Setpoint' + sep + 
              'pwr' + sep + 'mnumber' + sep + 'Time' + '\n')

    Measurement = batt.measurement(Lakeshore= Lakeshore, HP= HP, Fluke= Fluke)
    Measurement.go_to_setpoint(setpoint= highest_setpoint, plus= 3, heater= False, sign= 1)

    # COOLING
    Lakeshore.behest( f"SETP 1, {lowest_setpoint}", delay= 1 )
    Lakeshore.behest( f"RAMP 1,1,{ramp_rate}", delay= 1 )
    while (Lakeshore.query("SETP?", type= 'float', delay= 1) > lowest_setpoint):
        startTime = time.time()
        save_data( filename, Measurement.summary_measurement() ) # takes measurement and saves data to file
        batt.await_for( startTime, time_between_measurements )#time.sleep(time_between_measurements) # awaits
    # HEATING
    print('lecimy w góre')
    Lakeshore.behest(f"SETP 1, {highest_setpoint + 2}", delay= 1)
    Lakeshore.behest(f"RAMP 1,1,{ramp_rate}", delay= 1)
    while (Lakeshore.query("SETP?", 'float', delay= 1) < highest_setpoint):
        startTime = time.time()
        save_data( filename, Measurement.take_measurement() ) # takes measurement and saves data to file
        batt.await_for( startTime, time_between_measurements )#time.sleep(time_between_measurements) # awaits
        
    save_data( filename, '# MEASUREMENT ENDED\n' )
    print('MEASUREMENT ENDED\n')
        
    batt.closeInstruments( Lakeshore, HP, Fluke )

try: main()
except:
    print('interrupted')
