##### Imports ##########
## kivy imports
import kivy
kivy.require('1.9.1')
from kivy import Config
Config.set('graphics', 'multisamples', '0')
Config.set('graphics', 'width', 1000)
Config.set('graphics', 'height', 700)
Config.set('graphics', 'resizable', False)
Config.set('graphics', 'kivy_clock', 'interrupt')
import matplotlib
matplotlib.use('module://kivy.garden.matplotlib.backend_kivy') # so that kivy can plot figures
from kivy.uix.widget import Widget
from kivy.app import App
from kivy.uix.image import Image 
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.slider import Slider
from kivy.uix.label import Label

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

##### End Imports ##########


global PACKET_LENGTH
PACKET_LENGTH = md.HX_EMG_SAMPLES_PER_MSG 

class EmgControl(BoxLayout):
	def __init__(self, **kwargs):
		super(EmgControl, self).__init__(**kwargs)
		self.orientation ='vertical'
		self.mod = PyDragonfly.Dragonfly_Module(0, 0)
		try:
			self.mod.ConnectToMMM(MM_IP)
		except:
			print("EMG Control could not connect to Message Manager.")
		print("EMG Control connected to Message Manager")
		
		PACKET_LENGTH = md.HX_EMG_SAMPLES_PER_MSG 

		self.mod.Subscribe(md.MT_SHUT_DOWN)

		self.data_diff_path = Global.data_diff_path #"R:/users/mfl24/research_code/mem_map/mmDataDiff.dat" #os.path.join(base_dir, 'mem_map', 'mmDataDiff.dat')
		self.data_diffTime_path = Global.data_diffTime_path #"R:/users/mfl24/research_code/mem_map/mmDataDiffTime.dat" #os.path.join(base_dir, 'mem_map', 'mmDataDiffTime.dat')
		
		self.filterOn = False
		self.filters = []
		
		self.listener = Thread(target=self.emgListener)
		self.listener.daemon = True
		self.listener.start()

		self.plotter = Thread(target=self.emgPlotter)
		self.plotter.daemon = True
		self.plotter.start()

	def emgListener(self):
		while True:
			msg = PyDragonfly.CMessage()
			self.mod.ReadMessage(msg, 0)
			if msg.GetHeader().msg_type == md.MT_SHUT_DOWN:
				msg_data = md.MDF_SHUT_DOWN()
				self.mod.DisconnectFromMMM()
				print("Emergency stop; Dragonfly thread closed")

			if filters_mpQ.empty() == False:
				filters = filters_mpQ.get(block=False)
				self.filters = filters
				if len(filters) == 0:
					self.filterOn = False
				else:
					self.filterOn = True
			time.sleep(0.001)

	def emgPlotter(self):
		mmDiff = np.memmap(self.data_diff_path, dtype='float32', mode='r', shape=(NUM_CHANS, BUFFER_LENGTH))
		mmDiffTime = np.memmap(self.data_diffTime_path, dtype='uint32', mode='r', shape=(BUFFER_LENGTH)) 
		emgPlot = self.get_root_window().children[-1].ids['plotMuscle']
		time.sleep(0.5)

		Clock.schedule_interval(lambda dt: emgPlot.update_plot(mmDiff, mmDiffTime, self.filters, self.filterOn), 0.001)

class EMGButtons(GridLayout):
	def __init__(self, **kwargs):
		super(EMGButtons, self).__init__(**kwargs)
		self.muscles = ['TFL', 'RF', 'VL', 'BF', 'SE', 'TA', 'SO', 'LG']
		self.activeMuscle = "Right TFL"
	
	def plot_muscle(self, muscle, state):
		if state == "down":
			self.activeMuscle = muscle
		elif state == "normal":
			self.activeMuscle = ""
		muscleNameLabel = self.get_root_window().children[-1].ids['muscleName']
		muscleNameLabel.text = self.activeMuscle

	def get_muscle_idx(self):
		if self.activeMuscle == "":
			return -1
		else:
			(side, muscleName) = self.activeMuscle.split(" ")
			m_idx = self.muscles.index(muscleName)
			if side == "Left":
				m_idx = m_idx + 8
			return m_idx

class EMGFigure(BoxLayout):
	def __init__(self, **kwargs):
		super(EMGFigure, self).__init__(**kwargs) 
		self.make_plot()

	def make_plot(self):
		muscle = plt.figure(facecolor=(0.3, 0.3, 0.3))
		plt.subplots_adjust(top=0.99, bottom=0.01, left=0.05, right=0.95)
		ax = muscle.add_subplot(1, 1, 1)
		ax.spines['bottom'].set_color('white')
		ax.spines['top'].set_color('white')
		ax.spines['left'].set_color('white')
		ax.spines['right'].set_color('white')
		ax.tick_params(length=0, color='white', labelsize=8, labelcolor='white')
		ax.set_facecolor((0.3, 0.3, 0.3))
		ax.set_xticks([])
		ax.set_yticks([])
		ax.set_xticklabels([])
		ax.set_yticklabels([])
		ax.plot([], linewidth=1)[0]
		ax.plot([], linewidth=1)[0]
		muscle_handle = FigureCanvas(muscle)
		muscle_handle.blit()
		self.add_widget(muscle_handle)					
		self.muscle_handle = muscle_handle 

		
	def update_plot(self, mmDiff, mmDiffTime, filters, filterOn): 
		buttons = self.get_root_window().children[-1].ids['muscleButtons']
		m_idx = buttons.get_muscle_idx()
		timescale = self.get_root_window().children[-1].ids['timescale'].value
		SAMPLES = int(FS*timescale)
		fig = self.muscle_handle
		ax = fig.figure.axes[0]
		lines = ax.lines
		lines[0].set_xdata(np.arange(0, timescale,  0.0005)) # 0.002)) # 
		lines[0].set_ydata(mmDiff[m_idx, -1*SAMPLES:])
		ax.draw_artist(lines[0])
		if filterOn:
			for f in filters:
				filteredData = signal.filtfilt(f[0], f[1], mmDiff[m_idx, -SAMPLES:])
			lines[1].set_xdata(np.arange(0, timescale,  0.0005)) # 0.002)) #
			lines[1].set_ydata(filteredData)
			ax.draw_artist(lines[1])
		else:
			lines[1].set_xdata([])
			lines[1].set_ydata([])
			ax.draw_artist(lines[1])
		fig.draw()

	def update_axes(self, slide_name):
		start = time.time()
		fig = self.muscle_handle
		ax = fig.figure.axes[0]
		if slide_name == "timescale":
			timescale = self.get_root_window().children[-1].ids['timescale'].value
			ax.set_xlim(0, timescale)
		if slide_name == "yaxis":
			yaxis = self.get_root_window().children[-1].ids['yaxis'].value
			ax.set_ylim(-1*yaxis, yaxis)
		fig.blit()
		fig.draw()
		end = time.time()

class EmgControlApp(App):
	def __init__(self, **kwargs):
		super(EmgControlApp, self).__init__(**kwargs)
		global settings_mpQ
		global filters_mpQ
		global MM_IP
		if 'settings_queue' in kwargs.keys():
			settings_mpQ = kwargs['settings_queue']
			settings = settings_mpQ.get()
			MM_IP = settings[0]
		else:
			MM_IP = Global.MM_IP
		if 'filter_queue' in kwargs.keys():
			filters_mpQ = kwargs['filter_queue']
		else:
			filters_mpQ = mp.Queue()

		global NUM_CHANS
		global BUFFER_TIME
		global BUFFER_LENGTH
		global BUFFER_TYPE
		global FS

		NUM_CHANS = Global.NUM_CHANS 
		BUFFER_TIME = Global.BUFFER_TIME 
		BUFFER_TYPE = Global.BUFFER_TYPE 
		FS = Global.FS 
		BUFFER_LENGTH = Global.BUFFER_LENGTH

	def build(self,):
		## Literally just hacks, because importing these globally makes kivy make new blank windows automatically
		global FigureCanvas
		global Window
		global plt

		from kivy.garden.matplotlib.backend_kivyagg import FigureCanvas
		from kivy.core.window import Window
		import matplotlib.pyplot as plt
		return EmgControl() 

if __name__ == '__main__':
	#multiprocessing.freeze_support()
	EmgControlApp().run()
