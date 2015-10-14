from __future__ import print_function
from bluepy import btle
import myo_dicts
import struct
import socket
import json
import time
import math
import pprint
import logging as log
import subprocess
import sys
import os

# Author:
#    Max Leefer
# Source:
#    https://github.com/mamo91/Dongleless-myo
# Free to modify and use as you wish, so long as my name remains in this file.
# Special thanks to the support at Thalmic labs for their help, and to IanHarvey for bluepy

# Slight cleanup and modification by Andrey Alekseenko (al42and)

# Notes
# If the Myo is unsynced while the program is running, you will need to plug it in and let it fall asleep before poses will work again.
# Mixes up fist and wave in when worn on left arm with led toward elbow


PATH = os.getcwd()

busylog = False #decides whether emg/imu notifications will generate log messages.
log.basicConfig(filename=PATH+"/dongleless.log", filemode = 'w', level = log.CRITICAL, #change log.CRITICAL to log.DEBUG to get log messages
				format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%H:%M:%S')

class Connection(btle.Peripheral):
	def __init__(self, mac):
		btle.Peripheral.__init__(self, mac)
		self.subscribe()

	def subscribe(self):
		self.writeCharacteristic(0x24, struct.pack('<bb', 0x02, 0x00),True) # Subscribe to classifier indications
		self.writeCharacteristic(0x1d, struct.pack('<bb', 0x01, 0x00),True) # Subscribe to imu notifications
		self.writeCharacteristic(0x28, struct.pack('<bb', 0x01, 0x00),True) # Subscribe to emg notifications

	def setMode(self, emg_mode, imu_mode, classifier_mode):
		# For some reason, to enable EMG we must use mode 0x01, unlike 0x02 like myohw.h says
		self.writeCharacteristic(0x19, struct.pack('<bbbbb', 0x01, 0x03, emg_mode,imu_mode,classifier_mode) ,True)

	def setSleep(self, sleep_mode):
		"""0 - normal, 1 - never sleep"""
		self.writeCharacteristic(0x19, struct.pack('<bbb', 0x09, 0x01, sleep_mode) ,True)

	def deepSleep(self):
		self.writeCharacteristic(0x19, struct.pack('<bb', 0x04, 0x00) ,True)

	def setLeds(self, logo_r, logo_g, logo_b, line_r, line_g, line_b):
		"""The numerical value indicates blinking period of respective LED"""
		self.writeCharacteristic(0x19, struct.pack('<bbbbbbbb', 0x06, 0x06, logo_r, logo_g, logo_b, line_r, line_g, line_b),True)

	def vibrate(self, length):
		self.writeCharacteristic(0x19, struct.pack('<bbb', 0x03, 0x01, length),True)

class MyoDelegate(btle.DefaultDelegate):
	def __init__(self, bindings, myo):
		self.bindings = bindings
		self.myo = myo

	def handleNotification(self, cHandle, data):
		if cHandle == 0x23:
			log.debug("got pose notification")
			ev_type=None
			data=struct.unpack('>6b',data) #sometimes gets the poses mixed up, if this happens, try wearing it in a different orientation.
			if data[0] == 3: # Classifier
				ev_type = myo_dicts.pose[data[1]]

			elif data[0] == 1: #sync
				log.info("Arm synced")
				ev_type = "arm_synced"
				#rewrite handles
				if data[1] == 2: #left arm
					self.arm = "left"
				elif data[1] == 1: #right arm
					self.arm = "right"
				else:
					self.arm = "unknown"
				if 'arm_synced' in self.bindings:
					self.bindings['arm_synced'](self.myo, myo_dicts.x_direction[data[2]], myo_dicts.arm[data[1]])
				return

			if ev_type in self.bindings:
				self.bindings[ev_type](self.myo)

		elif cHandle == 0x1c: # IMU
			data = struct.unpack('<10h', data)
			quat = data[:4]
			accel = data[4:7]
			gyro = data[7:]
			if busylog:
				log.debug("got imu notification")
			ev_type = "imu_data"
			if "imu_data" in self.bindings:
				self.bindings["imu_data"](self.myo, quat, accel, gyro)

		elif cHandle == 0x27: # EMG
			data = struct.unpack('<8HB', data) # an extra byte for some reason
			if busylog:
				log.debug("got emg notification")
			ev_type = "emg_data"
			if "emg_data" in self.bindings:
				self.bindings["emg_data"](self.myo, data[:8])

def print_wrapper(*args):
	print(args)

#take a list of the events.
events = ("rest", "fist", "wave_in", "wave_out", "wave_left", "wave_right",
"fingers_spread", "double_tap", "unknown","arm_synced", "arm_unsynced",
"orientation_data", "gyroscope_data", "accelerometer_data", "imu_data", "emg_data")

# Bluepy is more suited to getting default values like heartrate and such, it's not great at fetching by uuid.

