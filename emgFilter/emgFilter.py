import kivy
kivy.require('1.9.1')
from kivy import Config
Config.set('graphics', 'width', 1400)
Config.set('graphics', 'height', 700)
from kivy.uix.widget import Widget
from kivy.app import App
from kivy.uix.gridlayout import GridLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ToggleButtonBehavior
from kivy.uix.textinput import TextInput 
from kivy.uix.button import Button

from kivy.uix.label import Label
from kivy.uix.switch import Switch
from kivy.uix.popup import Popup

import sys
import os
sys.path.append(os.path.abspath(os.getcwd()))
from globals import Global 
from scipy import signal

global ALL_FILTERS 
ALL_FILTERS = {}

class FilterModule(GridLayout):
	def __init__(self, **kwargs):
		super(FilterModule, self).__init__(**kwargs)
		self.cols = 1

class FilterSettings(GridLayout):
	def __init__(self, **kwargs):
		super(FilterSettings, self).__init__(**kwargs)
		self.filterSettingsDict = {}
  	
	def on_enter(self, instance, value):
		if value == "":
			popup = MyPopup(errorText = "Must enter valid integer > 0")
			popup.open()
		else:
			if instance.find("cheby") != -1:
				self.filterSettingsDict[instance] = float(value)
			else:
				self.filterSettingsDict[instance] = int(value)

	def set_filter_types(self, key, state, value):
		group = key.split('type')[0]
		if state == 'down':
			self.filterSettingsDict[key] = value
			if value.lower() == "notch":
				self.get_root_window().children[-1].ids[group + 'highpass'].disabled = True
				self.get_root_window().children[-1].ids[group + 'highpass'].state = "normal"
				self.get_root_window().children[-1].ids[group + 'lowpass'].disabled = True
				self.get_root_window().children[-1].ids[group + 'lowpass'].state = "normal"
				self.get_root_window().children[-1].ids[group + 'bandpass'].disabled = True
				self.get_root_window().children[-1].ids[group + 'bandpass'].state = "normal"
				self.get_root_window().children[-1].ids[group + 'bandstop'].state = "down"
				self.set_filter_pass(group + "pass", "down", "bandstop")

				self.get_root_window().children[-1].ids[group + 'HighLabel'].text = "Quality\n Bandwith"
				self.get_root_window().children[-1].ids[group + 'High'].hint_text = "Q = w0/bw"

			else:
				self.get_root_window().children[-1].ids[group + 'highpass'].disabled = False
				self.get_root_window().children[-1].ids[group + 'lowpass'].disabled = False
				self.get_root_window().children[-1].ids[group + 'bandpass'].disabled = False

				self.get_root_window().children[-1].ids[group + 'HighLabel'].text = "Cutoff \nFrequency \nHigh (Hz):"
				self.get_root_window().children[-1].ids[group + 'High'].hint_text = "e.g. 200 (Hz)"

			if value.lower().replace(" ", "") == "chebyshev1" or value.lower().replace(" ", "") == "chebyshev2":
				self.get_root_window().children[-1].ids[group + "cheby"].disabled = False
			else:
				self.get_root_window().children[-1].ids[group + "cheby"].disabled = True

		if state == 'normal':
			if key in self.filterSettingsDict.keys():
				del self.filterSettingsDict[key]

	def set_filter_pass(self, key, state, value):
		group = key.split('pass')[0]
		if state == 'down':
			self.filterSettingsDict[key] = value
			if value.lower() == "highpass" or value.lower() == "lowpass":
				self.get_root_window().children[-1].ids[group + "High"].disabled = True
			else:
				self.get_root_window().children[-1].ids[group + "High"].disabled = False

		if state == 'normal':
			if key in self.filterSettingsDict.keys():
				del self.filterSettingsDict[key]
	
	def set_filters(self):
		#print(ALL_FILTERS)
		FS = Global.FS
		nyquist = FS/2

		filters = []
		for fgroup in ALL_FILTERS.keys():
			filterParams = ALL_FILTERS[fgroup]
			filterType = filterParams[fgroup + "type"]
			filterPass = filterParams[fgroup + "pass"]
			filterOrder = filterParams[fgroup + "order"]
			
			if filterPass.lower() == "lowpass" or filterPass.lower() == "highpass":
				filterCutoff = float(filterParams[fgroup + "Low"]/float(nyquist))
			else:
				if filterType.lower() == "notch":
					w0 = float(filterParams[fgroup + "Low"]/float(nyquist))
					filterCutoff = (w0, float(w0/float(filterParams[fgroup + "High"])))
				else:
					filterCutoff = (float(filterParams[fgroup + "Low"]/float(nyquist)), float(filterParams[fgroup + "High"]/float(nyquist)))

			#print(filterType, filterOrder, filterCutoff, filterPass.lower())
			if filterType.lower().replace(" ", "") == "butterworth":
				b, a = signal.butter(filterOrder, filterCutoff, filterPass.lower())
			elif filterType.lower().replace(" ", "") == "chebyshev1":
				filterCheby = filterParams[fgroup + "cheby"]
				b, a = signal.cheby1(filterOrder, filterCheby, filterCutoff, filterPass.lower())
			elif filterType.lower().replace(" ", "") == "chebyshev2":
				filterCheby = filterParams[fgroup + "cheby"]
				b, a = signal.cheby2(filterOrder, filterCheby, filterCutoff, filterPass.lower())
			elif filterType.lower().replace(" ", "") == "notch":
				b, a = signal.iirnotch(filterCutoff[0], filterCutoff[1])
			filters.append((b,a))
		filters_mpQ.put(filters)

	def set_filter_settings(self, group, is_active):
		filterType = group + "type"
		filterPass = group + "pass"
		filterOrder = group + "order"
		lowHz = group + "Low"
		highHz = group + "High"
		if is_active == True:
			if filterType not in self.filterSettingsDict.keys() or filterPass not in self.filterSettingsDict.keys() or filterOrder not in self.filterSettingsDict.keys():
				switch_button = self.get_root_window().children[-1].ids[group + 'Switch']
				switch_button.active = False 
				popup = MyPopup(errorText = "No filter type or filter pass selected, or filter order not specified.")
				popup.open()
			elif self.filterSettingsDict[filterPass].lower() == "bandpass" or self.filterSettingsDict[filterPass].lower() == group + "bandstop":
				if lowHz not in self.filterSettingsDict.keys() or highHz not in self.filterSettingsDict.keys():
					switch_button = self.get_root_window().children[-1].ids[group + 'Switch']
					switch_button.active = False 
					popup = MyPopup(errorText = "Must enter both low and high cutoff for bandpass and bandstop.")
					popup.open()
				elif self.filterSettingsDict[lowHz] <= 0 or self.filterSettingsDict[highHz] <= 0 or self.filterSettingsDict[lowHz] > self.filterSettingsDict[highHz]:
					switch_button = self.get_root_window().children[-1].ids[group + 'Switch']
					switch_button.active = False 
					popup = MyPopup(errorText = "Low cutoff must be smaller than high cutoff and greater than 0.")
					popup.open()
			elif (self.filterSettingsDict[filterType].lower().replace(" ", "") == "chebyshev1" and group + "cheby" not in self.filterSettingsDict.keys())\
			 or (self.filterSettingsDict[filterType].lower().replace(" ", "") == "chebyshev2" and group + "cheby" not in self.filterSettingsDict.keys()):
					switch_button = self.get_root_window().children[-1].ids[group + 'Switch']
					switch_button.active = False 
					popup = MyPopup(errorText = "No rs or rp value specified for Chebyshev filter.")
					popup.open()
			else:
				ALL_FILTERS[group] = self.filterSettingsDict
				self.set_filters()				

		if is_active == False:
			if group in ALL_FILTERS.keys():
				del ALL_FILTERS[group]
			self.set_filters()

		

class MyPopup(Popup):
	def __init__(self, **kwargs):
		super(MyPopup, self).__init__(**kwargs)
		errorText = kwargs['errorText']
		content = BoxLayout(orientation='vertical', padding=[10], halign="center")
		mylabel = Label(text = errorText, size_hint = (1, 0.5), font_size=12)
		mybutton = Button(text = "Ok", size_hint=(1, 0.3), font_size=12)
		content.add_widget(mylabel)
		content.add_widget(mybutton)
		self.canvas.opacity = 0.8
		self.background_color = 1, 1, 1, 1
		self.content = content
		self.title = "Incomplete Filter Settings"
		self.auto_dismiss = False
		self.size_hint = (0.5, 0.2)
		self.pos_hint = {'right': 0.7, 'left': 0.3}
		self.font_size = 12
		mybutton.bind(on_press=self.close_popup)

	def close_popup(self, instance):
		self.dismiss()

class EmgFilterApp(App):
	def __init__(self, **kwargs):
		super(EmgFilterApp, self).__init__(**kwargs)
		global filters_mpQ
		filters_mpQ = kwargs['filter_queue']
	def build(self,):
		global Window
		from kivy.core.window import Window
		return FilterModule()

#def run():
	#PROCESS_QUEUE = q
	#print(PROCESS_QUEUE.get())
#	EmgFilterApp().run()

if __name__ == '__main__':
	EmgFilterApp().run() 