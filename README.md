# AVRLoader
AVR Open Source Bootloader Programmer

A Python port of the Atmel AVROSP application (application note AVR911).

Since there seemed to be no Linux port of this application, it was decided
to implement a port to Python. 

From Atmel:  
  *The AVR Open Source Programmer (AVROSP) is an AVR programmer application  
  *equivalent to the AVRProg tool included in AVR Studio. It is a  
  *command-line tool, using the same syntax as the other command-line tools  
  *in AVR Studio. The open source code and its modular design make  
  *it easy to port the application to other platforms and to add support  
  *for other programmer types and communication channels. Currently,  
  *AVROSP supports the programmers described in AVR109 and AVR910  
  *through the standard PC serial port. The application note describes how  
  *to add more support. AVROSP reads and writes Intel HEX files, and  
  *can use an existing AVR Studio installation to get required device  
  *parameters. This means that AVROSP automatically supports all  
  *devices supported by AVR Studio. No update is required for future AVR  
  *devices other than keeping your AVR Studio installation up to date.  
  
  *Q. How to use AVROSP without installing AVR Studio 4?  
  *A. AVR911 uses XML files from AVR Studio when communicating with  
      AVR109: Self Programming. The XMLfiles available with AVR Studio 5
      or later cannot be used with AVR911 because of a change in XML file
      format. This issue can be overcome by providing the XML files in a 
      folder and modifying the search path in AVR911. The attached zip file
      contains XML files that come with AVR Studio 4.19 build 730. This can
      be downloaded and extracted to a folder and provide the path to the 
      extracted folder as the XML search path in AVR911. Download and extract
      AVR911 zip file from http://www.atmel.com/Images/AVR911.zip...
     
The XML file path is specified with the def_path variable in the Devices
section of avrloader.cfg file.

Command Line Switches:
        [-d device name] [--if infile] [--ie infile] [--of outfile]
        [--oe outfile] [-s] [-O index] [--O# value] [--Sf addr] [--Se addr]
        [-e] [--p[f|e|b]] [--r[f|e|b]] [--v[f|e|b]] [-l value] [-L value]
        [-y] [-f value] [-E value] [-F value] [-G value] [-q] [-x value]
        [--af start:stop] [--ae start:stop] [-c port] [-b h|s] [-g] [-z]
        [-Y] [-n] [-h|?]

Parameters:
-d      Device name. Must be applied when programming the device.
--if    Name of FLASH input file. Required for programming or verification
        of the FLASH memory. The file format is Intel Extended HEX.
--ie    Name of EEPROM input file. Required for programming or verification
        of the EEPROM memory. The file format is Intel Extended HEX.
--of    Name of FLASH output file. Required for readout of the FLASH memory.
        The file format is Intel Extended HEX.
--oe    Name of EEPROM output file. Required for readout of the EEPROM
        memory. The file format is Intel Extended HEX.
-s      Read signature bytes.
-O      Read oscillator calibration byte. 'index' is optional.
--O#    User-defined oscillator calibration value.
--Sf    Write oscillator cal. byte to FLASH memory. 'addr' is byte address.
--Se    Write oscillator cal. byte to EEPROM memory. 'addr' is byte address.
-e      Erase device. If applied with another programming parameter, the
        device will be erased before any other programming takes place.
-p      Program device; FLASH (f), EEPROM (e) or both (b). Corresponding
        input files are required.
-r      Read out device; FLASH (f), EEPROM (e) or both (b). Corresponding
        output files are required
-v      Verify device; FLASH (f), EEPROM (e) or both (b). Can be used with
        -p or alone. Corresponding input files are required.
-l      Set lock byte. 'value' is an 8-bit hex. value.
-L      Verify lock byte. 'value' is an 8-bit hex. value to verify against.
-y      Read back lock byte.
-f      Set fuse bytes. 'value' is a 16-bit hex. value describing the
        settings for the upper and lower fuse bytes.
-E      Set extended fuse byte. 'value' is an 8-bit hex. value describing the
        extend fuse settings.
-F      Verify fuse bytes. 'value' is a 16-bit hex. value to verify against.
-G      Verify extended fuse byte. 'value' is an 8-bit hex. value to
        verify against.
-q      Read back fuse bytes.
-n      Send/receive encrypted hex files.
-x      Fill unspecified locations with a value (00-ff). The default is
        to not program locations not specified in the input files.
--af    FLASH address range. Specifies the address range of operations. The
        default is the entire FLASH. Byte addresses in hex.
--ae    EEPROM address range. Specifies the address range of operations.
        The default is the entire EEPROM. Byte addresses in hex.
-c      Select communication port; 'COM1' to 'COM8', '/dev/tty0', /dev/ttyUSB0.
        Deprecated: It is suggested to use settings in the configuration file.
-b      Get revisions; hardware revision (h) and software revision (s).
-g      Silent operation.
-z      No progress indicator. E.g. if piping to a file for log purposes.
-Y      Calibrate internal RC oscillator(AVR057). 'addr' is byte address
        this option to avoid the characters used for the indicator.
-h|-?   Help information (overrides all other settings).

This code is implemented as bootloader mode only and tested with Python 2.7
on Ubuntu 12.04. Not tested on the Windows OS.

Requires the pyserial Python module.
