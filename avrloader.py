#!/usr/bin/env python
"""
	avrloader.py
	AVR Loader main
"""
import sys
import ConfigParser
import traceback
import avrlog
from job_info import *

"""
	avrloader.py main.
	This module is invoked from the command line to start the
	application that interfaces with the AVR device bootloader.
	See the JobInfo class for command line parameter documentation.
"""
if __name__ == "__main__":

	avrlog.openlog('avrloader', avrlog.LOG_PID, avrlog.LOG_DAEMON)

	home_dir = sys.argv[0]
	slash_pos = sys.argv[0].rfind(os.sep)
	if slash_pos == -1:
		home_dir = '.'
	else:
		home_dir = sys.argv[0][:slash_pos]

	parser = ConfigParser.ConfigParser()
	cfg_file_name = '%s%savrloader.cfg' % (home_dir, os.sep)
	parser.read(cfg_file_name)

	try:
		log_level = eval('avrlog.%s' % parser.get('Logging', 'level'))
		avrlog.setlogmask(avrlog.LOG_UPTO(log_level))
	except:
		traceback.print_exc()
		avrlog.setlogmask(avrlog.LOG_UPTO(avrlog.LOG_ERR))

	try:
		j = JobInfo()
		j.parse_command_line(sys.argv)
		if len(j.com_port_name) == 0:
			device = parser.get('Communication', 'device')
			baud = parser.getint('Communication', 'baud')
			timeout = parser.getfloat('Communication', 'timeout')
			j.set_comms(device, baud, timeout)
		j.do_job()
	except RuntimeError, r_exc:
		avrlog.avrlog(avrlog.LOG_ERR, r_exc.message)
	except:
		avrlog.avrlog(avrlog.LOG_ERR, traceback.format_exc().replace('\n', '; '))
	avrlog.closelog()

