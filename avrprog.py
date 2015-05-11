"""
	avrprog.py
	AVR programmer and bootloader
"""
import avrlog
import types

class AVRProgrammer:
	"""
		AVRProgrammer class.
		Singleton class that represents the programmer. It attempts
		to sync with the device bootloader and determine the bootloader
		type. If successful, a AVRBootloader is instantiated and
		subsequently used as the main interface point.
	"""

	__instance = None
	def __init__(self, port):

		if AVRProgrammer.__instance != None:
			raise AVRProgrammer.__instance

		AVRProgrammer.__instance = self
		self.__port = port


	def instance(port=None):

		if AVRProgrammer.__instance is None:
			for i in range(0, 10):				# sync with programmer
				port.write(chr(27))
				port.flush()

			port.write('S')						# get programmer ID
			port.flush()

			pid = port.read(7)
			avrlog.avrlog(avrlog.LOG_DEBUG, 'Read programmer ID: (%s)' % pid)
			if pid == 'AVRBOOT':
				AVRProgrammer.__instance = AVRBootloader.instance(port)
			else:
				raise RuntimeError('AVR programmer not found.')

		return AVRProgrammer.__instance
	instance = staticmethod(instance)


class AVRBootloader:

	__instance = None
	def __init__(self, port):

		if AVRBootloader.__instance != None:
			raise AVRProgrammer.__instance

		AVRBootloader.__instance = self
		self.__port = port
		self.__page_size = -1


	def get_page_size(self):

		return self.__page_size


	def set_page_size(self, size):

		self.__page_size = size


	def enter_programming_mode(self):

		return True


	def leave_programming_mode(self):

		return True


	def chip_erase(self):

		result = True
		self.__port.write('e')
		self.__port.flush()

		if self.__port.read(1) != '\r':
			result = False
			avrlog.avrlog(avrlog.LOG_ERR, 'Chip erase failed! Programmer did not ack.')

		return result


	def rc_calibrate(self):

		return (False, '')


	def read_osccal(self, pos):

		return (False, 0)


	def read_signature(self):

		self.__port.write('s')
		self.__port.flush()

		sig0 = None
		sig1 = None
		sig2 = None
		sigs = self.__port.read(3)
		if len(sigs) == 3:
			sig2 = ord(sigs[0])
			sig1 = ord(sigs[1])
			sig0 = ord(sigs[2])
		return(sig0, sig1, sig2)


	def check_signature(self, sig0, sig1, sig2):

		result = True
		chk0, chk1, chk2 = self.read_signature()
		if chk0 != sig0 or chk1 != sig1 or chk2 != sig2:
			result = False
			avrlog.avrlog(avrlog.LOG_ERR,
			    'Signature does not match selected device: ' +
			    '0x%02x 0x%02x 0x%02x vs %02x %02x %02x' %
			    (ord(chk0), ord(chk1), ord(chk2), ord(sig0), ord(sig1), ord(sig2)))
		return result


	def write_flash_byte(self, address, value):

		if type(value) == types.IntType and value < 0x100 and \
		   type(address) == types.IntType:
			self.set_address(address >> 1)		# Flash operations use word addresses.
			if address & 0x01:
				value = (value << 8) | 0x00ff
			else:
				value = value | 0xff00

			self.write_flash_low_byte(value & 0xff)
			self.write_flash_high_byte(value >> 8)

			self.set_address(address >> 1)
			self.write_flash_page()
		else:
			raise RuntimeError('AVRBootloader.write_flash_bytes received %s:%s, ' %
			                   (str(type(address)), str(type(value))) +
			                   'expected IntType')


	def write_eeprom_byte(self, address, value):

		if type(value) == types.IntType and value < 0x100 and \
		   type(address) == types.IntType:
			self.set_address(address)
			result = True
			self.__port.write('D')
			self.__port.write(chr(value))
			self.__port.flush()

			if self.__port.read(1) != '\r':
				result = False
				avrlog.avrlog(avrlog.LOG_ERR, 'Write eeprom byte failed! ' +
				              'Programmer did not ack.')

			return result
		else:
			raise RuntimeError('AVRBootloader.write_flash_bytes received %s:%s, ' %
			                   (str(type(address)), str(type(value))) +
			                   'expected IntType')


	def write_flash(self, hex_file):

		if self.__page_size == -1:
			raise RuntimeError('Programmer page size not set!')

		self.__port.write('b')
		self.__port.flush()

		if self.__port.read(1) == 'Y':
			avrlog.avrlog(avrlog.LOG_DEBUG, 'Using block mode...')
			return self.write_flash_block(hex_file)

		start = hex_file.get_range_start()
		end = hex_file.get_range_end()

		# check autoincrement support
		self.__port.write('a')
		self.__port.flush()

		autoincrement = False
		if self.__port.read(1) == 'Y':
			autoincrement = true

		self.set_address(start >> 1)	# flash operations use word addresses

		address = start
		if address & 1:
			self.write_flash_low_byte(0xff)
			self.write_flash_high_byte(hex_file.get_data(address))
			address += 1
			if address % self.__page_size == 0 or address > end:
				self.set_address((address - 2) >> 1)
				self.write_flash_page()
				self.set_address(address >> 1)

		while (end - address + 1) >= 2:
			if not autoincrement:
				self.set_address(address >> 1)
			self.write_flash_low_byte(hex_file.get_data(address))
			self.write_flash_high_byte(hex_file.get_data(address + 1))
			address += 2

			if address % 256 == 0:
				avrlog.progress('.')

			if address % self.__page_size == 0 or address > end:
				self.set_address((address - 2) >> 1)
				self.write_flash_page()
				self.set_address(address >> 1)

		if address == end:
			self.write_flash_low_byte(hex_file.get_data(address))
			self.write_flash_high_byte(0xff)
			address += 2
			self.set_address((address - 2) >> 1)
			self.write_flash_page()

		avrlog.progress('\n')
		return True


	def write_flash_block(self, hex_file):

		# Get block size assuming the 'b' command was just ack'ed with a 'Y'
		block_size = (ord(self.__port.read(1)) << 8) | ord(self.__port.read(1))

		start = hex_file.get_range_start()
		end = hex_file.get_range_end()

		address = start
		if address & 1:
			self.set_address(address >> 1)		# Flash operations use word addresses

			# Use only high byte
			self.write_flash_low_byte(0xff)
			self.write_flash_high_byte(hex_file.get_data(address))
			address += 1

			if address % self.__page_size == 0 or address > end:
				self.set_address((address - 2) >> 1)
				self.write_flash_page()
				self.set_address(address >> 1)

		if (address % block_size) > 0:
			byte_count = block_size - (address & block_size)

			if (address + byte_count - 1) > end:
				byte_count = end - address + 1
				byte_count &= ~0x01				# Adjust to word count

			if byte_count > 0:
				self.set_address(address >> 1)

				self.__port.write('B')
				self.__port.write(chr((byte_count >> 8) & 0xff))
				self.__port.write(chr(byte_count & 0xff))
				self.__port.write('F')

				while byte_count > 0:
					self.__port.write(hex_file.get_data(address))
					address += 1
					byte_count -= 1

				if self.__port.read(1) != '\r':
					raise RuntimeError('Writing Flash block failed! ' +
					                   'Programmer did not return CR after B..F command')
				avrlog.progress('.')

		while (end - address + 1) >= block_size:

			byte_count = block_size

			self.set_address(address >> 1)

			self.__port.write('B')
			self.__port.write(chr((byte_count >> 8) & 0xff))
			self.__port.write(chr(byte_count & 0xff))
			self.__port.write('F')

			while byte_count > 0:
				self.__port.write(chr(hex_file.get_data(address)))
				address += 1
				byte_count -= 1

			if self.__port.read(1) != '\r':
				raise RuntimeError('Writing Flash block failed! ' +
				                   'Programmer did not return CR after B..F command')
			avrlog.progress('.')

		if (end - address + 1) >= 1:

			byte_count = (end - address + 1)
			if byte_count & 1:
				byte_count += 1

			self.set_address(address >> 1)

			self.__port.write('B')
			self.__port.write(chr((byte_count >> 8) & 0xff))
			self.__port.write(chr(byte_count & 0xff))
			self.__port.write('F')

			while byte_count > 0:
				if address > end:
					self.__port.write(chr(0xff))
				else:
					self.__port.write(chr(hex_file.get_data(address)))
				address += 1
				byte_count -= 1

			if self.__port.read(1) != '\r':
				raise RuntimeError('Writing Flash block failed! ' +
				                   'Programmer did not return CR after B..F command')
			avrlog.progress('.')

		avrlog.progress('\n')

		return True


	def read_flash(self, hex_file):

		if self.__page_size == -1:
			raise RuntimeError('Programmer page size is not set.')

		self.__port.write('b')
		self.__port.flush()

		if self.__port.read(1) == 'Y':
			avrlog.avrlog(avrlog.LOG_DEBUG, 'Read flash: using block mode...')
			return self.read_flash_block(hex_file)

		start = hex_file.get_range_start()
		end = hex_file.get_range_end()

		self.__port.write('a')
		self.__port.flush()

		auto_increment = False
		if self.__port.read(1) == 'Y':
			auto_increment = True

		self.set_address(start >> 1)

		address = start
		if address & 1:
			self.__port.write('R')
			self.__port.flush()

			hex_file.set_data(address, self.__port.read(1))		# High byte
			self.__port.read(1)									# Don't use low byte
			address += 1

		while (end - address + 1) >= 2:
			if not auto_increment:
				self.set_address(address >> 1)

			self.__port.write('R')
			self.__port.flush()

			hex_file.set_data(address + 1, self.__port.read(1))
			hex_file.set_data(address, self.__port.read(1))
			address += 2
			
			if address % 256 == 0:
				avrlog.progress('.')

		if address == end:
			self.__port.write('R')
			self.__port.flush()

			self.__port.read(1)
			hex_file.set_data(address, self.__port.read(1))

		avrlog.progress('\n')


	def read_flash_block(self, hex_file):

		# Get block size assuming the 'b' command was just ack'ed with a 'Y'
		block_size = (ord(self.__port.read(1)) << 8) | ord(self.__port.read(1))

		start = hex_file.get_range_start()
		end = hex_file.get_range_end()

		address = start
		if address & 1:
			self.set_address(address >> 1)		# Flash operations use word addresses

			self.__port.write('R')
			self.__port.flush()

			hex_file.set_data(address, self.__port.read(1))		# Save high byte
			self.__port.read(1)									# Skip low byte
			address += 1

		if (address % block_size) > 0:
			byte_count = block_size - (address % block_size)

			if (address + byte_count - 1) > end:
				byte_count = end - address + 1
				byte_count &= ~0x01

			if byte_count > 0:
				self.set_address(address >> 1)

				# Start Flash block read
				self.__port.write('g')
				self.__port.write(chr((byte_count >> 8) & 0xff))
				self.__port.write(chr(byte_count & 0xff))
				self.__port.write('F')

				while byte_count > 0:
					hex_file.set_data(address, self.__port.read(1))
					address += 1
					byte_count -= 1

				avrlog.progress('.')

		while (end - address + 1) >= block_size:
			byte_count = block_size

			self.set_address(address >> 1)

			# Start Flash block read
			self.__port.write('g')
			self.__port.write(chr((byte_count >> 8) & 0xff))
			self.__port.write(chr(byte_count & 0xff))
			self.__port.write('F')

			while byte_count > 0:
				hex_file.set_data(address, self.__port.read(1))
				address += 1
				byte_count -= 1

			avrlog.progress('.')

		if (end - address + 1) >= 1:
			byte_count = (end - address + 1)
			if byte_count & 1:
				byte_count += 1

			self.set_address(address >> 1)

			# Start Flash block read
			self.__port.write('g')
			self.__port.write(chr((byte_count >> 8) & 0xff))
			self.__port.write(chr(byte_count & 0xff))
			self.__port.write('F')

			while byte_count > 0:
				if address > end:
					self.__port.read(1)
				else:
					hex_file.set_data(address, self.__port.read(1))

				address += 1
				byte_count -= 1

			avrlog.progress('.')

		avrlog.progress('\n')

		return True


	def write_eeprom(self, hex_file):

		self.__port.write('b')
		self.__port.flush()

		if self.__port.read(1) == 'Y':
			avrlog.avrlog(avrlog.LOG_DEBUG, 'Write EEPROM using block mode...')

		start = hex_file.get_range_start()
		end = hex_file.get_range_end()

		self.__port.write('a')
		self.__port.flush()

		auto_increment = False
		if self.__port.read(1) == 'Y':
			auto_increment = True

		self.set_address(start)

		address = start
		while address <= end:

			if not auto_increment:
				self.set_address(address)

			self.__port.write('D')
			self.__port.write(hex_file.get_data(address))
			self.__port.flush()

			if self.__port.read(1) != '\r':
				raise RuntimeError('Writing byte to EEPROM failed! ' +
				                   'Programmer did not ack command.')
			if address % 256 == 0:
				avrlog.progress('.')

			address += 1

		avrlog.progress('\n')

		return True


	def write_eeprom_block(self, hex_file):

		# Get block size assuming the 'b' command was just ack'ed with a 'Y'
		block_size = (self.__port.read(1) << 8) | self.__port.read(1)

		start = hex_file.get_range_start()
		end = hex_file.get_range_end()

		address = start
		while address <= end:
			byte_count = block_size
			if (address + byte_count - 1) > end:
				byte_count = end - address + 1

			self.set_address(address)

			self.__port.write('B')
			self.__port.write(chr((byte_count >> 8) & 0xff))
			self.__port.write(chr(byte_count & 0xff))
			self.__port.write('E')

			while byte_count > 0:
				self.__port.write(hex_file.get_data(address))
				self.__port.flush()

				address += 1
				byte_count -= 1

			if self.__port.read(1) != '\r':
				raise RuntimeError('Writing EEPROM block failed! ' +
				                   'Programmer did not ack B..E command.')

			avrlog.progress('.')

		avrlog.progress('\n')

		return True


	def read_eeprom(self, hex_file):

		self.__port.write('b')
		self.__port.flush()

		if self.__port.read(1) == 'Y':
			avrlog.avrlog(avrlog.LOG_DEBUG, 'Read EEPROM: using block mode...')
			return self.read_eeprom_block(hex_file)

		start = hex_file.get_range_start()
		end = hex_file.get_range_end()

		self.__port.write('a')
		self.__port.flush()

		auto_increment = False
		if self.__port.read(1) == 'Y':
			auto_increment = True

		self.set_address(start)

		address = start
		while address <= end:
			if not auto_increment:
				self.set_address(address)

			self.__port.write('d')
			self.__port.flush()

			hex_file.set_data(address, self.__port.read(1))

			if address % 256 == 0:
				avrlog.progress('.')

			address += 1

		avrlog.progress('\n')

		return True


	def read_eeprom_block(self, hex_file):

		# Get block size assuming the 'b' command was just ack'ed with a 'Y'
		block_size = (ord(self.__port.read(1)) << 8) | ord(self.__port.read(1))

		start = hex_file.get_range_start()
		end = hex_file.get_range_end()

		address = start
		while address <= end:
			byte_count = block_size
			if (address + byte_count - 1) > end:
				byte_count = end - address + 1

			self.set_address(address)

			self.__port.write('g')
			self.__port.write(chr((byte_count >> 8) & 0xff))
			self.__port.write(chr(byte_count & 0xff))
			self.__port.write('E')

			while byte_count > 0:
				hex_file.set_data(address, self.__port.read(1))

				address += 1
				byte_count -= 1

			avrlog.progress('.')

		avrlog.progress('\n')

		return True


	def write_lock_bits(self, value):

		if type(value) == types.IntType and value < 0x100:
			self.__port.write('l')
			self.__port.write(chr(value & 0xff))
			self.__port.flush()

			bits = self.__port.read(1)

			return(True, bits)
		else:
			raise RuntimeError('AVRBootloader.write_lock_bits received %s, ' %
			                   str(type(value)) +
			                   'expected IntType')


	def read_lock_bits(self):

		self.__port.write('r')
		self.__port.flush()

		bits = self.__port.read(1)

		return(True, ord(bits))


	def write_fuse_bits(self, bits):

		return False


	def read_fuse_bits(self):

		self.__port.write('N')
		self.__port.flush()

		highfuse = self.__port.read(1)

		self.__port.write('F')
		self.__port.flush()

		lowfuse = self.__port.read(1)

		bits = (ord(highfuse) << 8) | ord(lowfuse)

		return(True, bits)


	def write_extended_fuse_bits(self):

		return False


	def read_extended_fuse_bits(self):

		result = True
		self.__port.write('Q')
		self.__port.flush()

		bits = self.__port.read(1)

		return(True, ord(bits))


	def programmer_software_version(self):

		result = True
		self.__port.write('V')
		self.__port.flush()

		major = self.__port.read(1)
		minor = self.__port.read(1)

		return(True, major, minor)


	def programmer_hardware_version(self):

		return(false, 0, 0)


	def set_address(self, address):

		result = True
		if address < 0x10000:
			self.__port.write('A')
			self.__port.write(chr(((address >> 8) & 0xff)))
			self.__port.write(chr(address & 0xff))
			self.__port.flush()
		else:
			self.__port.write('H')
			self.__port.write(chr(((address >> 16) & 0xff)))
			self.__port.write(chr(((address >> 8) & 0xff)))
			self.__port.write(chr(address & 0xff))
			self.__port.flush()

		if self.__port.read(1) != '\r':
			result = False
			avrlog.avrlog(avrlog.LOG_ERR, 'Setting address failed! ' +
			              'Programmer did not ack.')

		return result


	def write_flash_low_byte(self, value):

		if type(value) == types.IntType and value < 0x100:
			result = True
			self.__port.write('c')
			self.__port.write(chr(value))
			self.__port.flush()

			if self.__port.read(1) != '\r':
				result = False
				avrlog.avrlog(avrlog.LOG_ERR, 'Write flash low byte failed! ' +
				              'Programmer did not ack.')

			return result
		else:
			raise RuntimeError('AVRBootloader.write_flash_low_byte received %s, ' %
			                   str(type(value)) +
			                   'expected IntType')


	def write_flash_high_byte(self, value):

		if type(value) == types.IntType and value < 0x100:
			result = True
			self.__port.write('C')
			self.__port.write(chr(value))
			self.__port.flush()

			if self.__port.read(1) != '\r':
				result = False
				avrlog.avrlog(avrlog.LOG_ERR, 'Write flash high byte failed! ' +
				              'Programmer did not ack.')

			return result
		else:
			raise RuntimeError('AVRBootloader.write_flash_high_byte received %s, ' %
			                   str(type(value)) +
			                   'expected IntType')


	def write_flash_page(self):

		result = True
		self.__port.write('m')
		self.__port.flush()

		if self.__port.read(1) != '\r':
			result = False
			avrlog.avrlog(avrlog.LOG_ERR,
			              'Write flash page failed! Programmer did not ack.')

		return result


	def instance(port=None):

		if AVRBootloader.__instance is None:
			AVRBootloader.__instance = AVRBootloader(port)
		return AVRBootloader.__instance
	instance = staticmethod(instance)






