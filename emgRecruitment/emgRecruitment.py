##### Imports ##########
## kivy imports
import kivy
kivy.require('1.9.1')
from kivy import Config
Config.set('graphics', 'multisamples', '0')
Config.set('graphics', 'width', 1400)
Config.set('graphics', 'height', 700)
Config.set('graphics', 'resizable', False)
Config.set('graphics', 'kivy_clock', 'interrupt')
import matplotlib
matplotlib.use('module://kivy.garden.matplotlib.backend_kivy') # so that kivy can plot figures
from kivy.uix.widget import Widget
from kivy.app import App
from kivy.uix.image import Image 
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
Clock.max_iteration = 40

## Dragonfly imports
import PyDragonfly
from PyDragonfly import copy_to_msg, copy_from_msg
import HX_message_defs as md 

## Standard Python/NumPy/SciPy imports
import multiprocessing as mp
from threading import Thread
import os
import sys 
import numpy as np
import time
from scipy import signal
sys.path.append(os.path.abspath(os.getcwd()))
from globals import Global 
import multiprocessing
import Queue


global NUM_PLOT_PULSES
NUM_PLOT_PULSES = 50



class RecruitmentAnalysis(BoxLayout):
	def __init__(self, **kwargs):
		super(RecruitmentAnalysis, self).__init__(**kwargs)

		self.muscles = ['TF', 'RF', 'VL', 'TA', 'SO', 'SE', 'BF', 'LG']
		self.mod = PyDragonfly.Dragonfly_Module(0, 0)
		try:
			self.mod.ConnectToMMM(MM_IP)
		except:
			print("EMG Recruitment could not connect to Message Manager.")
		print("EMG Recruitment connected to Message Manager")
		

		self.mod.Subscribe(md.MT_SHUT_DOWN)
		self.mod.Subscribe(md.MT_OL_SPINALLEAD_STIMCONFIG)
		self.mod.Subscribe(md.MT_STIM_TIMES)

		self.data_diff_path = Global.data_diff_path #"R:/users/mfl24/research_code/mem_map/mmDataDiff.dat" #os.path.join(base_dir, 'mem_map', 'mmDataDiff.dat')
		self.data_diffTime_path = Global.data_diffTime_path #"R:/users/mfl24/research_code/mem_map/mmDataDiffTime.dat" #os.path.join(base_dir, 'mem_map', 'mmDataDiffTime.dat')

		self.currentStim = ()
		self.stimDict = {}
		self.stimMeanPulse = {}
		self.currentPulse = np.zeros((NUM_PLOT_PULSES, 16, int(1.5*FS)))

		self.listener = Thread(target=self.listener)
		self.listener.daemon = True
		self.listener.start()


	def listener(self):
		PACKET_LENGTH = md.HX_EMG_SAMPLES_PER_MSG 
		mmDiff = np.memmap(self.data_diff_path, dtype='float32', mode='r', shape=(NUM_CHANS, BUFFER_LENGTH))
		mmDiffTime = np.memmap(self.data_diffTime_path, dtype='uint32', mode='r', shape=(BUFFER_LENGTH)) 
		while True:
			msg = PyDragonfly.CMessage()
			self.mod.ReadMessage(msg, 0)
			if msg.GetHeader().msg_type == md.MT_SHUT_DOWN:
				msg_data = md.MDF_SHUT_DOWN()
				self.mod.DisconnectFromMMM()
				print("Emergency stop; Dragonfly thread closed")
			
			elif msg.GetHeader().msg_type == md.MT_OL_SPINALLEAD_STIMCONFIG:
				msg_data = md.MDF_OL_SPINALLEAD_STIMCONFIG()
				copy_from_msg(msg_data, msg)
				acratio = msg_data.acratio
				elecID = np.array(msg_data.elecID[:])
				elec = np.array(msg_data.elec[:])
				amp = np.array(msg_data.amp[:])
				freq = np.array(msg_data.freq[:])
				pw = np.array(msg_data.width[:])
				dur = np.array(msg_data.dur[:])

				stimParams = list(np.concatenate((elecID, elec, amp, freq, pw, dur)))
				stimParams = tuple(stimParams)
				self.currentStim = stimParams
				if stimParams not in self.stimDict.keys():
					self.stimDict[stimParams] = np.zeros((17, 1))
				if stimParams not in self.stimMeanPulse.keys():
					self.stimMeanPulse[stimParams] = np.zeros((16, int(1.5*FS)))

				## update labels
				(veUnique, veUniqueIDX) = np.unique(elecID, return_index = True)
				elecString = ""
				ampString = ""
				freqString = ""
				pwString = ""
				durString = ""
				for i in range(0, len(veUniqueIDX)):
					veIDX = veUniqueIDX[i]
					veID = elecID[veIDX]
					if veID > 0:
						veElec = elec[np.where(elecID == veID)]
						veAmp = amp[np.where(elecID == veID)]
						veFreq = freq[veIDX]
						vePW = pw[veIDX]
						veDur = dur[np.where(elecID == veID)]
						elecString = elecString + str(veID) + ": " + str(veElec) + "\n"
						ampString = ampString + str(veAmp) + "\n"
						freqString = freqString + str(veFreq) + "\n"
						pwString = pwString + str(vePW) + "\n"
						durString = durString + str(veDur) + "\n"
				Clock.schedule_once(lambda dt: self.update_labels(elecString, ampString, freqString, pwString, durString))
			
			elif msg.GetHeader().msg_type == md.MT_STIM_TIMES:
				msg_data = md.MDF_STIM_TIMES()
				copy_from_msg(msg_data, msg)
				stimTimes = np.array(msg_data.stimTimes[:])
				stimTimes = stimTimes[np.where(stimTimes != 99)]
				msg_data = md.MDF_STIM_TIMES()
				copy_from_msg(msg_data, msg)
				stimTimes = np.array(msg_data.stimTimes[:])
				stimTimes = stimTimes[np.where(stimTimes != 99)]
				time.sleep(1)
				
				mmEmgTime = mmDiffTime.copy()
				emgData = mmDiff.copy()

				b, a = signal.butter(4, 0.1, 'highpass')
				filtEMG = signal.filtfilt(b, a, emgData[0:16, :], axis = 1)

				rms_window = self.get_root_window().children[-1].ids['rmsWindow'].value/1000.0

				emgRMS = self.stimDict[self.currentStim]
				emgMean = self.stimMeanPulse[self.currentStim]
				self.currentPulse = np.zeros((NUM_PLOT_PULSES, 16, int(1.5*FS)))
				for s_idx in range(0, len(stimTimes)):
					stimTime = stimTimes[s_idx]

					emgTime = np.argmin(np.abs(mmEmgTime-stimTime)).astype(int)
					emgStart = int(max(0, emgTime - (FS * rms_window)))
					emgEnd = int(min(BUFFER_LENGTH, emgTime + (FS*rms_window)))
					emgPreWindow = filtEMG[:, emgStart:emgTime]
					emgPostWindow = filtEMG[:, emgTime:emgEnd]
					pulsePreRMS = np.reshape(np.sqrt(np.mean(np.square(emgPreWindow), 1)), (16,1))
					pulsePostRMS = np.reshape(np.sqrt(np.mean(np.square(emgPostWindow), 1)), (16, 1))
					pulseRMS = pulsePostRMS - pulsePreRMS
					
					## multiply running average by previous number of pulses, add current pulse, divide by num_pulses + 1
					emgRMS[1:] = ((emgRMS[1:] * emgRMS[0]) + pulseRMS)/(emgRMS[0] + 1)
					
					pulseStart = int(max(emgTime-0.5*FS, 0))
					pulseEnd = int(min(emgTime+FS, BUFFER_LENGTH))
					emgPulse = np.zeros((16, int(1.5*FS)))
					emgPulse[:, :pulseEnd-pulseStart] = np.array(filtEMG[:, pulseStart:pulseEnd])
					
					emgMean = ((emgMean * emgRMS[0]) + emgPulse)/(emgRMS[0] + 1)
					emgRMS[0] = emgRMS[0] + 1

					if s_idx < NUM_PLOT_PULSES:
						self.currentPulse[s_idx, :, :] = emgPulse

				self.stimDict[self.currentStim] = emgRMS
				self.stimMeanPulse[self.currentStim] = emgMean
				
				recGraph = self.get_root_window().children[-1].ids['recGraph']
				recGraph.set_data(self.stimDict, self.stimMeanPulse, self.currentStim, self.currentPulse)
				Clock.schedule_once(lambda dt:recGraph.update_plots(), 0.1)
			time.sleep(0.001)

	def update_labels(self, elecString, ampString, freqString, pwString, durString):
		elecLabel = self.get_root_window().children[-1].ids['stimParamsElectrode']
		pwLabel = self.get_root_window().children[-1].ids['stimParamsPW']
		ampLabel = self.get_root_window().children[-1].ids['stimParamsAmp']
		freqLabel = self.get_root_window().children[-1].ids['stimParamsFreq']
		durLabel = self.get_root_window().children[-1].ids['stimParamsDur']
		elecLabel.text = elecString
		pwLabel.text = pwString
		ampLabel.text = ampString
		freqLabel.text = freqString
		durLabel.text = durString

	def get_stimDict(self):
		return self.stimDict

	def get_stimMeanPulseDict(self):
		return self.stimMeanPulse

	def get_currentStimParams(self):
		return self.currentStim

	def get_currentPulse(self):
		return self.currentPulse

class RecruitmentGraph(BoxLayout):
	def __init__(self, **kwargs):
		super(RecruitmentGraph, self).__init__(**kwargs)
		self.muscles = ['TFL', 'RF', 'VL', 'BF', 'SE', 'TA', 'SO', 'LG']
		self.sides = ["Left", "Right"]
		self.pulseMuscle_idx = 0
		self.recLines_idx = []
		self.leftXvar = ""
		self.rightXvar = ""
		self.leftXdata = np.array([])
		self.leftYdata = np.array([])
		self.rightXdata = np.array([])
		self.rightYdata = np.array([])
		self.meanPulseData = np.array([])
		self.currPulseData = np.array([])
		self.init_plots()

	def init_plots(self):
		fig = plt.figure(facecolor=(0.3, 0.3, 0.3))
		plt.subplots_adjust(left=0.05, right=0.98, wspace=0.2)
		for side_i in range(0, len(self.sides)): ## side_i, get it?
			ax = fig.add_subplot(1, 3, side_i + 1)
			ax.spines['bottom'].set_color('white')
			ax.spines['top'].set_color('white')
			ax.spines['left'].set_color('white')
			ax.spines['right'].set_color('white')
			ax.tick_params(length=0, color='white', labelsize=8, labelcolor='white')
			ax.set_title(self.sides[side_i] + ' Recruitment Curve', color='w', pad=2)
			ax.set_facecolor((0.3, 0.3, 0.3))
			ax.set_xticks([]) #np.arange(0, 10000, 1000))
			ax.set_yticks([]) #np.arange(0, 10000, 1000))
			for m in self.muscles:
				ax.plot([], '.', label=m)
			leg = ax.legend(self.muscles, facecolor=(0.3, 0.3, 0.3), edgecolor='white')
			plt.setp(leg.get_texts(), color='white')

		pulse_ax = fig.add_subplot(1, 3, 3)
		pulse_ax.spines['bottom'].set_color('white')
		pulse_ax.spines['top'].set_color('white')
		pulse_ax.spines['left'].set_color('white')
		pulse_ax.spines['right'].set_color('white')
		pulse_ax.tick_params(length=0, color='white', labelsize=8, labelcolor='white')
		pulse_ax.set_title('EMG Stim Pulses', color='w', pad=2)
		pulse_ax.set_facecolor((0.3, 0.3, 0.3))
		pulse_ax.set_xticks([])
		pulse_ax.set_yticks([])
		for i in range(0, NUM_PLOT_PULSES):
			pulse_ax.plot([], '-', linewidth=1, color="#0471A6")
		pulse_ax.plot([], '-', linewidth=1, color="#FB3640")
		fig_handle = FigureCanvas(fig)
		fig_handle.blit()
		fig_handle.draw()					
		self.add_widget(fig_handle)
		self.recruitmentHandle = fig_handle

	def get_plot_settings(self):
		leftX = self.get_root_window().children[-1].ids['leftX'].text
		leftXmin = self.get_root_window().children[-1].ids['leftXmin'].value
		leftXmax = self.get_root_window().children[-1].ids['leftXmax'].value
		leftYmin = self.get_root_window().children[-1].ids['leftYmin'].value
		leftYmax = self.get_root_window().children[-1].ids['leftYmax'].value

		rightX = self.get_root_window().children[-1].ids['rightX'].text
		rightXmin = self.get_root_window().children[-1].ids['rightXmin'].value
		rightXmax = self.get_root_window().children[-1].ids['rightXmax'].value
		rightYmin = self.get_root_window().children[-1].ids['rightYmin'].value
		rightYmax = self.get_root_window().children[-1].ids['rightYmax'].value

		pulseX = self.get_root_window().children[-1].ids['pulseX'].value
		pulseY = self.get_root_window().children[-1].ids['pulseY'].value

		return (leftX, leftXmin, leftXmax, leftYmin, leftYmax, rightXmin, rightXmax, rightYmin, rightYmax, pulseX, pulseY)

	def update_axes(self):
		(leftX, leftXmin, leftXmax, leftYmin, leftYmax, rightXmin, rightXmax, rightYmin, rightYmax, pulseX, pulseY) = self.get_plot_settings()
		recFig = self.recruitmentHandle
		leftAxes = recFig.figure.axes[0]
		rightAxes = recFig.figure.axes[1]
		pulseAxes = recFig.figure.axes[2]
		
		leftXaxes = leftAxes.get_xlim()
		leftYaxes = leftAxes.get_ylim()
		rightXaxes = rightAxes.get_xlim()
		rightYaxes = rightAxes.get_ylim()
		pulseXaxes = pulseAxes.get_xlim()
		pulseYaxes = pulseAxes.get_ylim()

		need_update = False
		if leftXaxes[0] != leftXmin or leftXaxes[1] != leftXmax:
			need_update = True
			leftAxes.set_xlim(leftXmin, leftXmax)
		if leftYaxes[0] != leftYmin or leftYaxes[1] != leftYmax:
			need_update = True
			leftAxes.set_ylim(leftYmin, leftYmax)

		if rightXaxes[0] != rightXmin or rightXaxes[1] != rightXmax:
			need_update = True
			rightAxes.set_xlim(rightXmin, rightXmax)
		if rightYaxes[0] != rightYmin or rightYaxes[1] != rightYmax:
			need_update = True
			rightAxes.set_ylim(rightYmin, rightYmax)

		if pulseXaxes[1] != pulseX:
			need_update = True
			pulseAxes.set_xlim(-1*pulseX, pulseX)
		if pulseYaxes[1] != pulseY: 
			need_update = True
			pulseAxes.set_ylim(-1*pulseY, pulseY)

		if need_update == True:
			recFig.blit()
			recFig.draw()
	
	def update_rms_sliders(self, spinner_name):
		value = self.get_root_window().children[-1].ids[spinner_name].text
		if spinner_name == "leftX" or spinner_name == "rightX":
			if spinner_name == "leftX":
				self.leftXvar = value
			elif spinner_name == "rightX":
				self.rightXvar = value
			x_min = self.get_root_window().children[-1].ids[spinner_name + 'min']
			x_max = self.get_root_window().children[-1].ids[spinner_name + 'max']
			if value == "Amplitude":
				x_min.min = 0
				x_min.max = 5000
				x_min.step = 1000
				x_max.min = 2000
				x_max.max = 10000
				x_max.step = 1000
			elif value == "Frequency":
				x_min.min = 0
				x_min.max = 500
				x_min.step = 10
				x_max.min = 500
				x_max.max = 1000
				x_max.step = 10
			elif value == "Pulse-Width":
				x_min.min = 0
				x_min.max = 500
				x_min.step = 100
				x_max.min = 500
				x_max.max = 1000
				x_max.step = 100
			elif value == "Duration":
				x_min.min = 0
				x_min.max = 2500
				x_min.step = 100
				x_max.min = 2500
				x_max.max = 5000
				x_max.step = 100
		elif spinner_name == "pulseMuscle":
			side, muscle = value.split(" ") 
			m_idx = self.muscles.index(muscle)
			if side == "Left":
				m_idx = m_idx + 8
			self.pulseMuscle_idx = m_idx

		recAnalysis = self.get_root_window().children[-1]
		self.set_data(recAnalysis.get_stimDict(), recAnalysis.get_stimMeanPulseDict(), recAnalysis.get_currentStimParams(), recAnalysis.get_currentPulse())
		self.update_plots()

	def get_rec_lines(self, check_id, state):
		side, muscle = check_id.split(" ")
		m_idx = self.muscles.index(muscle)
		if side == "Left":
			m_idx = m_idx + 8
		if m_idx not in self.recLines_idx and state == True:
			self.recLines_idx.append(m_idx)
		elif m_idx in self.recLines_idx and state == False:
			self.recLines_idx.remove(m_idx)
		self.recLines_idx.sort()
		self.update_plots()

	def set_data(self, stimDict, meanTracesDict, stimParams, currPulse):
		if len(stimDict.keys()) == 0 or len(meanTracesDict.keys()) == 0:
			return
		left_x = []
		if self.leftXvar == "Amplitude":
			left_x = np.array([x[96] for x in stimDict.keys()])
		elif self.leftXvar == "Frequency":
			left_x = np.array([x[144] for x in stimDict.keys()])
		elif self.leftXvar == "Pulse-Width":
			left_x = np.array([x[152] for x in stimDict.keys()])
		elif self.leftXvar == "Duration":
			left_x = np.array([x[160] for x in stimDict.keys()])
		left_y = []
		for key in stimDict.keys():
			left_y.append(stimDict[key])

		right_x = []
		if self.rightXvar == "Amplitude":
			right_x = np.array([x[96] for x in stimDict.keys()])
		elif self.rightXvar == "Frequency":
			right_x = np.array([x[144] for x in stimDict.keys()])
		elif self.rightXvar == "Pulse-Width":
			right_x = np.array([x[152] for x in stimDict.keys()])
		elif self.rightXvar == "Duration":
			right_x = np.array([x[160] for x in stimDict.keys()])
		right_y = []
		for key in stimDict.keys():
			right_y.append(stimDict[key])

		meanTraces = meanTracesDict[stimParams]
		mean_pulse_data = np.squeeze(meanTraces[self.pulseMuscle_idx, :])
		curr_pulse_data = np.squeeze(currPulse[:, self.pulseMuscle_idx, :])
		
		self.leftXdata = np.array(left_x)
		self.leftYdata = np.array(left_y)
		self.rightXdata = np.array(right_x)
		self.rightYdata = np.array(right_y)
		self.meanPulseData = mean_pulse_data
		self.currPulseData = curr_pulse_data



	def update_plots(self):
		self.update_axes()
		recruitmentFig = self.recruitmentHandle
		recruitmentAxes = recruitmentFig.figure.axes
		leftAxes = recruitmentAxes[0]
		rightAxes = recruitmentAxes[1]
		pulseAxes = recruitmentAxes[2]

		if self.leftYdata.size != 0:
			for l in range(0, 8): 
				line = leftAxes.lines[l]
				if (l+8) in self.recLines_idx:
					line.set_xdata(self.leftXdata)
					line.set_ydata(self.leftYdata[:, l])	
				else:
					line.set_xdata([])
					line.set_ydata([])
				leftAxes.draw_artist(line)
		if self.rightYdata.size != 0:
			for r in range(0, 8):
				line = rightAxes.lines[r]
				if r in self.recLines_idx:
					line.set_xdata(self.rightXdata)
					line.set_ydata(self.rightYdata[:, r])
				else:
					line.set_xdata([])
					line.set_ydata([])
				rightAxes.draw_artist(line)

		if self.currPulseData.size != 0:
			for i in range(0, NUM_PLOT_PULSES):
				line = pulseAxes.lines[i]
				pulseLimits = pulseAxes.get_xlim()
				line.set_xdata(np.arange(-500, 1000, 0.5))
				line.set_ydata(self.currPulseData[i, :])
				pulseAxes.draw_artist(line)
		if self.meanPulseData.size != 0:
			meanLine = pulseAxes.lines[-1]
			meanLine.set_xdata(np.arange(-500, 1000, 0.5))
			meanLine.set_ydata(self.meanPulseData)
			pulseAxes.draw_artist(meanLine)
		recruitmentFig.draw()

class EmgRecruitmentApp(App):
	def __init__(self, **kwargs):
		super(EmgRecruitmentApp, self).__init__(**kwargs)
		global settings_mpQ
		global filters_mpQ
		global MM_IP
		if 'settings_queue' in kwargs.keys():
			settings_mpQ = kwargs['settings_queue']
			settings = settings_mpQ.get()
			MM_IP = settings[0]
		else:
			MM_IP = Global.MM_IP

		global FS
		global BUFFER_TIME
		global BUFFER_TYPE
		global BUFFER_LENGTH
		global NUM_CHANS
		FS = Global.FS #2000
		BUFFER_TIME = Global.BUFFER_TIME 
		BUFFER_TYPE = Global.BUFFER_TYPE 
		BUFFER_LENGTH = Global.BUFFER_LENGTH
		NUM_CHANS = Global.NUM_CHANS 

	def build(self,):
		global FigureCanvas
		global Window
		global plt

		from kivy.garden.matplotlib.backend_kivyagg import FigureCanvas
		from kivy.core.window import Window
		import matplotlib.pyplot as plt
		return RecruitmentAnalysis() 

if __name__ == '__main__':
	EmgRecruitmentApp().run()
