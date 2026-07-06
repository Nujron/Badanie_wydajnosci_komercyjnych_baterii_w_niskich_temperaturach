import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from scipy.optimize import curve_fit

class meas_data:    
    def __init__(self, filename, comment = '#', sep = ',', markersize = 10, show_time = False):
        self.params = []
        self.info = ''
        self.histereza = 0.
        self.filename = filename
        self.ID = self.filename.split('/')[-1].split('_')[0]
        self.batt_type = self.filename.split('/')[-1].split('_')[1]
        self.data = pd.read_csv(filename, sep=sep, comment= comment)
        self.Measurement_Time = pd.to_datetime(self.data['Time'], format= '%d/%m/%Y-%H:%M:%S')
        self.Measurement_Time_Hours = (self.Measurement_Time - self.Measurement_Time.iloc[0]).dt.total_seconds() / 3600
        self.measurement_duration = ''
        self.ramp_rate = 0
        self.TemperatureA = self.data.loc[:, 'TemperatureA']
        self.TemperatureB = self.data.loc[:, 'TemperatureB']
        self.Voltage = self.data.loc[:, 'Voltage']
        self.Current = self.data.loc[:, 'Current']
        self.Batt_Power = self.Voltage*self.Current
        self.Setpoint = self.data.loc[:, 'Setpoint']
        self.Heater_Power = self.data.loc[:, 'pwr']
        self.markersize = markersize
        self.T90U, self.T10U, self.T90P, self.T10P = 0, 0, 0, 0
        self.DeltaT90U, self.DeltaT10U, self.DeltaT90P, self.DeltaT10P = 0, 0, 0, 0
        self.T90Usmall, self.T10Usmall, self.T90Psmall, self.T10Psmall = 0, 0, 0, 0
        self.T90Uhuge, self.T10Uhuge, self.T90Phuge, self.T10Phuge = 0, 0, 0, 0
        self.Voltage_diff, self.Voltage_perc_diff = 0, 0
        self.Power_diff, self.Power_perc_diff = 0, 0
        self.get_info(show_time= show_time)
        self.T90T10('Voltage')
        self.T90T10('Power')
        
        
             
    def split_data_VorIorP(self, VorIorP):
        if VorIorP == 'Voltage': quantity = self.Voltage
        if VorIorP == 'Current': quantity = self.Current
        if VorIorP == 'Power': quantity = self.Batt_Power
        indmin = quantity.argmin()
        mask1 = (quantity.index < indmin)
        mask2 = (quantity.index > indmin)
        
        quantity_1st_half = quantity[mask1]
        quantity_2nd_half = quantity[mask2]
        TemperatureA_1st_half = self.TemperatureA[mask1]
        TemperatureA_2nd_half = self.TemperatureA[mask2]
        Measurement_Time_1st_half = self.Measurement_Time[mask1]
        Measurement_Time_2nd_half = self.Measurement_Time[mask2]
        return quantity, quantity_1st_half, quantity_2nd_half, TemperatureA_1st_half, TemperatureA_2nd_half, Measurement_Time_1st_half, Measurement_Time_2nd_half
        
        
    def goldilocks_zone(self, VorIorP):
        quantity, quantity_1st_half, quantity_2nd_half, TemperatureA_1st_half, TemperatureA_2nd_half, _, _ = self.split_data_VorIorP(VorIorP)
        max_quantity = quantity.max()
        min_quantity = quantity.min()
        ikar_rise = 0.9*(max_quantity - min_quantity) + min_quantity
        ikar_fall = 0.1*(max_quantity - min_quantity) + min_quantity
        #
        ikar_rise_ind_1st_half = ( abs(quantity_1st_half - ikar_rise) ).argmin()
        ikar_rise_ind_2nd_half = ( abs(quantity_2nd_half - ikar_rise) ).argmin()
        ikar_rise_T = ( TemperatureA_1st_half.iloc[ikar_rise_ind_1st_half] + TemperatureA_2nd_half.iloc[ikar_rise_ind_2nd_half] )/2
        #
        ikar_fall_ind_1st_half = ( abs(quantity_1st_half - ikar_fall) ).argmin()
        ikar_fall_ind_2nd_half = ( abs(quantity_2nd_half - ikar_fall) ).argmin()
        ikar_fall_T = ( TemperatureA_1st_half.iloc[ikar_fall_ind_1st_half] + TemperatureA_2nd_half.iloc[ikar_fall_ind_2nd_half] )/2
        #       
        return ikar_rise, ikar_fall, ikar_rise_T, ikar_fall_T
        
    
    def T90T10(self, VorIorP):
        quantity, quantity_1st_half, quantity_2nd_half, TemperatureA_1st_half, TemperatureA_2nd_half, Measurement_Time_1st_half, Measurement_Time_2nd_half = self.split_data_VorIorP(VorIorP)
        ikar_rise, ikar_fall, ikar_rise_T, ikar_fall_T = self.goldilocks_zone(VorIorP)
        
        # podział na krzywą chłodzenia i grzania
        mask1 = (quantity_1st_half > ikar_fall)*(quantity_1st_half < ikar_rise)
        quantity_1st_half_area = quantity_1st_half[mask1]
        TemperatureA_1st_half_area = TemperatureA_1st_half[mask1]
        
        mask2 = (quantity_2nd_half > ikar_fall)*(quantity_2nd_half < ikar_rise)
        quantity_2nd_half_area = quantity_2nd_half[mask2]
        TemperatureA_2nd_half_area = TemperatureA_2nd_half[mask2]
        
        # do liczenia rozstrzału histerezy
        y_to_fill_1st = np.array(quantity_1st_half_area)
        y_to_fill_2nd = np.array(quantity_2nd_half_area)
        x_to_fill_1st = np.array(TemperatureA_1st_half_area)
        x_to_fill_2nd = np.array(TemperatureA_2nd_half_area)
        x_to_fill_2nd_adjusted = x_to_fill_1st.copy()
        for i, val in enumerate(x_to_fill_2nd_adjusted):
            idx = np.argmin(np.abs(y_to_fill_1st[i] - y_to_fill_2nd))
            x_to_fill_2nd_adjusted[i] = x_to_fill_2nd[idx]
            
        if VorIorP == 'Voltage':
            self.T90U = ikar_rise_T
            self.T10U = ikar_fall_T
            self.T10Uhuge, self.T10Usmall = max(x_to_fill_1st[-1], x_to_fill_2nd[0]), min(x_to_fill_1st[-1], x_to_fill_2nd[0])
            self.T90Uhuge, self.T90Usmall = max(x_to_fill_1st[0], x_to_fill_2nd[-1]), min(x_to_fill_1st[0], x_to_fill_2nd[-1])
            self.DeltaT10U = self.T10Uhuge - self.T10Usmall
            self.DeltaT90U = self.T90Uhuge - self.T90Usmall
        if VorIorP == 'Power':
            self.T90P = ikar_rise_T
            self.T10P = ikar_fall_T
            self.T10Phuge, self.T10Psmall = max(x_to_fill_1st[-1], x_to_fill_2nd[0]), min(x_to_fill_1st[-1], x_to_fill_2nd[0])
            self.T90Phuge, self.T90Psmall = max(x_to_fill_1st[0], x_to_fill_2nd[-1]), min(x_to_fill_1st[0], x_to_fill_2nd[-1])
            self.DeltaT10P = self.T10Phuge - self.T10Psmall
            self.DeltaT90P = self.T90Phuge - self.T90Psmall
            
        field_diff = 0
        for i in range(1, len(x_to_fill_1st)):
            field_diff += abs(x_to_fill_1st[i] - x_to_fill_2nd_adjusted[i]) * abs(y_to_fill_1st[i] - y_to_fill_1st[i-1])
        
        quantity_diff = field_diff/(ikar_rise - ikar_fall)
        perc_diff = abs(quantity_diff/(ikar_rise_T-ikar_fall_T)*100)
        
        if VorIorP == 'Voltage':
            self.Voltage_diff = quantity_diff
            self.Voltage_perc_diff = perc_diff
        if VorIorP == 'Power':
            self.Power_diff = quantity_diff
            self.Power_perc_diff = perc_diff
        
    
    def histereza_T_VorIorP(self, VorIorP, ax = False, show_times = False, testing = False, legend= True):
        quantity, quantity_1st_half, quantity_2nd_half, TemperatureA_1st_half, TemperatureA_2nd_half, Measurement_Time_1st_half, Measurement_Time_2nd_half = self.split_data_VorIorP(VorIorP)
        ikar_rise, ikar_fall, ikar_rise_T, ikar_fall_T = self.goldilocks_zone(VorIorP)
        
        # podział na krzywą chłodzenia i grzania
        mask1 = (quantity_1st_half > ikar_fall)*(quantity_1st_half < ikar_rise)
        quantity_1st_half_area = quantity_1st_half[mask1]
        TemperatureA_1st_half_area = TemperatureA_1st_half[mask1]
        
        mask2 = (quantity_2nd_half > ikar_fall)*(quantity_2nd_half < ikar_rise)
        quantity_2nd_half_area = quantity_2nd_half[mask2]
        TemperatureA_2nd_half_area = TemperatureA_2nd_half[mask2]
        
        # do liczenia rozstrzału histerezy
        y_to_fill_1st = np.array(quantity_1st_half_area)
        y_to_fill_2nd = np.array(quantity_2nd_half_area)
        x_to_fill_1st = np.array(TemperatureA_1st_half_area)
        x_to_fill_2nd = np.array(TemperatureA_2nd_half_area)
        x_to_fill_2nd_adjusted = x_to_fill_1st.copy()
        for i, val in enumerate(x_to_fill_2nd_adjusted):
            idx = np.argmin(np.abs(y_to_fill_1st[i] - y_to_fill_2nd))
            x_to_fill_2nd_adjusted[i] = x_to_fill_2nd[idx]
            
        field_diff = 0
        for i in range(1, len(x_to_fill_1st)):
            field_diff += abs(x_to_fill_1st[i] - x_to_fill_2nd_adjusted[i]) * abs(y_to_fill_1st[i] - y_to_fill_1st[i-1])
        
        quantity_diff = field_diff/(ikar_rise - ikar_fall)
        perc_diff = abs(quantity_diff/(ikar_rise_T-ikar_fall_T)*100)
        if not ax: print(f'Temperature mean difference: {quantity_diff:.0f}K ({perc_diff:.0f}% of range)') 
        # czas zasypiania i budzenia się
        falling_interval = (Measurement_Time_1st_half[mask1]).max() - (Measurement_Time_1st_half[mask1]).min()
        rising_interval = (Measurement_Time_2nd_half[mask2]).max() - (Measurement_Time_2nd_half[mask2]).min()
        full_interval = falling_interval + rising_interval
        # wykresy
        if ax:
            factor = (1 + ((1e3 - 1)*(VorIorP=='Current')) + ((1e3-1)*(VorIorP=='Power')))
            if legend:
                ax.set_title(show_times*('Duration: ' + self.measurement_duration + '\n') +
                            f'Temperature mean difference: {quantity_diff:.0f}K ({perc_diff:.0f}% of range)' + 
                            show_times * ('\nFading: ' + ((d := rising_interval.days) != 0)*f'{d}d' + ((m := falling_interval.seconds/3600) >= 1 )*f' {m:.0f}h'+ ((s := falling_interval.seconds % 60) != 0)*f' {s:.0f}min' +
                            '  |  Rising: ' + ((d := rising_interval.days) != 0)*f'{d}d' + ((m := rising_interval.seconds/3600) >= 1 )*f' {m:.0f}h' + ((s := rising_interval.seconds % 60) != 0)*f' {s:.0f}min' + 
                            '  |  Sum: ' + ((d := full_interval.days) != 0)*f'{d}d' + ((m := full_interval.seconds/3600) >= 1 )*f' {m:.0f}h' + ((s := full_interval.seconds % 60) != 0)*f' {s:.0f}min') ,)
                
            ax.plot(TemperatureA_1st_half, quantity_1st_half*factor, linewidth= 2, color = 'magenta', label = 'cooling')
            ax.plot(TemperatureA_2nd_half, quantity_2nd_half*factor, linewidth= 2, color = 'orange', label = 'heating')
            
            ax.plot([self.TemperatureA.min(), self.TemperatureA.max()], np.ones(2)*ikar_rise*factor, color = 'seagreen', ls = '-.', linewidth = 1,
                    label = '90% of maximum ' + VorIorP)
            ax.plot(np.ones(2)*ikar_rise_T, np.array([quantity.min(), quantity.max()])*factor, color = 'seagreen', ls = '--', linewidth = 1.5,
                    label = f'90% point $T$: $\\mathbf{{{ikar_rise_T:.0f}K}}$, $\\Delta T$: $\\mathbf{{{abs(x_to_fill_1st[0]-x_to_fill_2nd)[-1]:.0f}K}}$')
            
            ax.plot([self.TemperatureA.min(), self.TemperatureA.max()], np.ones(2)*ikar_fall*factor, color = 'crimson', ls = '-.', linewidth = 1,
                    label = '10% of maximum ' + VorIorP)
            ax.plot(np.ones(2)*ikar_fall_T, np.array([quantity.min(), quantity.max()])*factor, color = 'crimson', ls = '--', linewidth = 1.5,
                    label = f'10% point $T$: $\\mathbf{{{ikar_fall_T:.0f}K}}$, $\\Delta T$: $\\mathbf{{{abs(x_to_fill_1st[-1]-x_to_fill_2nd)[0]:.0f}K}}$')
            
            ax.set_xlabel('Temperature of battery [K]')
            if VorIorP == 'Voltage': ax.set_ylabel('Voltage [V]')
            if VorIorP == 'Current': ax.set_ylabel('Current [mA]')
            if VorIorP == 'Power': ax.set_ylabel('Power [mW]')
            
            if legend: ax.fill_betweenx(y_to_fill_1st*factor, x_to_fill_1st, x_to_fill_2nd_adjusted, color = 'deepskyblue', alpha = .3, label= 'hysteresis width')
            
            if legend: ax.legend(loc = 'lower right', bbox_to_anchor=(.98, .2))
     
        
    def read_parameters(self, type_int = False):
        f = open(self.filename, 'r')
        while True:
            line = f.readline()
            if line[0] == '#':
                try:
                    sub_params = {}
                    line = line.split()
                    sub_params['quantity'] = line[1]
                    sub_params['value'] = int(line[3]) if type_int else float(line[3])
                    sub_params['unit'] = line[4]
                    self.params.append(sub_params)
                except: pass
            else: break
        f.close()


    def get_info(self, show_time= False):
        if self.params == []: self.read_parameters()
        tmp = 'ID: ' + self.ID + ' | Battery type: ' + (self.batt_type + ' | Rampa rate: ')
        for i, val in enumerate(self.params): 
            if i == 2: 
                self.ramp_rate = val['value']
                tmp += False*f'{val['quantity']}:' + f'{val['value']}{val['unit']}' + (val != self.params[-1]) * '  |  ' 
        if show_time:
            timedelta = (self.Measurement_Time.max() - self.Measurement_Time.min())
            self.measurement_duration = f'{timedelta.days}d {timedelta.seconds/3600:.0f}h'
            tmp = tmp + '  |  ' + 'duration: ' + self.measurement_duration
        self.info = tmp
  
        
    def plot_V_I(self, fig, axs):
        # tablice do kolorowania
        colormask = (self.Measurement_Time - self.Measurement_Time.min()).dt.total_seconds()
        cbar_positions = np.linspace( colormask.min(), colormask.max(), 21 )
        cbar_labels = pd.to_timedelta(cbar_positions.astype(int), unit = 's').astype(str)
        # wykresy
        scatter1 = axs[0].scatter(self.TemperatureA, self.Voltage, s = self.markersize, c= colormask, cmap= 'tab20b')
        axs[0].set_xlabel('Temperature of battery [K]')
        axs[0].set_ylabel('Voltage [V]')
        #
        scatter1 = axs[1].scatter(self.TemperatureA, self.Current*1000, s = self.markersize, c= colormask, cmap= 'tab20b')
        axs[1].set_xlabel('Temperature of battery [K]')
        axs[1].set_ylabel('Current [mA]')
        cbar = fig.colorbar(scatter1)
        cbar.set_ticks(cbar_positions)
        cbar.set_ticklabels(cbar_labels)
    
    
    def plot_T_T(self, fig, ax):
        # tablice do kolorowania
        colormask = (self.Measurement_Time - self.Measurement_Time.min()).dt.total_seconds()
        cbar_positions = np.linspace( colormask.min(), colormask.max(), 21 )
        cbar_labels = pd.to_timedelta(cbar_positions.astype(int), unit = 's').astype(str)
        # wykres
        scatter = ax.scatter(self.TemperatureB, self.TemperatureA, s = self.markersize, c= colormask, cmap= 'tab20b', zorder= 10)
        ax.set_xlabel('Temperature B of probe')
        ax.set_ylabel('Temperature A of battery')
        cbar = fig.colorbar(scatter)
        cbar.set_ticks(cbar_positions)
        cbar.set_ticklabels(cbar_labels)
    
        
    def plot_T_t(self, fig, ax, batt= True, probe= True, setp= True, lis = '-', maxtime = False, xlims= False, ylims= False, VorIorP= False, legend= True):
        batt_kwargs, probe_kwargs, setp_kwargs = {}, {}, {}
        if bool(not(int(batt) + int(probe) + int(setp))) + bool(VorIorP): 
            batt_kwargs.update(color="deepskyblue", label="Temperature of battery")
            probe_kwargs.update(color="purple", label="Temperature of probe")
            setp_kwargs.update(color="orange", label="Setpoint")
            if bool(not(int(batt) + int(probe) + int(setp))):
                secax = ax.secondary_yaxis('right', functions = (lambda x: 100*(x-Tmin)/(Tmax - Tmin), 
                                                            lambda x: x*(Tmax - Tmin)/100 + Tmin))
                secax.set_ylabel('Heater power [%]')
        else:
            batt_kwargs["label"] = self.ID + ' (' + self.batt_type + ')'
            probe_kwargs["label"] = self.ID + ' (' + self.batt_type + ')'
            setp_kwargs["label"] = self.ID + ' (' + self.batt_type + ')'     
        
        alpha = 1
        Tmax = max(self.TemperatureA.max(), self.TemperatureB.max(), self.Setpoint.max())
        Tmin = min(self.TemperatureA.min(), self.TemperatureB.min(), self.Setpoint.min())
        
        if not(int(batt) + int(probe) + int(setp) == 1):
            if isinstance(ylims, tuple): Tmax, Tmin = ylims[1], ylims[0]
            ax.plot(self.Measurement_Time_Hours, self.Heater_Power*(Tmax-Tmin)/100+Tmin, 
                    color = 'gray', alpha = alpha, zorder = 7, marker = 's', linewidth= 1, markersize= 2.5, label = 'Power')
            ax.fill_between(self.Measurement_Time_Hours, self.Heater_Power*(Tmax-Tmin)/100+Tmin, 
                            np.ones(len(self.Heater_Power*(Tmax-Tmin)/100+Tmin))*Tmin,
                            color = 'gray', alpha = .5, zorder = 7)
            
        if maxtime: timeshift = (maxtime - self.Measurement_Time_Hours.max())/2
        else: timeshift = 0
        if probe: ax.plot(self.Measurement_Time_Hours + timeshift, self.TemperatureB,
                linewidth= 2, alpha = alpha, zorder = 9, ls= lis , **probe_kwargs)
        if setp: ax.plot(self.Measurement_Time_Hours + timeshift, self.Setpoint, 
                linewidth= 2, alpha = alpha, zorder = 8, ls= lis, **setp_kwargs)
        if batt: ax.plot(self.Measurement_Time_Hours + timeshift, self.TemperatureA, 
                linewidth= 2, alpha = alpha, zorder = 10, ls= lis, **batt_kwargs)
        
        #ax.tick_params(axis='x', labelrotation=45)
        if isinstance(xlims, tuple): ax.set_xlim(*xlims)
        if isinstance(ylims, tuple): ax.set_ylim(*ylims)
        
        if VorIorP:
            ax2 = plt.twinx(ax)
            if VorIorP == 'Voltage':
                quantity = self.Voltage
                ax2.set_ylabel('Voltage [V]')
            ax2.plot(self.Measurement_Time_Hours, quantity, color= 'black', label= 'Voltage')
            
        ax.set_ylabel('Temperature [K]')
        ax.set_xlabel('Time [h]')
        if legend: fig.legend(bbox_to_anchor= (.25, .27))
    
        
    def plot_T_t_3D(self, fig, ax, lis, z, color):    
        alpha = 1
        
        X = self.Measurement_Time_Hours
        Y = self.TemperatureA
        Z = np.ones(len(self.TemperatureA))*z
        
        lw = .8
        ax.plot(np.ones(2)*self.Measurement_Time_Hours[0], np.ones(2)*z,  np.array([self.TemperatureA[0], 150]),
                linewidth= lw, color= color)
        ax.plot(np.ones(2)*np.array(self.Measurement_Time_Hours)[-1], np.ones(2)*z,  np.array([np.array(self.TemperatureA)[-1], 150]),
                linewidth= lw, color= color)
        ax.plot([self.Measurement_Time_Hours[0], np.array(self.Measurement_Time_Hours)[-1]], 
                np.ones(2)*z,  
                [150]*2,
                linewidth= lw, color= color)
        
        ax.plot(self.Measurement_Time_Hours, Z, self.TemperatureA, 
                linewidth= 2, alpha = alpha, ls= lis, label = self.ID + ' (' + self.batt_type + ')', color= color,)
        
        ax.set_xlabel('Time [h]', labelpad=20)
        ax.set_zlabel('Temperature [K]')
        #ax.legend()
        
        # N = len(self.TemperatureA)
        # verts = [[(X[0], z, 150), *zip(X, Z, Y), (X[len(X)-1], z, 150)]]

        # poly = Poly3DCollection(verts, alpha = .1)
        # # ax.add_collection3d(poly)
        # # poly.set_zsort('min')
        
        
        #ax.tick_params(axis='x', labelrotation=45)

    def half_curve(self, fig, ax, VorIorP, color, show_times = False, maxquantity= False, half= 1, lis= '-'):
        quantity, quantity_1st_half, quantity_2nd_half, TemperatureA_1st_half, TemperatureA_2nd_half, Measurement_Time_1st_half, Measurement_Time_2nd_half = self.split_data_VorIorP(VorIorP)
            
        # wykresy
        factor = (1 + ((1e3 - 1)*(VorIorP=='Current')) + ((1e3-1)*(VorIorP=='Power')))
        
        Y_1st_half = np.array(quantity_1st_half*factor)
        Y_2nd_half = np.array(quantity_2nd_half*factor)
        Y_1st_half *= 1/Y_1st_half.max()
        Y_2nd_half *= 1/Y_2nd_half.max()
        
        if half == 1: ax.plot(TemperatureA_1st_half, Y_1st_half, linewidth= 2, 
                                label= self.ID + ' (' + self.batt_type + ')', ls= lis, color= color)
        if half == 2: ax.plot(TemperatureA_2nd_half, Y_2nd_half, linewidth= 2, 
                                label= self.ID + ' (' + self.batt_type + ')', ls= lis, color= color)
        
        ax.set_xlabel('TemperatureA of battery [K]')
        if VorIorP == 'Voltage': ax.set_ylabel('Voltage [V]')
        if VorIorP == 'Current': ax.set_ylabel('Current [mA]')
        if VorIorP == 'Power': ax.set_ylabel('Power [mW]')
                        
        ax.legend(loc = 'lower right')
            
    def half_curve_3D(self, fig, ax, VorIorP, color, z, show_times = False, maxquantity= False, half= 1, lis= '-'):
        quantity, quantity_1st_half, quantity_2nd_half, TemperatureA_1st_half, TemperatureA_2nd_half, Measurement_Time_1st_half, Measurement_Time_2nd_half = self.split_data_VorIorP(VorIorP)
        
        # wykresy
        factor = (1 + ((1e3 - 1)*(VorIorP=='Current')) + ((1e3-1)*(VorIorP=='Power')))
        
        Y_1st_half = np.array(quantity_1st_half*factor)
        Y_2nd_half = np.array(quantity_2nd_half*factor)
        Y_1st_half *= 1/Y_1st_half.max()
        Y_2nd_half *= 1/Y_2nd_half.max()
        
        if half == 1:
            X = TemperatureA_1st_half
            Y = Y_1st_half
            Z = np.ones(len(TemperatureA_1st_half))*z
        elif half == 2:
            X = TemperatureA_2nd_half
            Y = Y_2nd_half
            Z = np.ones(len(TemperatureA_2nd_half))*z
        
        if half == 1: ax.plot(X, Z, Y, linewidth= 2,
                                label= self.ID + ' (' + self.batt_type + ')', ls= lis, color= color)
        if half == 2: ax.plot(X, Z, Y, linewidth= 2,
                                label= self.ID + ' (' + self.batt_type + ')', ls= lis, color= color)
        
        lw = .8
        #ax.plot(np.ones(2)*X[0], np.ones(2)*z,  np.array([Y.min(), Y.max()]), linewidth= lw, color= color)
        ax.plot([X[0], np.array(X)[-1]], 
                np.ones(2)*z,  
                [Y.min()]*2,
                linewidth= lw, color= color)
        
        ax.set_xlabel('TemperatureA of battery [K]')
        if VorIorP == 'Voltage': ax.set_zlabel('Voltage/max(Voltage')
        if VorIorP == 'Current': ax.set_zlabel('Current/max(Current)')
        if VorIorP == 'Power': ax.set_zlabel('Power/max(Power)')
                        
        ax.legend(loc = 'lower right')
            
    def T90vsDate(self, fig, ax, VorIorP, batt_date, marker):
        if VorIorP == 'Voltage': 
            T10 = self.T10U
            T90 = self.T90U
            T10huge, T10small = self.T10Uhuge - self.T10U, self.T10U - self.T10Usmall
            T90huge, T90small = self.T90Uhuge - self.T90U, self.T90U - self.T90Usmall
            # print(T10huge, T10small)
            # print(T90huge, T90small)
        if VorIorP == 'Power': 
            T10 = self.T10P
            T90 = self.T90P
            T10huge, T10small = self.T10Phuge - self.T10P, self.T10P - self.T10Psmall
            T90huge, T90small = self.T90Phuge - self.T90P, self.T90P - self.T90Psmall
        
        ax.scatter(batt_date, [T90], marker= marker, zorder= 9, s= 300)
        ax.annotate( self.batt_type, (batt_date, T90), zorder= 10, xytext= (5, 7), textcoords='offset points', fontsize = 14)
        #ax.errorbar(batt_date, [T90], yerr= [[T90small], [T90huge]], capsize= 10)
    
    def phase_changes(self, fig, ax, lims:tuple):
        NT = len(self.Measurement_Time_Hours)
        cooling_time = np.array( self.Measurement_Time_Hours[int(lims[0]*NT):int(lims[1]*NT)] )
        cooling_temperature = np.array( self.TemperatureA[int(lims[0]*NT):int(lims[1]*NT)] )
        cooling_voltage = np.array( self.Voltage[int(lims[0]*NT):int(lims[1]*NT)] )
        
        heating_time = np.array( self.Measurement_Time_Hours[int(lims[2]*NT):int(lims[3]*NT)] )
        heating_temperature = np.array( self.TemperatureA[int(lims[2]*NT):int(lims[3]*NT)] )
        heating_voltage = np.array( self.Voltage[int(lims[2]*NT):int(lims[3]*NT)] )
        
        def fun(x, a, b):
            return b*x + a
        fit = curve_fit(fun, cooling_time, cooling_temperature)
        params = fit[0]
        ax0 = ax[0]
        
        ax1 = ax0.twinx()
        ax2 = ax0.twinx()
        ax1.spines["right"].set_position(("outward", 60))
        
        ax1.scatter(cooling_time, cooling_temperature, s= 15, color= 'gray', label= 'Temperature of battery')
        ax1.plot(cooling_time, fun(cooling_time, *params), color= 'black', label= 'Fit')
        ax1.set_ylabel('Temperature of battery [K]')
        ax1.set_xlabel('Time [h]')
        
        time_c_90 = cooling_time[np.argmin( abs( cooling_voltage - .9*cooling_voltage.max() ) )]
        ax0.fill_between([time_c_90, cooling_time[-1]], [cooling_voltage[0]]*2, [cooling_voltage[-1]]*2, alpha= .17, color = 'red', label= 'beneath 90% of $U_{max}$')
        ax0.fill_between([time_c_90, cooling_time[0]], [cooling_voltage[0]]*2, [cooling_voltage[-1]]*2, alpha= .17, color = 'green', label= 'above 90% of $U_{max}$')
        ax0.plot(cooling_time, cooling_voltage, color= 'brown', label= 'Battery voltage')
        ax0.set_ylabel('Voltage [V]')
        
        ax2.scatter(cooling_time, cooling_temperature - fun(cooling_time, *params),
                    s= 10, color= 'magenta', marker= '^', label= 'Temperature of battery - fit')
        ax2.set_ylabel('$\Delta$ Temperature [K]')
        
        
        fit = curve_fit(fun, heating_time, heating_temperature)
        params = fit[0]
        ax01 = ax[1]
        
        
        ax11 = ax01.twinx()
        ax21 = ax01.twinx()
        ax11.spines["right"].set_position(("outward", 60))
        
        ax11.scatter(heating_time, heating_temperature, s= 15, color= 'gray')
        ax11.plot(heating_time, fun(heating_time, *params), color= 'black')
        ax11.set_ylabel('Temperature of battery [K]')
        ax11.set_xlabel('Time [h]')
        
        time_h_90 = heating_time[np.argmin( abs( heating_voltage - .9*cooling_voltage.max() ) )]
        ax01.fill_between([time_h_90, heating_time[0]], [heating_voltage[-1]]*2, [heating_voltage[0]]*2, alpha= .17, color = 'red')
        ax01.fill_between([time_h_90, heating_time[-1]], [heating_voltage[-1]]*2, [heating_voltage[0]]*2, alpha= .17, color = 'green')
        ax01.plot(heating_time, heating_voltage, color= 'brown')
        ax01.set_ylabel('Voltage [V]')
        
        ax21.scatter(heating_time, heating_temperature - fun(heating_time, *params),
                    s= 10, color= 'magenta', marker= '^')
        ax21.set_ylabel('$\Delta$ Temperature [K]')
        
    
    
    
        
    def cut_garbage(self, up_boundary = 400, down_boundary = 140):
        mask = np.array(self.TemperatureB < up_boundary)*np.array(self.TemperatureA < up_boundary)*np.array(self.TemperatureB > down_boundary)*np.array(self.TemperatureA > down_boundary)
        self.TemperatureB = self.TemperatureB[mask]
        self.TemperatureA = self.TemperatureA[mask]
        self.Measurement_Time = self.Measurement_Time[mask]
        self.Measurement_Time_Hours = self.Measurement_Time_Hours[mask]
        self.Voltage = self.Voltage[mask]
        self.Current = self.Current[mask]
        self.Heater_Power = self.Heater_Power[mask]
        self.Batt_Power = self.Batt_Power[mask]
        self.Setpoint = self.Setpoint[mask]   
    

    
# def plot_T_t_fragment(self, fig, axs, start, stop):        
#     mask = (self.Measurement_Time > start) & (self.Measurement_Time < stop)
#     axs[0].scatter(self.Measurement_Time[mask], self.Setpoint[mask], color= 'orange', s = 5*self.markersize, label = 'Setpoint')
#     axs[0].scatter(self.Measurement_Time[mask], self.TemperatureB[mask], color= 'purple', s = self.markersize, label = 'Temperature of probe')
#     axs[0].set_xlabel('Time [s]')
#     axs[0].set_ylabel('Temperature B of probe')
#     axs[0].tick_params(axis='x', labelrotation=45)
#     axs[0].legend()
    
#     axs[1].scatter(self.Measurement_Time[mask], self.Setpoint[mask], color= 'orange', s= 5*self.markersize, label = 'Setpoint')
#     axs[1].scatter(self.Measurement_Time[mask], self.TemperatureA[mask], color = 'purple', s= self.markersize, label = 'Temperature of battery')
#     axs[1].set_xlabel('Time [s]')
#     axs[1].set_ylabel('Temperature A of battery')
#     axs[1].tick_params(axis='x', labelrotation=45)
#     axs[1].legend()
    
    
# def plot_VandI_t_fragment(self, fig, axs, start, stop):        
#     mask = (self.Measurement_Time > start) & (self.Measurement_Time < stop)
#     axs[0].scatter(self.Measurement_Time[mask], self.Voltage[mask], color= 'orange', s = 2*self.markersize, label = 'Voltage')
#     axs[0].set_xlabel('Time [s]')
#     axs[0].set_ylabel('Voltage [V]')
#     axs[0].tick_params(axis='x', labelrotation=45)
#     axs[0].legend()
    
#     axs[1].scatter(self.Measurement_Time[mask], self.Current[mask], color= 'orange', s= 2*self.markersize, label = 'Current')
#     axs[1].set_xlabel('Time [s]')
#     axs[1].set_ylabel('Current [A]')
#     axs[1].tick_params(axis='x', labelrotation=45)
#     axs[1].legend()

