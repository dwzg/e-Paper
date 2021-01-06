# *****************************************************************************
# * | File        :	  epd4in2bc.py
# * | Author      :   Waveshare team, Dennis Witzig
# * | Function    :   Electronic paper driver
# * | Info        :
# *----------------
# * | This version:   V4.0
# * | Date        :   2019-06-20
# # | Info        :   python demo
# -----------------------------------------------------------------------------
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documnetation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to  whom the Software is
# furished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS OR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#

import logging
import itertools
from . import epdconfig

commands = {
    "PSR"  : 0x00,
    "PWR"  : 0x01,
    "POF"  : 0x02,
    "PFS"  : 0x03,
    "PON"  : 0x04,
    "PMES" : 0x05,
    "BTST" : 0x06,
    "DSLP" : 0x07,
    "DTM1" : 0x10,
    "DSP"  : 0x11,
    "DRF"  : 0x12,
    "DTM2" : 0x13,
    "PLL"  : 0x30,
    "TSC"  : 0x40,
    "TSE"  : 0x41,
    "TSW"  : 0x42,
    "TSR"  : 0x43,
    "CDI"  : 0x50,
    "LPD"  : 0x51,
    "TCON" : 0x60,
    "TRES" : 0x61,
    "GSST" : 0x65,
    "REV"  : 0x70,
    "FLG"  : 0x71,
    "VCOM" : 0x80,
    "VV"   : 0x81,
    "VDCS" : 0x82,
    "PTL"  : 0x90,
    "PTIN" : 0x91,
    "PTOUT": 0x92,
    "PGM"  : 0xA0,
    "APG"  : 0xA1,
    "ROTP" : 0xA2,
    "CCSET": 0xE0,
    "PWS"  : 0xE3,
    "TSSET": 0xE5,
    "LPSEL": 0xE4,
}

# Display resolution
EPD_WIDTH       = 400
EPD_HEIGHT      = 300

class EPD:
    def __init__(self):
        self.reset_pin = epdconfig.RST_PIN
        self.dc_pin = epdconfig.DC_PIN
        self.busy_pin = epdconfig.BUSY_PIN
        self.cs_pin = epdconfig.CS_PIN
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT

    # Hardware reset
    def reset(self):
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(200)
        epdconfig.digital_write(self.reset_pin, 0)
        epdconfig.delay_ms(5)
        epdconfig.digital_write(self.reset_pin, 1)
        epdconfig.delay_ms(200)

    def sendCommand(self, command):
        if command not in commands:
            return None
        code = commands[command]
        epdconfig.digital_write(self.dc_pin, 0)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([code])
        epdconfig.digital_write(self.cs_pin, 1)
        return code

    def sendData(self, data):
        epdconfig.digital_write(self.dc_pin, 1)
        epdconfig.digital_write(self.cs_pin, 0)
        epdconfig.spi_writebyte([data])
        epdconfig.digital_write(self.cs_pin, 1)

    def readBusy(self):
        logging.debug("e-Paper busy")
        self.sendCommand("FLG")
        while self.isBusy():
            self.sendCommand("FLG")
            epdconfig.delay_ms(20)
        logging.debug("e-Paper busy release")

    def isBusy(self):
        return epdconfig.digital_read(self.busy_pin) == 0

    def init(self):
        epdconfig.module_init()

        self.reset()

        self.sendCommand("PWR") # POWER SETTING
        self.sendData(0x03) # VDS_EN, VDG_EN
        self.sendData(0x00) # VCOM_HV, VGHL_LV[1], VGHL_LV[0]
        self.sendData(0x26) # VDH
        self.sendData(0x26) # VDL
        self.sendData(0x03) # VDHR

        self.sendCommand("BTST") # boost soft start
        self.sendData(0x17)
        self.sendData(0x17)
        self.sendData(0x17)

        self.sendCommand("PON") # POWER_ON
        self.readBusy()

        self.sendCommand("PSR")
        self.sendData(0x0F)
        self.sendData(0x0D)

        self.sendCommand("PLL") # PLL setting
        self.sendData(0x3C) # 3A 100HZ   29 150Hz 39 200HZ  31 171HZ

        self.sendCommand("TRES")	# resolution setting
        self.sendData(0x01)
        self.sendData(0x90)
        self.sendData(0x01)
        self.sendData(0x2B)

        self.sendCommand("VDCS") # vcom_DC setting
        self.sendData(0x00)

        self.sendCommand("CDI")
        self.sendData(0xD7)

    def getBuffer(self, image):
        buf = [0xFF] * (int(self.width/8) * self.height)
        image_monocolor = image.convert('1')
        imwidth, imheight = image_monocolor.size
        pixels = image_monocolor.load()
        if imwidth == self.width and imheight == self.height:
            logging.debug("Horizontal")
            for y in range(imheight):
                for x in range(imwidth):
                    # Set the bits for the column of pixels at the current position.
                    if pixels[x, y] == 0:
                        buf[int((x + y * self.width) / 8)] &= ~(0x80 >> (x % 8))
        elif imwidth == self.height and imheight == self.width:
            logging.debug("Vertical")
            for y in range(imheight):
                for x in range(imwidth):
                    newx = y
                    newy = self.height - x - 1
                    if pixels[x, y] == 0:
                        buf[int((newx + newy*self.width) / 8)] &= ~(0x80 >> (y % 8))
        return buf

    def display(self, imageBlack, imageRed):
        nBytes = int(self.width * self.height / 8)
        self.sendCommand("DTM1")
        for i in range(0, nBytes):
            self.sendData(imageBlack[i])

        self.sendCommand("DSP")

        self.sendCommand("DTM2")
        for i in range(0, nBytes):
            self.sendData(imageRed[i])

        self.sendCommand("DSP")

        self.sendCommand("DRF")
        epdconfig.delay_ms(20)
        self.readBusy()

    def clear(self):
        self.sendCommand("DTM1")
        for _ in itertools.repeat(None, (int(self.width * self.height / 8))):
            self.sendData(0xFF)

        self.sendCommand("DSP")

        self.sendCommand("DTM2")
        for _ in itertools.repeat(None, (int(self.width * self.height / 8))):
            self.sendData(0xFF)

        self.sendCommand("DSP")

        self.sendCommand("DRF")
        epdconfig.delay_ms(20)
        self.readBusy()

    def sleep(self):
        self.sendCommand("CDI")
        self.sendData(0xD7)

        self.sendCommand("POF") #power off
        self.readBusy() #waiting for the electronic paper IC to release the idle signal
        self.sendCommand("DSLP") #deep sleep
        self.sendData(0xA5) #check code

    def devExit(self):
        epdconfig.module_exit()
### END OF FILE ###

