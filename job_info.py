"""
	job_info.py
	The module to interface with the user and invoke commands.
"""
import os
import getopt
import sys
import serial
import avrlog
import avrprog
import avrdev
from hex_util import HexFile

class JobInfo():
	"""
		JobInfo class.
		This class deals with the command line input from the user. The
		command line is parsed. If a valid command is detected then a job
		is run. If an invalid command is detected then the usage message
		is displayed and the user is returned to the command line.
	"""
	def __init__(self):

		self.show_help = False
		self.silent_mode = False
		self.no_progress_indicator = False
		self.read_signature = False
		self.chip_erase = False
		self.get_hw_revision = False
		self.get_sw_revision = False
		self.program_flash = False
		self.program_eeprom = False
		self.read_flash = False
		self.read_eeprom = False
		self.verify_flash = False
		self.verify_eeprom = False
		self.read_lock_bits = False
		self.read_fuse_bits = False
		self.read_osccal = False
		self.rc_calibrate = False

		self.device_name = ''
		self.input_file_flash = ''
		self.input_file_eeprom = ''
		self.output_file_flash = ''
		self.output_file_eeprom = ''

		self.osccal_parameter = -1
		self.osccal_flash_address = -1
		self.osccal_flash_address_tiny = -1
		self.calib_retval = -1
		self.osccal_eeprom_address = -1

		self.program_lock_bits = -1
		self.verify_lock_bits = -1

		self.program_fuse_bits = -1
		self.program_extended_fuse_bits = -1
		self.verify_fuse_bits = -1
		self.verify_extended_fuse_bits = -1

		self.memory_fill_pattern = -1

		self.flash_start_address = -1
		self.flash_end_address = -1

		self.eeprom_start_address = -1
		self.eeprom_end_address = -1

		self.com_port_name = ''
		self.baud = 9600
		self.timeout = 2.0
		self.search_path = ''

		self.encrypted = False


	def parse_command_line(self, argv):

		own_path = argv[0]
		slash_pos = argv[0].rfind(os.sep)
		if slash_pos == -1:
			own_path = '.'
		else:
			own_path = argv[0][:slash_pos]

		self.search_path = own_path
		self.search_path = '%s%s%s%sdevices' % \
		                   (self.search_path, os.pathsep, own_path, os.sep)

		try:
			optlist, args = getopt.getopt(argv[1:], "b:c:ed:E:f:F:gG:h?l:L:nO:qsx:yY:z", ['af=', 'ae=', 'if=', 'ie=', 'of=', 'oe=', 'O#=', 'pf', 'pe', 'pb', 'rf', 're', 'rb', 'Sf=', 'Se=', 'vf', 've', 'vb'])
			for (x, y) in optlist:
				if x == '--af':
					self.flash_start_address, self.flash_end_address = y.split(':')
				elif x == '--ae':
					self.eeprom_start_address, self.eeprom_end_address = y.split(':')
				elif x == '-b':
					if y == 'h':
						self.get_hw_revision = True
					elif y == 's':
						self.get_sw_revision = True
					else:
						raise RuntimeError('Invalid programmer revision request.')
				elif x == '-c':
					self.com_port_name = y
				elif x == '-d':
					self.device_name = y
				elif x == '-e':
					self.chip_erase = True
				elif x == '-E':
					self.program_extended_fuse_bits = int(y, 16)
				elif x == '-f':
					self.program_fuse_bits = int(y, 16)
				elif x == '-F':
					self.verify_fuse_bits = int(y, 16)
				elif x == '-g':
					self.silent_mode = True
				elif x == '-G':
					self.verify_extended_fuse_bits = int(y, 16)
				elif x == '-h' or x == '-?':
					self.show_help = True
				elif x == '--if':
					self.input_file_flash = y
				elif x == '--ie':
					self.input_file_eeprom = y
				elif x == '-l':
					self.program_lock_bits = int(y, 16)
				elif x == '-L':
					self.verify_lock_bits = int(y, 16)
				elif x == '-n':
					self.encrypted = True
				elif x == '--of':
					self.output_file_flash = y
				elif x == '--oe':
					self.output_file_eeprom = y
				elif x == '-O':
					self.read_osccal = True
					self.osccal_parameter = int(y, 16)
				elif x == '--O#':
					self.read_osccal = False
					self.osccal_parameter = int(y, 16)
				elif x == '--pf':
					self.program_flash = True
				elif x == '--pe':
					self.program_eeprom = True
				elif x == '--pb':
					self.program_flash = True
					self.program_eeprom = True
				elif x == '-q':
					self.read_fuse_bits = True
				elif x == '--rf':
					self.read_flash = True
				elif x == '--re':
					self.read_eeprom = True
				elif x == '--rb':
					self.read_flash = True
					self.read_eeprom = True
				elif x == '-s':
					self.read_signature = True
				elif x == '--Sf':
					self.osccal_flash_address = int(y, 16)
				elif x == '--Se':
					self.osccal_eeprom_address = int(y, 16)
				elif x == '--vf':
					self.verify_flash = True
				elif x == '--ve':
					self.verify_eeprom = True
				elif x == '--vb':
					self.verify_flash = True
					self.verify_eeprom = True
				elif x == '-x':
					self.memory_fill_pattern = int(y, 16)
				elif x == '-y':
					self.read_lock_bits = True
				elif x == '-Y':
					self.rc_calibrate = True
					self.osccal_flash_address_tiny = int(y, 16)
				elif x == '-z':
					self.no_progress_indicator = True
				else:
					self.usage()
					sys.exit(1)
		except:
			self.usage()
			sys.exit(1)


	def set_comms(self, device, baud, timeout):

		self.com_port_name = device
		self.baud = baud
		self.timeout = timeout


	def do_job(self):

		if self.silent_mode:
			avrlog.set_silent()
			avrlog.set_progress(False)

		if self.no_progress_indicator:
			avrlog.set_progress(False)

		if self.show_help:
			self.usage()
			return

		port = None
		prog = None
		if len(self.com_port_name) > 0:
			port = serial.Serial(port=self.com_port_name, baudrate=self.baud,
			                     timeout=self.timeout, writeTimeout=self.timeout)
			prog = avrprog.AVRProgrammer.instance(port)
		else:
			avrlog.avrlog(avrlog.LOG_ERR, 'Serial port not specified.')

		if prog == None:
			raise RuntimeError('AVR Programmer not found.')

		if self.rc_calibrate:
			if not prog.rc_calibrate():
				avrlog.avrlog(avrlog.LOG_ERR, 'RC calibrate failed.')
				sys.exit(1)
			else:
				avrlog.avrlog(avrlog.LOG_INFO, 'RC calibrate succeeded.')

		avrlog.avrlog(avrlog.LOG_INFO, 'Entering programming mode...')
		if not prog.enter_programming_mode():
			avrlog.avrlog(avrlog.LOG_ERR, 'Set programming mode failed.')
			sys.exit(1)
		else:
			avrlog.avrlog(avrlog.LOG_INFO, 'Set programming mode succeeded.')

		if self.read_signature:
			avrlog.avrlog(avrlog.LOG_CRIT, 'Reading signature bytes: ', False)
			sig0, sig1, sig2 = prog.read_signature()
			avrlog.avrlog(avrlog.LOG_CRIT,
			              '0x%02x, 0x%02x, 0x%02x\n' % (sig0, sig1, sig2), False)

		if self.get_sw_revision:
			avrlog.avrlog(avrlog.LOG_CRIT,
			              'Reading programmer software revision: ', False)
			res, major, minor = prog.programmer_software_version()
			if res:
				avrlog.avrlog(avrlog.LOG_CRIT,
				              '%s.%s\n' % (major, minor), False)
			else:
				avrlog.avrlog(avrlog.LOG_CRIT,
				              '\nError retrieving software revision.\n', False)

		if len(self.device_name) == 0:
			avrlog.avrlog(avrlog.LOG_ERR, 'Device name not specified.')
			return

		device = avrdev.AVRDevice(self.device_name)
		device.read_avr_parameters(self.search_path)

		sig0, sig1, sig2 = device.get_signature()
		if not prog.check_signature(sig0, sig1, sig2):
			avrlog.avrlog(avrlog.LOG_ERR, 'Signature does not match device.')

		self._do_device_dependent(prog, device)

		prog.leave_programming_mode()

		if port != None:
			port.close()


	def _do_device_dependent(self, prog, device):

		prog.set_page_size(device.get_page_size())

		if self.flash_end_address != -1:
			if self.flash_end_address >= device.get_flash_size():
				raise RuntimeError('Specified flash address is outside of ' +
				                   'the device address space')
		else:
			self.flash_start_address = 0
			self.flash_end_address = device.get_flash_size() - 1

		if self.eeprom_end_address != -1:
			if self.eeprom_end_address >= device.get_eeprom_size():
				raise RuntimeError('Specified EEPROM address is outside of ' +
				                   'the device address space')
		else:
			self.eeprom_start_address = 0
			self.eeprom_end_address = device.get_eeprom_size() - 1

		if self.read_flash:

			if len(self.output_file_flash) == 0:
				raise RuntimeError('Cannot read flash without output file specified.')

			hexf = HexFile(device.get_flash_size())
			hexf.set_used_range(self.flash_start_address, self.flash_end_address)

			avrlog.avrlog(avrlog.LOG_INFO, 'Reading flash contents...')

			if not prog.read_flash(hexf):
				raise RuntimeError('Flash read is not supported by this programmer.')

			avrlog.avrlog(avrlog.LOG_INFO, 'Writing Hex output file...')
			hexf.write_file(self.output_file_flash)

		if self.read_eeprom:

			if len(self.output_file_eeprom) == 0:
				raise RuntimeError('Cannot read EEPROM without file specified.')

			hexf = HexFile(device.get_eeprom_size())
			hexf.set_used_range(self.eeprom_start_address, self.eeprom_end_address)

			avrlog.avrlog(avrlog.LOG_INFO, 'Reading EEPROM contents...')

			if not prog.read_eeprom(hexf):
				raise RuntimeError('EEPROM read is not supported by the programmer.')

			avrlog.avrlog(avrlog.LOG_INFO, 'Writing Hex output file...')
			hexf.write_file(self.output_file_eeprom)

		if self.read_lock_bits:

			avrlog.avrlog(avrlog.LOG_INFO, 'Reading lock bits...')
			result, bits = prog.read_lock_bits()
			if not result:
				raise RuntimeError('Lock bit read is not supported by the programmer.')

			avrlog.avrlog(avrlog.LOG_ERR, 'Lock bits: 0x%02X\n' % bits, False)

		if self.read_fuse_bits:

			if not device.get_fuse_status():
				raise RuntimeError('Selected device has no fuse bits.')

			avrlog.avrlog(avrlog.LOG_INFO, 'Reading fuse bits...')

			result, bits = prog.read_fuse_bits()
			if not result:
				raise RuntimeError('Fuse bit read is not supported by the programmer.')

			avrlog.avrlog(avrlog.LOG_ERR, 'Fuse bits: 0x%04X\n' % bits, False)

			if device.get_ext_fuse_status():

				result, bits = prog.read_extended_fuse_bits()
				if not result:
					raise RuntimeError(
					      'Extended fuse bit read is not supported by this programmer.')

				avrlog.avrlog(avrlog.LOG_ERR, 'Extended fuse bits: %0x02X' % bits, False)

		if self.chip_erase:

			avrlog.avrlog(avrlog.LOG_INFO, 'Erasing chip contents...')

			if not prog.chip_erase():
				raise RuntimeError('Chip erase is not supported by this programmer.')

		if self.program_flash or self.verify_flash:

			if len(self.input_file_flash) == 0:
				raise RuntimeError(
				      'Cannot program or verify flash without a file specified.')

			hexf = HexFile(device.get_flash_size())

			if self.memory_fill_pattern != -1:
				hexf.clear_all(self.memory_fill_pattern)

			avrlog.avrlog(avrlog.LOG_INFO, 'Reading hex input file for flash operation...')

			hexf.read_file(self.input_file_flash)

			if hexf.get_range_start() > self.flash_end_address or \
			   hexf.get_range_end() < self.flash_start_address:
				raise RuntimeError('Hex file defines data outside specified range.')

			if self.memory_fill_pattern == -1:

				if hexf.get_range_start() > self.flash_start_address:
					self.flash_start_address = hexf.get_range_start()

				if hexf.get_range_end() < self.flash_end_address:
					self.flash_end_address = hexf.get_range_end()

			if self.rc_calibrate:

				if self.osccal_flash_address_tiny > self.flash_start_address and \
				   self.osccal_flash_address_tiny < self.flash_end_address:
					raise RuntimeError('Specified address is within application code.')

				hexf.set_data(self.osccal_flash_address_tiny, self.calib_retval)
				hexf.set_used_range(self.flash_start_address,
				                   self.osccal_flash_address_tiny)

		if self.program_flash:

			avrlog.avrlog(avrlog.LOG_INFO, 'Programming flash contents...')
			if not prog.write_flash(hexf):
				raise RuntimeError(
				      'Flash programming is not supported by this programmer.')


		if self.verify_flash:

			hexv = HexFile(device.get_flash_size())

			avrlog.avrlog(avrlog.LOG_INFO, 'Reading flash contents...')

			hexv.set_used_range(hexf.get_range_start(), hexf.get_range_end())

			if not prog.read_flash(hexv):
				raise RuntimeError('Flash read is not supported by this programmer.')

			avrlog.avrlog(avrlog.LOG_INFO, 'Comparing flash data...')

			for pos in range(hexf.get_range_start(), hexf.get_range_end() + 1):

				valf = hexf.get_data(pos)
				valv = hexv.get_data(pos)
				if valf != valv:
					avrlog.avrlog(avrlog.LOG_ERR,
					              'Unverified at 0x%X (0x%02X vs 0x%02X)\n' % (pos, valf, valv),
					              False)
					break

			if pos >= hexf.get_range_end():
				avrlog.avrlog(avrlog.LOG_ERR, 'Verified.\n', False)

		if self.program_eeprom or self.verify_eeprom:

			if len(self.input_file_eeprom) == 0:
				raise RuntimeError(
				      'Cannot program or verify EEPROM without a file specified.')

			hexf = HexFile(device.get_eeprom_size())

			if self.memory_fill_pattern != -1:
				hexf.clear_all(self.memory_fill_pattern)

			avrlog.avrlog(avrlog.LOG_INFO,
			              'Reading hex file for EEPROM operations...')

			hexf.read_file(self.input_file_eeprom)

			if hexf.get_range_start() > self.eeprom_end_address or \
			   hexf.get_range_end() < self.eeprom_start_address:
				raise RuntimeError('Hex file defines data outside of specified range.')

			if self.memory_fill_pattern == -1:
				if hexf.get_range_start() > self.eeprom_start_address:
					self.eeprom_start_address = hexf.get_range_start()

				if hexf.get_range_end() < self.eeprom_end_address:
					self.eeprom_end_address = hexf.get_range_end()

			hexf.set_used_range(self.eeprom_start_address, self.eeprom_end_address)

		if self.program_eeprom:

			avrlog.avrlog(avrlog.LOG_INFO, 'Programming EEPROM contents...')
			if not prog.write_eeprom(hexf):
				raise RuntimeError(
				      'EEPROM programming is not supported by this programmer.')

		if self.verify_eeprom:

			hexv = HexFile(device.get_eeprom_size())

			avrlog.avrlog(avrlog.LOG_INFO, 'Reading EEPROM contents...')

			hexv.set_used_range(hexf.get_range_start(), hexf.get_range_end())

			if not prog.read_eeprom(hexv):
				raise RuntimeError('EEPROM read is not supported by this programmer.')

			avrlog.avrlog(avrlog.LOG_INFO, 'Comparing EEPROM data...')

			for pos in range(hexf.get_range_start(), hexf.get_range_end() + 1):

				valf = hexf.get_data(pos)
				valv = hexv.get_data(pos)
				if valf != valv:
					avrlog.avrlog(avrlog.LOG_ERR,
					              'Unverified at address 0x%X (0x%02X vs 0x%02X)\n' %
					              (valf, valv), False)
					break

			if pos >= hexf.get_range_end():
				avrlog.avrlog(avrlog.LOG_ERR, 'Verified.\n', False)


		if self.program_lock_bits != -1:

			avrlog.avrlog(avrlog.LOG_INFO, 'Programming lock bits...')

			if not prog.write_lock_bits(self.program_lock_bits):
				raise RuntimeError(
				      'Lock bit programming is not supported by this programmer.')

		if self.program_fuse_bits != -1:

			if not device.get_fuse_status():
				raise RuntimeError('Selected device has no fuse bits.')

			avrlog.avrlog(avrlog.LOG_INFO, 'Programming fuse bits...')

			if not prog.write_fuse_bits(self.program_fuse_bits):
				raise RuntimeError(
				      'Fuse bit programming is not supported by this programmer.')

		if self.program_extended_fuse_bits != -1:

			if not device.get_extended_fuse_status():
				raise RuntimeError('Selected device has no extended fuse bits.')

			avrlog.avrlog(avrlog.LOG_INFO, 'Programming extended fuse bits...')

			if not prog.write_extended_fuse_bits(self.program_extended_fuse_bits):
				raise RuntimeError(
				      'Extended fuse bit programming is not supported by this programmer.')

		if self.verify_lock_bits != -1:

			avrlog.avrlog(avrlog.LOG_INFO, 'Verifying lock bits...')

			result, bits = prog.read_lock_bits()
			if not result:
				raise RuntimeError('Lock bit read is not supported by this programmer.')

			if bits == self.verify_lock_bits:
				avrlog.avrlog(avrlog.LOG_ERR, 'Lock bits verified.\n', False)
			else:
				avrlog.avrlog(avrlog.LOG_ERR, 'Lock bits differ (0x%02X vs 0x%02X)\n' %
				              (self.verify_lock_bits, bits), False)

		if self.verify_fuse_bits != -1:

			if not device.get_fuse_status():
				raise RuntimeError('Selected device has no fuse bits.')

			avrlog.avrlog(avrlog.LOG_INFO, 'Verifying fuse bits...')

			result, bits = prog.read_fuse_bits()
			if not result:
				raise RuntimeError('Fuse bit read is not supported by this programmer.')

			if bits == self.verify_fuse_bits:
				avrlog.avrlog(avrlog.LOG_ERR, 'Fuse bits (0x%04X) verified.\n' % bits, False)
			else:
				avrlog.avrlog(avrlog.LOG_ERR, 'Fuse bits differ (0x%04X vs 0x%04X)\n' %
				              (self.verify_fuse_bits, bits), False)

		if self.verify_extended_fuse_bits != -1:

			if not device.get_ext_fuse_status():
				raise RuntimeError('Selected device has no extended fuse bits.')

			avrlog.avrlog(avrlog.LOG_INFO, 'Verifying extended fuse bits...')

			result, bits = prog.read_extended_fuse_bits()
			if not result:
				raise RuntimeError(
				      'Extended fuse bit read is not supported by this programmer.')

			if bits == self.verify_extended_fuse_bits:
				avrlog.avrlog(avrlog.LOG_ERR, 'Extended fuse bits verified.\n', False)
			else:
				avrlog.avrlog(avrlog.LOG_ERR,
				              'Extended fuse bits differ (0x%02X vs 0x%02X).\n' %
				              (self.verify_fuse_bits, bits), False)

		if self.osccal_parameter != -1:

			if self.read_osccal:

				avrlog.avrlog(avrlog.LOG_INFO, 'Reading OSCCAL from device...')

				pos = self.osccal_parameter
				result, self.osccal_parameter = prog.read_osccal(pos)
				if not result:
					raise RuntimeError('OSCCAL read is not supported by this programmer.')

				avrlog.avrlog(avrlog.LOG_ERR,
				              'OSCCAL parameter: 0x%02X' % self.osccal_parameter,
				              False)

		if self.osccal_flash_address != -1:

			if self.osccal_parameter == -1:
				raise RuntimeError('OSCCAL value not specified.')

			avrlog.avrlog(avrlog.LOG_INFO, 'Programming OSCCAL to flash...')

			if not prog.write_flash_byte(self.osccal_flash_address, self.osccal_parameter):
				raise RuntimeError('Flash programming is not supprted by this programmer.')

		if self.osccal_eeprom_address != -1:

			if self.osccal_parameter == -1:
				raise RuntimeError('OSCCAL value not specified.')

			avrlog.avrlog(avrlog.LOG_INFO, 'Programming OSCCAL to EEPROM...')

			if not prog.write_eeprom_byte(self.osccal_eeprom_address,
			                              self.osccal_parameter):
				raise RuntimeError(
				      'EEPROM programming is not supported by this programmer.')


	def usage(self):

		print "Command Line Switches:"
		print "        [-d device name] [--if infile] [--ie infile] [--of outfile]"
		print "        [--oe outfile] [-s] [-O index] [--O# value] [--Sf addr] [--Se addr]"
		print "        [-e] [--p[f|e|b]] [--r[f|e|b]] [--v[f|e|b]] [-l value] [-L value]"
		print "        [-y] [-f value] [-E value] [-F value] [-G value] [-q] [-x value]"
		print "        [--af start:stop] [--ae start:stop] [-c port] [-b h|s] [-g] [-z]"
		print "        [-Y] [-n] [-h|?]"
		print ""
		print "Parameters:"
		print "-d      Device name. Must be applied when programming the device."
		print "--if    Name of FLASH input file. Required for programming or verification"
		print "        of the FLASH memory. The file format is Intel Extended HEX."
		print "--ie    Name of EEPROM input file. Required for programming or verification"
		print "        of the EEPROM memory. The file format is Intel Extended HEX."
		print "--of    Name of FLASH output file. Required for readout of the FLASH memory."
		print "        The file format is Intel Extended HEX."
		print "--oe    Name of EEPROM output file. Required for readout of the EEPROM"
		print "        memory. The file format is Intel Extended HEX."
		print "-s      Read signature bytes."
		print "-O      Read oscillator calibration byte. 'index' is optional."
		print "--O#    User-defined oscillator calibration value."
		print "--Sf    Write oscillator cal. byte to FLASH memory. 'addr' is byte address."
		print "--Se    Write oscillator cal. byte to EEPROM memory. 'addr' is byte address."
		print "-e      Erase device. If applied with another programming parameter, the"
		print "        device will be erased before any other programming takes place."
		print "-p      Program device; FLASH (f), EEPROM (e) or both (b). Corresponding"
		print "        input files are required."
		print "-r      Read out device; FLASH (f), EEPROM (e) or both (b). Corresponding"
		print "        output files are required"
		print "-v      Verify device; FLASH (f), EEPROM (e) or both (b). Can be used with"
		print "        -p or alone. Corresponding input files are required."
		print "-l      Set lock byte. 'value' is an 8-bit hex. value."
		print "-L      Verify lock byte. 'value' is an 8-bit hex. value to verify against."
		print "-y      Read back lock byte."
		print "-f      Set fuse bytes. 'value' is a 16-bit hex. value describing the"
		print "        settings for the upper and lower fuse bytes."
		print "-E      Set extended fuse byte. 'value' is an 8-bit hex. value describing the"
		print "        extend fuse settings."
		print "-F      Verify fuse bytes. 'value' is a 16-bit hex. value to verify against."
		print "-G      Verify extended fuse byte. 'value' is an 8-bit hex. value to"
		print "        verify against."
		print "-q      Read back fuse bytes."
		print "-n      Send/receive encrypted hex files."
		print "-x      Fill unspecified locations with a value (00-ff). The default is"
		print "        to not program locations not specified in the input files."
		print "--af    FLASH address range. Specifies the address range of operations. The"
		print "        default is the entire FLASH. Byte addresses in hex."
		print "--ae    EEPROM address range. Specifies the address range of operations."
		print "        The default is the entire EEPROM. Byte addresses in hex."
		print "-c      Select communication port; 'COM1' to 'COM8', '/dev/tty0', /dev/ttyUSB0."
		print "        Deprecated: It is suggested to use settings in the configuration file."
		print "-b      Get revisions; hardware revision (h) and software revision (s)."
		print "-g      Silent operation."
		print "-z      No progress indicator. E.g. if piping to a file for log purposes."
		print "-Y      Calibrate internal RC oscillator(AVR057). 'addr' is byte address"
		print "        this option to avoid the characters used for the indicator."
		print "-h|-?   Help information (overrides all other settings)."
		print ""

