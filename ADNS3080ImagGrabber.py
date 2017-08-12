#Read the Optical mouse value via SPI
#Pin layout
# RasPi  | ADNS3080
#  3V3   |   3.3V
#  GND   |   GND
# SPIMOSI|   MOSI
# SPIMISO|   MISO
# SPISCLK|   SCLK
# SPICE0 |   NCS
# GPIO25 |   RST

import spidev
import time
from Tkinter import *
from threading import Timer
import RPi.GPIO as GPIO

RESET_PIN = 25                                   #GPIO25 for reset ADNS3080
SS_PIN = 0                                       #GPIO8(CE0)  if choose GE1, set 1
SPI_MODE = 0b11                                  #SPI mode as two bit pattern of clock polarity and phase
                                                 #[CPOL|CPHA], min:0b00 = 0, max:0b11 = 3
SPI_MAX_SPEED = 2000000
SPI_OPEN = False

#Register Map for the ADNS3080 OpticalFlow Sensor
ADNS3080_PRODUCT_ID = 0x00
ADNS3080_CONFIGURATION_BITS = 0x0a
ADNS3080_MOTION_BURST = 0x50
ADNS3080_FRAME_CAPTURE = 0x13
ADNS3080_PRODUCT_ID_VALUE = 0x17

ADNS3080_PIXELS_X = 30
ADNS3080_PIXELS_Y = 30

class GUI():
    grid_size = 10
    pixelValue = [0 for i in range(ADNS3080_PIXELS_X*ADNS3080_PIXELS_Y)]
    position_X = 0
    position_Y = 0
    capture_image = True
    pixel_dictionary = {}
    plot_dpi = 100
    position_gap = (grid_size*ADNS3080_PIXELS_X) / 2

    def __init__(self, master):
        master.title("ADNS3080 Capture Image")        # set main window's title
        master.geometry("900x900")                    # set window's size
        
        self.canvas_for_Image = Canvas(master, width = self.grid_size*ADNS3080_PIXELS_X, height = self.grid_size*ADNS3080_PIXELS_Y)
        self.canvas_for_Image.place(x=0,y=0)

        self.canvas_for_Plot = Canvas(master, width = self.grid_size*ADNS3080_PIXELS_X, height = self.grid_size*ADNS3080_PIXELS_Y)
        self.canvas_for_Plot.place(x=0,y=self.grid_size*ADNS3080_PIXELS_Y)
        self.canvas_for_Plot.create_rectangle(0, 0, self.grid_size*ADNS3080_PIXELS_X, self.grid_size*ADNS3080_PIXELS_Y, width=0, fill="white")
        # make grid on plot area
        for i in range(6):
            for j in range(6):
                self.canvas_for_Plot.create_rectangle(j*50+1, i*50+1, (j+1)*50-1, (i+1)*50-1, width=0, fill="lightgray")
        self.canvas_for_Plot.create_text(100,100,text="Test")
        self.init_data = self.canvas_for_Plot.create_oval(self.position_X - self.grid_size/2 + self.position_gap, self.position_Y - self.grid_size/2 + self.position_gap,\
                                                         self.position_X + self.grid_size/2 + self.position_gap, self.position_Y + self.grid_size/2 + self.position_gap, fill = 'blue')
        self.old_data = self.init_data
        
        

        self.button_exit = Button(master, text="EXIT", width = 15, command = self.endProgram)
        self.button_exit.place(x=self.grid_size*ADNS3080_PIXELS_X,y=0)

        self.button_change_status = Button(master, text="Change", width = 15, command = self.change_status)
        self.button_change_status.place(x=self.grid_size*ADNS3080_PIXELS_X,y=self.grid_size*ADNS3080_PIXELS_Y)

        self.read_loop()                              # start attempts to read from ADNS3080 via SPI

    def plotData(self):
        self.canvas_for_Plot.delete(self.old_data)
        del(self.old_data)
        self.new_data = self.canvas_for_Plot.create_oval(self.position_X - self.grid_size/2 + self.position_gap, self.position_Y - self.grid_size/2 + self.position_gap,\
                                                         self.position_X + self.grid_size/2 + self.position_gap, self.position_Y + self.grid_size/2 + self.position_gap, fill = 'blue')
        self.old_data = self.new_data

    def __del__(self):
        self.endProgram()

    def endProgram(self):
        global SPI_OPEN
        try:
            self.timer.cancel()
            SPI_OPEN = False
        except:
            print("failed to exit program")

    def change_status(self):
        global SPI_OPEN
        self.timer.cancel()
        if self.capture_image == False:
            self.capture_image = True
        else:
            self.capture_image = False
        resetADNS3080()                               # must reset to change mode in ADNS3080 to get dx dy
        checkConnect()
        configuration()

    def read_loop(self):
        try:
            self.timer.cancel()
        except:
            hoge = 1 # do nothing

        if SPI_OPEN == True:
            if self.capture_image == True:
                self.printPixelData()
            else:
                self.updateDxDy()

            self.timer = Timer(0.0, self.read_loop)
            self.timer.start()
        else:
            hoge = 1 # do nothing
            
    def printPixelData(self):
        spiWrite(ADNS3080_FRAME_CAPTURE,[0x83])
        time.sleep(1510e-6)
        for column in range(ADNS3080_PIXELS_Y):
            for row in range(ADNS3080_PIXELS_X):
                if (SPI_OPEN == True & self.capture_image == True):
                    try:         # find the old pixel if it exists and delete it 
                        self.old_pixel = self.pixel_dictionary[row + column * ADNS3080_PIXELS_Y]
                        self.canvas_for_Image.delete(self.old_pixel)
                        del(self.old_pixel)
                    except:
                        hoge = 1 # do nothing
                    regValue = spiRead(ADNS3080_FRAME_CAPTURE,[0xff])
                    self.pixelValue[row + column * ADNS3080_PIXELS_X] = regValue[0] & 0x3f   #Only lower 6bits have data
                    colour = int(self.pixelValue[row + column * ADNS3080_PIXELS_X]) * 4      #*4 to improve image contrast for display
                    fillColour = "#%02x%02x%02x" % (colour,colour,colour)
                    #draw new pixel and add to pixel_array
                    self.new_pixel = self.canvas_for_Image.create_rectangle(row*self.grid_size,column*self.grid_size,(row+1)*self.grid_size,(column+1)*self.grid_size,fill= fillColour,width=0)
                    self.pixel_dictionary[row + column * ADNS3080_PIXELS_X] = self.new_pixel
                else:
                    break

    def updateDxDy(self):
        buf = [0 for i in range(4)]
        buf = spiRead(ADNS3080_MOTION_BURST,buf)
        motion = buf[0]
        if  (motion & 0x10):
            print("ADNS-3080 overflow")
        elif (motion & 0x80):
            dx = buf[1] if(buf[1]<0x80) else (buf[1]-0xFF)
            dy = buf[2] if(buf[2]<0x80) else (buf[2]-0xFF)
            surfaceQuality = buf[3]

            self.position_X += dx
            self.position_Y += dy

            print('x:{0},dx:{1}  y:{2},dy:{3}  surfaceQuality:{4}'.format(self.position_X,dx,self.position_Y,dy,surfaceQuality))
        self.plotData()
        time.sleep(0.01)
#end class GUI()


def spiSettings(bus,device,mode,max_speed):
    global spi, SPI_OPEN
    try:
        spi = spidev.SpiDev()                        #Open SPI device
        spi.open(bus,device)                         #spi.open(bus, device)
        spi.mode = mode
        spi.max_speed_hz = max_speed
        SPI_OPEN = True
    except:
        print("Could not open SPI")
#end def spiSettings()

def resetADNS3080():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RESET_PIN, GPIO.OUT)
    GPIO.output(RESET_PIN, GPIO.HIGH)
    time.sleep(10e-6)
    GPIO.output(RESET_PIN, GPIO.LOW)
    time.sleep(500e-6)
#end def resetADNS3080()

def checkConnect():
    resp = spiRead(ADNS3080_PRODUCT_ID,[0xff])
    product_ID = resp[0]
    if product_ID == ADNS3080_PRODUCT_ID_VALUE:
        print("ADNS-3080 found. Product ID: 0x" '%x' %product_ID)
    else:
        print("Could not found ADNS-3080 or too fast SPI speed: 0x" '%x' %product_ID)
#end def checkConnect()

def configuration():
    config = spiRead(ADNS3080_CONFIGURATION_BITS,[0xff])
    spiWrite(ADNS3080_CONFIGURATION_BITS,[config[0] | 0x10])  #Set resolution to 1600 counts per inch
    config = spiRead(ADNS3080_CONFIGURATION_BITS,[0xff])
    if (config[0] & 0x19):
        print("Resolution in counts per inch = 1600")
    else:
        print("Resolution in counts per inch = 400")
#end def configuration()

def spiRead(reg,data):                                        #"data" must be list
    length = len(data)
    to_send = [reg]
    to_send += data
    resp = spi.xfer(to_send)
    return resp[1:length+1]
#end def spiRead()

def spiWrite(reg,data):
    to_send = [reg | 0x80]
    to_send += data
    spi.writebytes(to_send)
#end def spiWrite()


## Settings ##
spiSettings(0,SS_PIN,SPI_MODE,SPI_MAX_SPEED)
resetADNS3080()
checkConnect()
configuration()

## main loop ##
root = Tk()

gui = GUI(root)

print("entering main loop!")

root.mainloop()

gui.endProgram()

spi.close()

GPIO.cleanup()
print("existing")
