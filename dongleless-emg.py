import datetime
import dongleless
import functools
import sys
from bluepy import btle

mac = sys.argv[1]
out_file = sys.argv[2]

def write_emg(f, myo, emg):
    f.write('E ')
    f.write(datetime.datetime.now().time().isoformat())
    f.write(' ')
    f.write(' '.join(map(str,emg)))
    f.write('\n')

def write_imu(f, myo, quat, accel, gyro):
    f.write('I ')
    f.write(datetime.datetime.now().time().isoformat())
    f.write(' ')
    f.write(' '.join(map(str,quat)))
    f.write(' ')
    f.write(' '.join(map(str,accel)))
    f.write(' ')
    f.write(' '.join(map(str,gyro)))
    f.write('\n')


out_fd = open(out_file, 'w')

function_dict = {
    "emg_data": functools.partial(write_emg, out_fd),
    "imu_data": functools.partial(write_imu, out_fd),
}

while True:
    while True:
        try:
            p = dongleless.Connection(mac)
        except btle.BTLEException:
            pass
        else:
            if p:
                break
    try:
        p.setMode(1,1,0) # Enable EMG and IMU data, disable pose classifier
        p.setSleep(1) # Disable sleep
        p.subscribe() # Subscribe to notifications
        p.setDelegate(dongleless.MyoDelegate(function_dict, p)) # Assign callbacks
        p.setLeds(0x00,0x00,0x00,0x00,0x00,0x00) # Dim LEDs
        while True:
            p.vibrate(0) # Doing this in a loop seems to somehow inhibit automatic Myo vibration
            p.waitForNotifications(3)
    except btle.BTLEException:
        pass

