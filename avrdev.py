"""
	avrdev.py
	AVR Device utility
"""
from os.path import exists, join, abspath
from os import pathsep
import avrlog
import xml.etree.ElementTree as ET


class AVRDevice:
	"""
		AVRDevice class.
		This is a class to represent an AVR device. XML files that
		are part of the AVR Studio installation are used to provide
		the device schema. An AVRDevice object is instantiated given
		the device name in order to find and parse the device's XML
		file. 
	"""
	def __init__(self, device_name):

		self._device_name = device_name
		self._flash_size = -1
		self._eeprom_size = -1
		self._has_fuse_bits = False
		self._has_extended_fuse_bits = False
		self._sig0 = -1
		self._sig1 = -1
		self._sig2 = -1
		self._page_size = -1
		self._nrww_size = -1


	def get_device_name(self):

		return self._device_name


	def get_flash_size(self):

		return self._flash_size


	def get_eeprom_size(self):

		return self._eeprom_size


	def get_page_size(self):

		return self._page_size


	def get_nrww_size(self):

		return self._nrww_size


	def get_nrww_pages(self):

		return self._nrww_size * 2/ self._page_size


	def get_total_pages(self):

		return self._flash_size / self._page_size


	def get_fuse_status(self):

		return self._has_fuse_bits


	def get_ext_fuse_status(self):

		return self._has_extended_fuse_bits


	def get_signature(self):

		return(self._sig0, self._sig1, self._sig2)


	def read_avr_parameters(self, search_path):

		if len(self._device_name) <= 0:
			raise RuntimeError('A device name must be specified.')

		file_name = ''
		paths = search_path.split(pathsep)
		for path in paths:
			if exists(join(path, '%s.xml' % self._device_name)):
				file_name = join(path, '%s.xml' % self._device_name)

		if len(file_name) > 0:
			avrlog.avrlog(avrlog.LOG_DEBUG, 'found file: %s' % file_name)

			tree = ET.parse(file_name)
			if tree != None:
				memory = tree.getroot().find('MEMORY')
				if memory != None:
					prog_flash = memory.find('PROG_FLASH')
					if prog_flash != None and prog_flash.text.isdigit():
						self._flash_size = int(prog_flash.text)
					else:
						raise RuntimeError('Flash size not found for %s' %
						                   self._device_name)
					eeprom = memory.find('EEPROM')
					if eeprom != None and eeprom.text.isdigit():
						self._eeprom_size = int(eeprom.text)
					else:
						raise RuntimeError('EEPROM size not found for %s' %
						                   self._device_name)
					boot_cfg = memory.find('BOOT_CONFIG')
					if boot_cfg != None:
						page_size = boot_cfg.find('PAGESIZE')
						if page_size != None and page_size.text.isdigit():
							self._page_size = int(page_size.text) << 1
						nrww_start = -1
						nrww_stop = -1
						nrww_start_addr = boot_cfg.find('NRWW_START_ADDR')
						if nrww_start_addr != None and len(nrww_start_addr.text) > 2:
							nrww_start = int(nrww_start_addr.text[1:], 16)
						nrww_stop_addr = boot_cfg.find('NRWW_STOP_ADDR')
						if nrww_stop_addr != None and len(nrww_stop_addr.text) > 2:
							nrww_stop = int(nrww_stop_addr.text[1:], 16)
						if nrww_start > 0 and nrww_stop > nrww_start:
							self._nrww_size = nrww_stop - nrww_start + 1
				else:
					raise RuntimeError('Memory configuration not found in %s.xml.' %
					                   self._device_name)
				fuse = tree.getroot().find('FUSE')
				if fuse != None:
					self._has_fuse_bits = True
					ext_fuse = fuse.find('EXTENDED')
					if ext_fuse != None:
						self._has_extended_fuse_bits = True
				else:
					avrlog.avrlog(avrlog.LOG_DEBUG, 'Fuse bits not supported on %s' %
					              self._device_name)
				admin = tree.getroot().find('ADMIN')
				if admin != None:
					sig_sect = admin.find('SIGNATURE')
					if sig_sect != None:
						addr0 = sig_sect.find('ADDR000')
						if addr0 != None and len(addr0.text) == 3:
							self._sig0 = int(addr0.text[1:], 16)						
						else:
							raise RuntimeError('Signature 0 section not found in %s.xml.' %
							                   self._device_name)
						addr1 = sig_sect.find('ADDR001')
						if addr1 != None and len(addr1.text) == 3:
							self._sig1 = int(addr1.text[1:], 16)						
						else:
							raise RuntimeError('Signature 1 section not found in %s.xml.' %
							                   self._device_name)
						addr2 = sig_sect.find('ADDR002')
						if addr2 != None and len(addr2.text) == 3:
							self._sig2 = int(addr2.text[1:], 16)						
						else:
							raise RuntimeError('Signature 2 section not found in %s.xml.' %
							                   self._device_name)
					else:
						raise RuntimeError('Signature section not found in %s.xml.' %
						                   self._device_name)
				else:
					raise RuntimeError('Admin section not found in %s.xml.' %
					                   self._device_name)
			else:
				raise RuntimeError('Error parsing %s.xml.' %
				                   self._device_name)
		else:
			raise RuntimeError('%s XML file not found.' % self._device_name)

if __name__ == "__main__":
	"""
		The main routine provides a method to test the AVRDevice class.
	"""

	import getopt
	import os.path
	import sys

	dev_name = ''
	path = ''
	try:
		optlist, args = getopt.getopt(sys.argv[1:], "d:p:")
		for (x, y) in optlist:
			if x == '-d':
				dev_name = y
			elif x == '-p':
				path = y
			else:
				dev_name = ''
				break
	except:
		dev_name = ''

	if len(dev_name) > 0 and len(path) > 0:

		device = AVRDevice(dev_name)
		device.read_avr_parameters(path)

		print device.get_device_name()

		sig0, sig1, sig2 = device.get_signature()
		print '\t  Signature:\t%02X %02X %02X' % (sig0, sig1, sig2)

		print '\t Flash size:\t%d' % device.get_flash_size()

		print '\t  Page size:\t%d (%d bytes)' % \
		      (device.get_page_size(), device.get_page_size() * 2)

		print '\t  NRWW size:\t%d' % device.get_nrww_size()

		print '\t NRWW pages:\t%d' % device.get_nrww_pages()

		print '\tTotal pages:\t%d' % device.get_total_pages()
	else:
		print '%s -d device_name -p search_path' % os.path.basename(sys.argv[0])


