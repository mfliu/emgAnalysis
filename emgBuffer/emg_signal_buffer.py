import numpy as np
import os
import socket 
import PyDragonfly
from PyDragonfly import copy_to_msg, copy_from_msg
import HX_message_defs as md 
import multiprocessing as mp 
import time
import sys
sys.path.append(os.path.abspath(os.getcwd()))
from globals import Global 


def emgBuffer():
	mm_ip = Global.MM_IP
	## Connect to MessageManager
	module = PyDragonfly.Dragonfly_Module(0, 0)
	try:
		module.ConnectToMMM(mm_ip)
	except:
		print("Could not connect to Message Manager at : ", mm_ip)
	print("Connected to Message Manager")

	PACKET_LENGTH = md.HX_EMG_SAMPLES_PER_MSG 
	FS = Global.FS
	NUM_CHANS = Global.NUM_CHANS
	BUFFER_TIME = Global.BUFFER_TIME 
	BUFFER_LENGTH =  Global.BUFFER_LENGTH
	###################################################
	## Set up memory mapped files. 
	## This is useful because both the EMG plotter and
	## recruitment curve shenanigans
	###################################################

	data_diff_path = Global.data_diff_path  #os.path.join(base_dir, 'mem_map', 'mmDataDiff.dat')
	data_diffTime_path = Global.data_diffTime_path #os.path.join(base_dir, 'mem_map', 'mmDataDiffTime.dat')

	if not os.path.exists(data_diff_path):
		with open(data_diff_path, 'w') as f:
			f.write(np.zeros(shape=(NUM_CHANS, BUFFER_LENGTH)))

	if not os.path.exists(data_diffTime_path):
		with open(data_diffTime_path, 'w') as f:
			f.write(np.zeros(shape=(1, BUFFER_LENGTH)))

	mmDiff = np.memmap(data_diff_path, dtype='float32', mode='w+', shape=(NUM_CHANS, BUFFER_LENGTH)) 
	mmDiffTime = np.memmap(data_diffTime_path, dtype='uint32', mode='w+', shape=(BUFFER_LENGTH)) 

	## Clear buffers 
	mmDiff[:] = mmDiff[:] * 0
	mmDiffTime[:] = mmDiffTime[:] * 0

	## Subscribe to Message Manager Messages
	module.Subscribe(md.MT_HX_EMG_DATA_DIFF)
	module.Subscribe(md.MT_SHUT_DOWN)

	print("Reading Messages")
	while True:
		msg = PyDragonfly.CMessage()
		module.ReadMessage(msg, 0)
		if msg.GetHeader().msg_type == md.MT_HX_EMG_DATA_DIFF:
			start = time.time()
			msg_data = md.MDF_HX_EMG_DATA_DIFF()
			copy_from_msg(msg_data, msg)
			mmDiff[:, 0:-PACKET_LENGTH] = mmDiff[:, PACKET_LENGTH:]
			mmDiff[:, -PACKET_LENGTH:] = np.transpose(np.reshape(msg_data.data, newshape=(PACKET_LENGTH, NUM_CHANS)))
			mmDiffTime[0:-PACKET_LENGTH] = mmDiffTime[PACKET_LENGTH:]
			mmDiffTime[-PACKET_LENGTH:] = msg_data.source_timestamp

		if msg.GetHeader().msg_type == md.MT_SHUT_DOWN:
			module.DisconnectFromMMM()
			print("Emergency Stop")
			print("Dragonfly Thread Closed")
			break

# Test
if __name__ == "__main__":
	emgBuffer() #mm_ip="192.168.50.10:7111", base_dir="C:\Users\liufe\Documents\Grad_School\EMG_MemMap_Test")


