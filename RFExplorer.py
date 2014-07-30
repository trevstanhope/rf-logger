#!/usr/bin/env python

"""
RFExplorer API
"""

__author__ = 'Trevor Stanhope'
__version__ = 0.1

# Modules
import serial
import os
import time
import binascii

# Commands
GO = '#' + chr(0x04) + 'C0'
STOP = '#' + chr(0x04) + 'CH'
LCD_OFF = '#' + chr(0x04) + 'L0'
LCD_ON = '#' + chr(0x04) + 'L1'
SHUTDOWN = '#' + chr(0x04) + 'CS' # SHUTDOWN DOESN'T WORK RELIABLY 
        
class RFExplorer:

    def __init__(self, port):   
        """
        Instantiates an RFExplorer instance.
        Args:
            port: the 'cleaned' com port from 'getRFExplorerPort'
        Returns:
            ser: A serial.Serial object.
            freq_list: None
        Raises:
            SerialException: could not open port [COMport]: [Error 2] The system cannot find the file specified.
        """ 
        self.port = port
        ser = serial.Serial(port)
        ser.baudrate = 500000
        ser.timeout = 5
        self.ser = ser
        self.freq_list = None

    def initialize_RFE_connection(self):
        """
        Starts the RF Explorer sending data.
        Args:
            None
        Returns:
            device_info: a list of the device's info
        Raises:
            ValueError:"RFE returned a value that was not '4L'"
        """
        try:
            s = self.ser.write(GO)
        except:
            raise ValueError("RFE returned a value that was not '4L'")
        response = self.ser.readline().split(':') # Check if everything is A-OK before collecting data
        if response[0] != '#C2-M': # We know this is NOT the Current_Setup key.
            ready = False
            while ready == False: # Keep closing/reopening and flushing com port to get back to square one
                self.ser.write(STOP)
                self.ser.close()
                print 'sleeping'
                time.sleep(0.25)
                print 'trying again'
                self.ser.open()
                self.ser.flushInput()
                self.ser.write(GO)
                response = self.ser.readline().split(':')
                if response[0] == '#C':
                    ready = True
        RFE_info = response[1] # Don't know if the RFE info matters, but can collect it here
        return RFE_info
        
    def parse_C2_F_response(self):  
        """
        Gives Frequency List from a C2 F response from the device
        Args:
            None
        Returns:
            freq_list: a list of the 112 frequencies that are being swept
        Raises:
            NameError: Means that self.ser.readline() is not providing a C2F 
        """        
        # Now that we have the first info line, the next line should be the Current_Config
        request_config = self.ser.readline().split(':')
        if request_config[0] == '#C2-F': # We know this is the Current_Config key
            request_config = request_config[1].split(',')
            initStart_Freq = int(request_config[0]) * 1000 # MAKE THIS Hz
            initFreq_Step = int(request_config[1]) # in Hz
            initAmp_Top = request_config[2]
            initAmp_Bottom = request_config[3]
            initSweep_Steps = int(request_config[4])
            initExpModuleStatus = request_config[5]
            initCurrentMode = request_config[6]
            initMin_Freq = request_config[7]
            initMax_Freq = request_config[8]
            initMax_Span = request_config[9]
            initResBandWidth = int(request_config[10])
            initSpan = initFreq_Step * initSweep_Steps
            initEndFreq = initStart_Freq + initSpan
            initCenterFreq = initStart_Freq + (initSpan/2)
            freq_list = [str(initStart_Freq)]
            for freq in range(1, int(initSweep_Steps)): 
                freq_list.append(str(int(freq_list[freq-1]) + int(initFreq_Step))) # Add a new list entry which is initFreq_Step greater than the previous list entry
            self.freq_list = freq_list
            return freq_list
        else:
            raise NameError("C2F value is not present in the serial port's queue")
            
    def collect_data(self):
        """
        Args:
            self
        Returns:
            final_results: a list of the 112 data point values to correspond with the freq_list above
        Raises:
            SerialException:None
            Used to break a while loop if all has gone to hell
            ValueError: If the conversion of datapoints fails for a specific 
        """
        first = self.ser.readline()
        if not first.startswith('$S'):
            not_ready = True
            while not_ready == True:
                results = self.ser.readline()
                if results.startswith('$S'):
                    not_ready = False
                elif not results.startswith('#'):
                    break
                    raise serial.SerialException
        else:
            results = first
        results = str(results).split('$S')[1] # Read one line to check for the weird readline() hex or ascii to see what's in the string
        if results.startswith('p'): # Now we know we've got good data
            results = results.split('p')[1]
            separated = []
            for i in results:
                separated.append(ord(i))
            if separated[-1] == 10:
                separated.pop()
                if separated[-1] == 13:
                    separated.pop()    
            final_results = []
            for i in separated:
                i = (int(i)/2)*-1 # Convert to dBm
                final_results.append(i) 
            if len(final_results) != 112:
                final_results = None
        else: # Try again it'll probably work
            final_results =  None
        return final_results
            
    def compile_dictionary(self, values):
        freq_dict = {}
        for indx, freq in enumerate(self.freq_list):
            freq_dict[freq] = values[indx]
        return freq_dict
                     
    def stop_please(self):
        self.ser.write(STOP)
        time.sleep(0.25)
        self.ser.close()
        time.sleep(0.25)
        self.ser.open()
        time.sleep(0.25)
        self.ser.flushInput()
        
    def set_sweep_params(self, start_freq, end_freq, amp_top, amp_bottom):
        """
        Args:
            self
            start_freq: 7 digit value in kHz. Can be between 0240000 and 0959888
            end_freq: 7 digit value in kHz. Can be between 0241112 and 0960000
            amp_top: 4 digit value in dBm include the +/- sign. Between -110 and +005  
            amp_bottom: 4 digit value in dBm include the +/- sign. Between -120 and -005 
        Returns:
            boolean: True designates a successful change of parameters
        Raises:
            ValueError: Incorrect Value submitted
            ValueError: Length of Value is not correct
            ValueError: Write to RFE Failed
        """
        if int(start_freq) < 15000 or int(start_freq) > 27000000:
            raise ValueError("start_freq not in bounds")
        if int(end_freq) < 15000 or int(end_freq) > 27000000:
            raise ValueError("end_freq not in bounds")
        if int(amp_top) < -110 or int(amp_top) > 5:
            raise ValueError("amp_top not in bounds")
        if int(amp_bottom) < -120 or int(amp_bottom) > -5:
            raise ValueError("amp_bottom not in bounds")
        start_freq = str(start_freq)
        end_freq = str(end_freq)
        amp_top = str(amp_top)
        amp_bottom = str(amp_bottom)
        if len(start_freq) < 7:
            sf_0 = 7-len(start_freq) 
            start_freq = ('0' * sf_0) + start_freq
        if len(end_freq) < 7:
            ef_0 = 7-len(end_freq) 
            end_freq = ('0' * sf_0) + end_freq
        if len(amp_top) != 4:
            raise ValueError("length of amp_top is not 4") 
        sweep_params = '#' + chr(0x20) + 'C2-F:' + start_freq + ',' + end_freq + ',' + amp_top + ',' + amp_bottom
        try:
            s = self.ser.write(sweep_params)
            return True
        except:
            raise ValueError("write to RFE failed")
        
    def quick_sweep(self, start, end):
        """
        Set the sweep settings and gather data for a specified time
        Args:
            start: 7 digit entry of starting frequency for the sweep 
            end: 7 digit entry of end frequency for the sweep
            stop_sweep: length of time in seconds for the sweep repeat and compare
        Returns:
            value_dictionary to compare with other sweep data
        """
        self.stop_please()
        top = '-010'
        bottom = '-100'
        sweep_settings = self.set_sweep_params(start, end, top, bottom)
        if sweep_settings == True:
            freq_list = self.parse_C2_F_response()
            if len(freq_list) != 112:
                raise ValueError("RFE_connection didn't initialize properly")
        else:    
            raise ValueError("RFE didn't take the sweep_settings")
        final_result = self.collect_data()
        now = time.time()
        if final_result == None: # Try this again, for a few more times...
            while time.time() < now + 30:
                final_result = self.collect_data()
                if final_result != None:
                    break
            if final_result == None:
                raise ValueError('This set of frequencies is not 112 long.')
        first_dict = self.compile_dictionary(final_result)
        return first_dict
        
    def timed_sweep(self, start,end,stop):
        """
        Set the sweep settings and gather data for a specified time
        Args:
            start: 7 digit entry of starting frequency for the sweep 
            end: 7 digit entry of end frequency for the sweep
            stop: length of time in seconds for the sweep repeat and compare
        Returns:
            value_dictionary to compare with other sweep data
        """
        self.stop_please()
        top = '-010'
        bottom = '-100'
        sweep_settings = self.set_sweep_params(start,end,top,bottom)
        if sweep_settings == True:
            freq_list = self.parse_C2_F_response()
            if len(freq_list) != 112:
                raise ValueError("RFE_connection didn't initialize properly")
        else:    
            raise ValueError("RFE didn't take the sweep_settings")
        now = time.time()
        stop_sweep = now + stop
        collection = []
        while time.time() < stop_sweep:
            final_result = self.collect_data()
            if final_result == None: # We are going to try this again, for a few more times more times.
                final_result = self.collect_data()
                if final_result == None:
                    final_result = self.collect_data()
            if final_result == None:
                raise ValueError('This set of frequencies is not 112 long.')
            for indx, val in enumerate(final_result):
                if indx in collection:
                    if val > collection[indx]:
                        collection.insert(indx,val)
                else:
                    collection.insert(indx,val)
        output_dict = self.compile_dictionary(final_result)
        return output_dict
        
    def make_csv(self, filename, freq_dict):
        """
        1. Creates the final CSV file by converting all Hz values to MHz
        2. Sorts the results dictionary and writes the file.
        Args: 
            filename: the name of the file that will be saved to the working directory
            freq_dict: a dictionary of freq in kHz, dBm value pairs
        Returns: 
            file: CSV file with filename of filename arg formatted correctly
        Raises:
        """
        if filename.endswith('.csv'):
            file = filename
        else:
            file = str(filename) + '.csv'
        fout = open(file, 'w')
        freq_dict = sorted(freq_dict.items())
        for i, v in freq_dict:
            x = ''
            for j in str(i)[0:3]:
                x += j
            x += '.'
            for j in str(i)[4:7]:
                x += j
            fout.write(str(x) + ',' + str(v) + '\n')
        fout.close()
        return True
        
    def make_list(self, freq_dict):
        """
        Sorts the results dictionary into a list
        Args: 
            freq_dict: a dictionary of freq in kHz, dBm value pairs
        Returns: 
            file: List of amplitudes
        Raises:
        """
        freq_dict = sorted(freq_dict.items())
        freq_list = []
        for i, v in freq_dict:
            freq_list.append(v)
        return freq_list
