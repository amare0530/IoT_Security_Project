#!/usr/bin/env python3
import sqlite3
import statistics

conn = sqlite3.connect('artifacts/zenodo_sensors.db')
cursor = conn.cursor()

# Get temperature and voltage statistics
cursor.execute('SELECT temperature_c, supply_proxy FROM crp_records WHERE dataset_name = ?', 
               ('zenodo-tima-sensors',))
rows = cursor.fetchall()

temps = [float(r[0]) for r in rows if r[0] and r[0] != '0']
voltages = [float(r[1]) for r in rows if r[1] and r[1] != 'unknown']

print('TEMPERATURE ANALYSIS')
print(f'  Records: {len(temps)}')
print(f'  Min: {min(temps):.2f}C')
print(f'  Max: {max(temps):.2f}C')
print(f'  Mean: {statistics.mean(temps):.2f}C')
print(f'  StdDev: {statistics.stdev(temps):.2f}C')
print(f'  Range: {max(temps) - min(temps):.2f}C')

print()
print('VOLTAGE ANALYSIS')
print(f'  Records: {len(voltages)}')
print(f'  Min: {min(voltages):.5f}V')
print(f'  Max: {max(voltages):.5f}V')
print(f'  Mean: {statistics.mean(voltages):.5f}V')
print(f'  StdDev: {statistics.stdev(voltages):.5f}V')
print(f'  Range: {max(voltages) - min(voltages):.5f}V')

# Check unique devices
cursor.execute('SELECT COUNT(DISTINCT device_id) FROM crp_records WHERE dataset_name = ?',
               ('zenodo-tima-sensors',))
unique_devices = cursor.fetchone()[0]
print()
print(f'UNIQUE DEVICES: {unique_devices}')

conn.close()
