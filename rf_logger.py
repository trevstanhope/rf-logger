#!/usr/bin/python
"""
Script to sweeps and outputs to a CSV file corresponding to GPS location
"""

from RFExplorer import *
import gps

def sweep_chunks(RFE, start_freq, end_freq, chunk, delay):
    """
    Creates the compiled dictionary for the band in chunks
    Args: RFExplorer instance
    Returns: compiled dictionary to feed into the CSV creator
    """
    chunks = (end_freq - start_freq) / chunk
    freq_list = [start_freq]
    for i in range(chunks - 1):
        freq_list.append(int(freq_list[i]) + chunk)
    sweep = {}
    for start in freq_list:
        end = str(int(start) + chunk)
        print 'Sweeping from %s to %s...' % (start, end)
        try:
            dict = RFE.timed_sweep(start, end, delay)
        except ValueError:
            manual_value = raw_input("Manual value entry: ")
            dict = {start : manual_value}
        for j, k in dict.iteritems():
            print j, k
            if start in sweep:
                if k > sweep[start]:
                    sweep[start] = k
            else:
                sweep[start] = k
        print('\tMax: %s' % str(sweep[start]))
    return sweep
    
if __name__ == '__main__':
    port = '/dev/ttyUSB0'
    start_freq = 100000 # kHz
    end_freq = 2700000 # kHz
    chunk = 100000 # kHz
    delay = 5 # seconds
    RFE = RFExplorer(port)
    filename = raw_input("Enter the name of the CSV file that you want generated: ")
    csvfile = open(filename, 'w')
    freqs = [start_freq + chunk * i for i in range((end_freq - start_freq) / chunk)]
    header_names = ['latitude', 'longitude']
    for i in freqs:
        header_names.append(str(i) + 'kHz')
    headers = ','.join(header_names)
    csvfile.write(headers + '\n')
    while True:
        try:
            latitude = raw_input("Latitude: ")
            longitude = raw_input("Longitude: ")
            sweep_dict = sweep_chunks(RFE, start_freq, end_freq, chunk, delay)
            print sweep_dict
            sweep_list = RFE.make_list(sweep_dict)
            print sweep_list
            sample = [str(latitude), str(longitude)]
            for i in sweep_list:
                sample.append(str(i))
            sample.append('\n')
            csvfile.write(','.join(sample))
        except KeyboardInterrupt as error:
            print str(error)
            csvfile.close()
            break
