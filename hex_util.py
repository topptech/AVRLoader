"""
	hex_util.py
	Hex file utility classes and functions.
"""
import binascii
import bisect
import avrlog
import types
import array

class HexRecord():
	"""
		HexRecord class.
		Represents a line, or hex record, of a hex file.
	"""
	def __init__(self):

		self._length = -1
		self._offset = -1
		self._type = -1
		self._checksum = -1
		self._data = bytearray(chr(0xff) * 16)


	def set_length(self, length):

		self._length = length


	def set_offset(self, offset):

		self._offset = offset


	def set_type(self, type):

		self._type = type


	def set_data(self, data):

		self._data = bytearray(data)


	def get_length(self):

		return self._length


	def get_offset(self):

		return self._offset


	def get_type(self):

		return self._type


	def get_data(self):

		return self._data


	def is_in_range(self, address):

		result = False
		if address >= self._offset and address < (self._offset + self._length):
			result = True
		return result


	def get_checksum(self):

		if self._checksum == -1:
			self.checksum()
		return self._checksum


	def checksum(self):

		self._checksum = self._length
		self._checksum += ((self._offset >> 8) & 0xff)
		self._checksum += (self._offset & 0xff)
		self._checksum += self._type

		for i in range(0, self._length):
			self._checksum += self._data[i]

		self._checksum = 0 - self._checksum
		self._checksum = (self._checksum & 0xff)

		return self._checksum


	def from_string(self, hex_line):
		"""
			Parses a line from a hex file.
		"""

		if len(hex_line) < 11:
			raise RuntimeError('Incorrect Hex file format, missing fields. ' +
			                   'Line from file (%s)' % (hex_line.strip()))

		if hex_line[0] != ':':
			raise RuntimeError('Incorrect Hex file format, does not start with a colon. ' +
			                   'Line from file (%s)' % (hex_line.strip()))

		self._length = int(hex_line[1:3], 16)
		self._offset = int(hex_line[3:7], 16)
		self._type = int(hex_line[7:9], 16)

		if len(hex_line) < (self._length * 2 + 11):
			raise RuntimeError('Incorrect Hex file format, missing field. ' +
			                   'Line from file (%s)' % (hex_line.strip()))

		checksum = self._length
		checksum += ((self._offset >> 8) & 0xff)
		checksum += (self._offset & 0xff)
		checksum += self._type

		adata = hex_line[9:(self._length*2+9)]
		if len(adata) % 2 != 0:
			raise RuntimeError('Incorrect Hex file format, invalid data. ' +
			                   'Line from file (%s)' % (hex_line.strip()))

		bdata = binascii.a2b_hex(adata)
		j = 0
		for b in bdata:
			checksum += ord(b)
			self._data[j] = b
			j += 1

		checksum += int(hex_line[-2:], 16)
		checksum &= 0xff
		if checksum != 0:
			raise RuntimeError('Incorrect Hex file format, invalid checksum. ' +
			                   'Line from file (%s)' % (hex_line.strip()))


	def __str__(self):
		"""
			Returns a hex file line string.
		"""

		result = ''

		if self._checksum == -1:
			self.checksum()

		result = ':%02X%04X%02X' % (self._length, self._offset, self._type)

		for i in range(0, self._length):
			result = '%s%02X' % (result, self._data[i])

		result = '%s%02X' % (result, (self._checksum & 0xff))
		return result


class EncryptedHexRecord(HexRecord):
	"""
		EncryptedHexRecord class.
		Represents a line, or hex record, of a hex file in encrypted form.
	"""

	def __init__(self):
		HexRecord.__init__(self)

		raise RuntimeError('Encrypted Hex file not implemented.')
		import xtea


	def from_record(self, hex_rec):

		self._length = hex_rec.get_length()
		self._offset = hex_rec.get_offset()
		self._type = hex_rec.get_type()
		self._data = hex_rec.get_data()
		self._checksum = -1


	def from_string(self, hex_line):

		if len(hex_line) < 11:
			raise RuntimeError('Incorrect Hex file format, missing fields. ' +
			                   'Line from file (%s)' % (hex_line.strip()))

		if hex_line[0] != ':':
			raise RuntimeError('Incorrect Hex file format, does not start with a colon. ' +
			                   'Line from file (%s)' % (hex_line.strip()))

		length = long(hex_line[1:5], 16)
		offset = long(hex_line[5:9], 16)
		v = [length, offset]
		self._length, self._offset = xtea.decipher(v, 0xffffL)

		rtype = long(hex_line[9:13], 16)
		tmp = long(hex_line[13:17], 16)
		v = [rtype, tmp]
		self._type, tmp = xtea.decipher(v, 0xffffL)

		if len(hex_line) < (self._length * 4 + 25):
			raise RuntimeError('Incorrect Hex file format, missing field. ' +
			                   'Line from file (%s)' % (hex_line.strip()))

		adata = hex_line[17:-8]

		if len(adata) % 8 != 0:
			raise RuntimeError('Incorrect Hex file format, invalid data. ' +
			                   'Line from file (%s)' % (hex_line.strip()))

		j = 0
		for i in range(0, len(adata), 8):
			pair = adata[i:i+8]

			d1 = long(pair[0:4], 16)
			d2 = long(pair[4:8], 16)

			v = [d1, d2]

			l0, l1 = xtea.decipher(v, 0xffffL)
			self._data[j] = chr(l0 & 0xff)
			j += 1
			if j < self._length:
				self._data[j] = chr(l1 & 0xff)
				j += 1

		chk = hex_line.strip()[-8:]
		d1 = long(chk[0:4], 16)
		d2 = long(chk[4:8], 16)
		v = [d1, d2]
		v0, tmp = xtea.decipher(v, 0xffffL)

		checksum = v0 & 0xff

		if checksum != self.checksum():
			raise RuntimeError('Incorrect Hex file format, invalid checksum. ' +
			                   'Line from file (%s)' % (hex_line.strip()))


	def __str__(self):
		"""
			Returns an encrypted hex file line string.
		"""

		result = ''

		if self._checksum == -1:
			checksum = self.checksum()

		v = [long(self._length), long(self._offset)]
		v0, v1 = xtea.encipher(v, 0xffffL)
		result = ':%04X%04X' % (v0, v1)
		v[0] = long(self._type)
		v[1] = 0xffL
		v0, v1 = xtea.encipher(v, 0xffffL)
		result += '%04X%04X' % (v0, v1)

		for i in range(0, self._length, 2):
			try:
				v = [long(self._data[i]), long(self._data[i+1])]
				v0, v1 = xtea.encipher(v, 0xffffL)
				result += '%04X%04X' % (v0, v1)
			except IndexError:
				v = [self._data[-1], 0xffL]
				v0, v1 = xtea.encipher(v, 0xffffL)
				result += '%04X%04X' % (v0, v1)

		v[0] = long(self._checksum)
		v[1] = 0xffL
		v0, v1 = xtea.encipher(v, 0xffffL)
		result += '%04X%04X' % (v0, v1)

		return result


class HexFile():
	"""
		HexFile class.
		A class to represent a hex file. It contains 
	"""

	def __init__(self, buffersize, value=0xff):

		self.__data = bytearray(chr((value & 0xff)) * buffersize)
		self.__start = -1
		self.__end = -1
		self.__size = buffersize


	def _write_record(self, fp, hex_rec):

		fp.write('%02X\n' % str(hex_rec))


	def _parse_record(self, hex_line):	# returns HexRecord

		hex_rec = HexRecord()
		hex_rec.from_string(hex_line.strip())
		return hex_rec


	def read_file(self, file_name):

		fp = open(file_name, 'r')
		base_address = 0
		self.__start = self.__size
		self.__end = 0
		lines = fp.readlines()
		for line in lines:

			avrlog.progress('.')

			rec = self._parse_record(line.strip())
			if rec.get_type() == 0x00:
				if (base_address + rec.get_offset() + rec.get_length()) > self.__size:
					raise RuntimeError('Hex file defines data outside buffer limits.')

				for data_pos in range(0, rec.get_length()):
					self.__data[base_address + rec.get_offset() + data_pos] = rec._data[data_pos]

				if base_address + rec.get_offset() < self.__start:
					self.__start = base_address + rec.get_offset()

				if base_address + rec.get_offset() + rec.get_length() > self.__end:
					self.__end = base_address + rec.get_offset() + rec.get_length() - 1

			elif rec.get_type() == 0x01:
				fp.close()
				avrlog.progress('\n')
				return
			elif rec.get_type() == 0x02:
				base_address =  (rec._data[0] << 8) | rec._data[1]
				base_address <<= 4
			elif rec.get_type() == 0x03:
				pass
			elif rec.get_type() == 0x04:
				base_address =  (rec._data[0] << 8) | rec._data[1]
				base_address <<= 16
			elif rec.get_type() == 0x05:
				pass
			else:
				raise RuntimeError('Incorrect Hex file format, unsupported format. ' +
				                   'Line from file (%s)' % (hex_line))

		raise RuntimeError('Premature EOF encountered. ' +
		                   'Make sure file contains an EOF record.')


	def write_file(self, file_name):

		fp = open(file_name, 'w')

		base_address = self.__start & ~0xffff
		self._offset = self.__start & 0xffff

		rec = HexRecord()
		rec.set_length(2)
		rec.set_offset(0)
		rec.set_type(0x02)
		rec._data[1] = 0x00
		rec._data[0] = base_address >> 12
		self._write_record(fp, rec)

		rec = HexRecord()
		rec.set_length(self.__size)
		data_pos = 0
		while base_address + self._offset + data_pos <= self.__end:
			rec._data[data_pos] = self.__data[base_address + self._offset + data_pos]
			data_pos += 1

			# check if we need to write out the current data record
			#	reached 64k boundary or
			#	data record full or
			#	end of used range reached
			if self._offset + data_pos >= 0x10000 or \
			   data_pos >= 16 or \
			   base_address + self._offset + data_pos > self.__end:
				rec.set_length(data_pos)
				rec.set_offset(self._offset)
				rec.set_type(0x00)

				if data_pos % 256 == 0:
					avrlog.progress('.')

				self._write_record(fp, rec)

				self._offset += data_pos
				data_pos = 0

			# check if we have passed a 64k boundary
			if self._offset + data_pos >= 0x10000:
				# update address pointers
				self._offset -= 0x10000
				base_address += 0x10000

				# write new base address record to hex file
				rec.set_length(2)
				rec.set_offset(0)
				rec.set_type(0x02)
				# give 4k page index
				rec._data[0] = base_address >> 12
				rec._data[1] = 0x00

				self._write_record(fp, rec)

		# write EOF record
		rec.set_length(0)
		rec.set_offset(0)
		rec.set_type(0x01)

		self._write_record(fp, rec)

		fp.close()
		avrlog.progress('\n')


	def set_used_range(self, start, end):

		if start < 0 or end >= self.__size or start > end:
			raise RuntimeError('Invalid range! Start must be 0 or greater, ' +
			                   'end must be inside allowed memory range.')
		self.__start = start
		self.__end = end


	def clear_all(self, value=0xff):

		for i in range(0, self.__size):
			self.__data[i] = chr((value & 0xff))


	def get_range_start(self):

		return self.__start


	def get_range_end(self):

		return self.__end


	def get_data(self, address):	# returns from byte array

		if address < 0 or address >= self.__size:
			raise RuntimeError('Address outside valid range!')
		return self.__data[address]


	def set_data(self, address, value):

		if type(value) != types.StringType or len(value) != 1:
			raise RuntimeError('HexFile.set_data() invalid value.')

		if address < 0 or address >= self.__size:
			raise RuntimeError('Address outside valid range!')
		self.__data[address] = value[0]


	def get_size(self):

		return self.__size


class EncryptedHexFile(HexFile):
	
	def __init__(self, buffersize, value=0x00ff):

		raise RuntimeError('Encrypted Hex file not implemented.')
		import xtea

		self.__start = -1
		self.__end = -1
		self.__default_value = value
		self.__size = buffersize
		self.__base_address = -1
		self.__records = {}
		self.__keys = []


	def _parse_record(self, hex_line):	# returns EncryptedHexRecord

		hex_rec = EncryptedHexRecord()
		hex_rec.from_string(hex_line.strip())
		return hex_rec


	def _add_record(self, ehex_rec):

		self.__records[ehex_rec.get_offset()] = ehex_rec
		self.__keys = self.__records.keys()
		self.__keys.sort()


	def read_file(self, file_name):

		fp = open(file_name, 'r')
		base_address = 0
		self.__start = self.__size
		self.__end = 0
		lines = fp.readlines()
		for line in lines:

			avrlog.progress('.')

			rec = self._parse_record(line.strip())
			if rec.get_type() == 0x00:
				if (base_address + rec.get_offset() + rec.get_length()) > self.__size:
					raise RuntimeError('Hex file defines data outside buffer limits. %s' % line.strip())

				if self.__base_address + rec.get_offset() < self.__start:
					self.__start = self.__base_address + rec.get_offset()

				if self.__base_address + rec.get_offset() + rec.get_length() > self.__end:
					self.__end = self.__base_address + rec.get_offset() + rec.get_length() - 1

			elif rec.get_type() == 0x01:
				fp.close()
				avrlog.progress('\n')
				return
			elif rec.get_type() == 0x02:
				self.__base_address =  (rec._data[0] << 8) | rec._data[1]
				self.__base_address <<= 4
			elif rec.get_type() == 0x03:
				pass
			elif rec.get_type() == 0x04:
				self.__base_address =  (rec._data[0] << 8) | rec._data[1]
				self.__base_address <<= 16
			elif rec.get_type() == 0x05:
				pass
			else:
				raise RuntimeError('Incorrect Hex file format, unsupported format. ' +
				                   'Line from file (%s)' % (hex_line))

			self._add_record(rec)

		raise RuntimeError('Premature EOF encountered. ' +
		                   'Make sure file contains an EOF record.')


	def write_file(self, file_name):

		fp = open(file_name, 'w')

		rec = EncryptedHexRecord()
		rec.set_length(2)
		rec.set_offset(0)
		rec.set_type(0x02)
		rec._data[1] = 0x00
		rec._data[0] = self.__base_address >> 12
		self._write_record(fp, rec)

		for rec_oset in self.__keys():
			rec = self.__records[rec_oset]
			self._write_record(fp, rec)

			if data_pos % 256 == 0:
				avrlog.progress('.')

		# write EOF record
		rec.set_length(0)
		rec.set_offset(0)
		rec.set_type(0x01)

		self._write_record(fp, rec)

		fp.close()
		avrlog.progress('\n')


	def set_used_range(self, start, end):

		if start < 0 or end >= self.__size or start > end:
			raise RuntimeError('Invalid range! Start must be 0 or greater, ' +
			                   'end must be inside allowed memory range.')
		self.__start = start
		self.__end = end


	def clear_all(self, value=0xff):

		# TODO
		for i in range(0, self.__size):
			self.__data[i] = chr((value & 0xff))


	def get_range_start(self):

		return self.__start


	def get_range_end(self):

		return self.__end


	def _find_record_offset(self, address):

		i = bisect.bisect_right(self.__keys, address)
		if i == len(self.__keys) and address >= self.__size:
			raise RuntimeError('Address not found. Hex file address: 0x%04X' % address)

		key = self.__keys[i-1]
		rec = self.__records[key]
		offset = address - rec.get_offset()
		if offset < 0:
			raise RuntimeError('Address error. Data not found at 0x%04X' % address)

		return (rec, offset)


	def get_data(self, address):	# returns from byte array

		if address < 0 or address >= self.__size:
			raise RuntimeError('Address outside valid range!')

		rec, offset = self._find_record_offset(address)

		try:
			return rec._data[offset]
		except Exception, exc:
			raise RuntimeError('EncryptedHexFile.get_data: %s' % exc.message)


	def set_data(self, address, value):

		if type(value) != types.StringType or len(value) != 1:
			raise RuntimeError('HexFile.set_data() invalid value.')

		if address < 0 or address >= self.__size:
			raise RuntimeError('Address outside valid range!')

		rec, offset = self._find_record_offset(address)

		try:
			rec._data[offset] = value
		except Exception, exc:
			raise RuntimeError('EncryptedHexFile.set_data: %s' % exc.message)


	def get_size(self):

		return self.__size


if __name__ == "__main__":

	import sys
	import getopt

	file_name = ''
	out_name = ''
	try:
		optlist, args = getopt.getopt(sys.argv[1:], "f:o:")
		for (x, y) in optlist:
			if x == '-f':
				file_name = y
			elif x == '-o':
				out_name = y
			else:
				sys.exit(1)
	except:
		sys.exit(1)

	if len(file_name) == 0 or len(out_name) == 0:
		sys.exit(1)

	fp = open(file_name, 'r')
	lines = fp.readlines()
	fp.close()

	fp = open(out_name, 'w')

	rec = HexRecord()
	erec = EncryptedHexRecord()
	for l in lines:
		rec.from_string(l.strip())
		erec.from_record(rec)
		fp.write('%s\n' % str(erec))
	fp.close()


	ehf = EncryptedHexFile(32768)
	ehf.read_file(out_name)
	print 'read address      0: 0x%02X' % ehf.get_data(0)
	print 'read address 0x00af: 0x%02X' % ehf.get_data(0x00af)
	print 'read address 0x74fe: 0x%02X' % ehf.get_data(0x74fe)
	print 'read address 0x75a0: 0x%02X' % ehf.get_data(0x75a0)
	print 'read address 0x75af: 0x%02X' % ehf.get_data(0x75af)
	print 'read address 0x7fff: 0x%02X' % ehf.get_data(0x7fff)

