## Python imports
import multiprocessing as mp
import sys
## Custom imports
from globals import Global
import emgBuffer.emg_signal_buffer
import time
#from emg_signal_buffer import emgBuffer

if len(sys.argv) < 2:
	MM_IP = "localhost:7111" #Global.MM_IP #
	#BASE_DIR = "C:\Users\rnel\monica_emgplot_test" # Global.BASE_DIR
elif len(sys.argv) == 2:
	MM_IP = sys.argv[1]
	#BASE_DIR = Global.BASE_DIR #os.getcwd()
elif len(sys.argv) > 2:
	MM_IP = sys.argv[1]
	#BASE_DIR = sys.argv[2]

#MM_IP = "192.168.0.253:7111"
#BASE_DIR = "C:\Users\liufe\Documents\Grad_School\EMG_MemMap_Test"

def start_buffer():
	emgBuffer.emg_signal_buffer.emgBuffer()

def start_plotter(settings_queue, filter_queue):
	#from emgPlotter.emgPlot import EmgPlotApp
	from emgControl.emgControl import EmgControlApp
	kwargs = {'settings_queue': settings_queue, 'filter_queue': filter_queue}
	EmgControlApp(**kwargs).run()

def start_filter(settings_queue, filter_queue):
	from emgFilter.emgFilter import EmgFilterApp
	kwargs = {'settings_queue': settings_queue, 'filter_queue': filter_queue}
	EmgFilterApp(**kwargs).run()

def start_recruitment(settings_queue):
	from emgRecruitment.emgRecruitment import EmgRecruitmentApp
	kwargs = {'settings_queue': settings_queue}
	EmgRecruitmentApp(**kwargs).run()
	#print("Ello")

if __name__ == '__main__':
	#mp.freeze_support()

	settings_queue = mp.Queue()
	filter_queue = mp.Queue()
	settings_queue.put([MM_IP])

	buffering = mp.Process(target=start_buffer)
	buffering.start()

	plot_proc = mp.Process(target=start_plotter, args=(settings_queue, filter_queue,)).start()
	#filt_proc = mp.Process(target=start_filter, args=(settings_queue, filter_queue,)).start()
	#recruit_proc = mp.Process(target=start_recruitment, args=(settings_queue,)).start()
	
