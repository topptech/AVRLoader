"""
	avrlog.py
	
	Logging utility with a syslog like API. It is set up to log to
	the command line to provide program progress and error messages.
"""
import logging
import os
import os.path
import sys

LOG_PID = None
LOG_DAEMON = None

LOG_CRIT = logging.CRITICAL
LOG_ERR = logging.ERROR
LOG_WARNING = logging.WARNING
LOG_INFO = logging.INFO
LOG_DEBUG = logging.DEBUG

gident = os.path.basename(sys.argv[0])
gpriority = LOG_DEBUG
gsilent = False
gprogress = True

def openlog(ident=None, logopt=None, facility=None):
	global gident
	if ident != None:
		gident = ident

	logging.basicConfig(stream=sys.stdout,
	                    format='%(asctime)s: [' + gident + \
	                    ']: %(module)s:%(lineno)d %(levelname)s: %(message)s',
	                    level=logging.DEBUG)


def avrlog(priority=None, message=None, use_fmt=True):
	"""
		Output a syslog like message.
	"""
	global gsilent
	global gpriority
	if gsilent:
		return

	if priority != None:
		gpriority = priority
	if use_fmt:
		if gpriority == LOG_CRIT:
			logging.critical(message)
		elif gpriority == LOG_ERR:
			logging.error(message)
		elif gpriority == LOG_WARNING:
			logging.warning(message)
		elif gpriority == LOG_INFO:
			logging.info(message)
		else:
			logging.debug(message)
	elif gpriority >= logging.root.level:
			sys.stdout.write(message)


def progress(message=None):
	"""
		Output a progress message.
	"""
	global gprogress
	if gprogress and message != None:
		sys.stdout.write(message)
		sys.stdout.flush()


def set_silent(silent=True):
	"""
		Enable or disable avrlog messages.
	"""
	global gsilent
	gsilent = silent


def set_progress(progress=True):
	"""
		Enable or disable progress messages.
	"""
	global gprogress
	gprogress = progress


def setlogmask(level):
	logging.root.setLevel(level)


def LOG_UPTO(level):
	return level


def closelog():
	logging.shutdown()


