## Python imports
import multiprocessing as mp
import sys
## Custom imports
from globals import Global
import emgBuffer.emg_signal_buffer
import time
#from emg_signal_buffer import emgBuffer

if len(sys.argv) < 2:
	MM_IP = Global.MM_IP 
elif len(sys.argv) == 2:
	MM_IP = sys.argv[1]
elif len(sys.argv) > 2:
	MM_IP = sys.argv[1]

def start_buffer():
	emgBuffer.emg_signal_buffer.emgBuffer()

def start_plotter(settings_queue, filter_queue):
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

if __name__ == '__main__':

	settings_queue = mp.Queue()
	filter_queue = mp.Queue()
	settings_queue.put([MM_IP])

	buffering = mp.Process(target=start_buffer)
	buffering.start()

	plot_proc = mp.Process(target=start_plotter, args=(settings_queue, filter_queue,)).start()
	filt_proc = mp.Process(target=start_filter, args=(settings_queue, filter_queue,)).start()
	#time.sleep(2)
	# Run recruitment in separate window, kivy doesn't like opening this and the plotter at the same time
	#recruit_proc = mp.Process(target=start_recruitment, args=(settings_queue,)).start()
	
