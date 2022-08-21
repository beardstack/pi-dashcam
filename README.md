# pi-dashcam

This application follows the idea to setup an OpenSource dashcam
that can be run on a low-cost hardware like the Raspberry PI 3 A+
(but also as in my intial approach with a PI Zero).
Main purpose is to have a trustfull software following the requirements
of GDPR rules in Germany (DSGVO) to store data only temporary and save
video chunks only in cases of accidents/emergencies. Data can be stored
either on RPi SD Card or external USB device (automounted).
Triggering of video data storing can also be done via acceleration sensor.

This project comes with a custom camera and rpi case:
- there is a camera case for the RPi Camera V2 (e.g. NoIR edition)
- there is a RPi 3A+ fitting base, where an RTC-DS3231 can be inserted into
- there is a top covering case, where a breadboard plate of 5x7cm can be easily inserted
    (watch for the LED and Button cutouts!)

I created my own HAT for the Pi-3A+; pictures will follow...

## Requirements
- 32-Bit Raspberry Pi OS (necessary to run picamera v1!)
- min. 1 CPU
- min. 128MB RAM
- Pi Camera attached
- legacy camera support enabled in raspi-config
- RealTime-Clock RTC DS3231 (e.g.: https://www.amazon.de/dp/B077XN4LL4/ref=pe_27091401_487024491_TE_item )
- ADXL345 acceleration sensor (e.g.: https://www.amazon.de/dp/B09T376QXX/ref=pe_27091401_487027711_TE_SCE_dp_1 )
- 4 Buttons and one RGB-LED (e.g.: on amazon, the 12mm x 12mm x 7mm tactile push botton with 5 colours ...)
- 3D printed cases for camera and rpi from 3dprints subfolder
    (and obviously a 3dprinter or you know somebody ;) )
- Some Dashcam carrier for your car (e.g.: https://www.amazon.de/dp/B091BVDT56/ref=pe_27091401_487024491_TE_item )

A single core and 512MB of RAM is sufficient enough to have a 1080p 
dashcam running. However, I decided to stick to the Pi 3A+ in order to be
more powerfull for future approaches.
For a nicer interaction, this application allows the usage of buttons
to e.g. trigger a copy of all legal files at the moment (by default, the last
10 minutes) to a separate folder on the disk (or external, auto-mounted device),
to be available later.
In addition, three LEDs (or an RGB-LED) can be controlled; one is a Power-LED,
that indicates a running system (by default a slow heartbeat pulsar, can be adjusted via Button)
next to a Data-Copy-LED, that lights up when current legal video chunks are stored separately
and blinks for some seconds when that process is done, and finally an info LED
that e.g. shows, no external device mounted or the video capturing process stopped.

More parameter can be set (e.g. resolution, chunk size and count), but the
default values should optimal for the most cases (1080p, 10 video chunks of 60s).


Real-World approach is then to solder all com


For any question, do not hesitate to contact me.

Best regards,
Lars




___________________________
Default PIN scheme:

GND <--> Button Power            <--> Board Pin 11 (GPIO 17)

GND <--> Button Copy             <--> Board Pin 12 (GPIO 18)

GND <--> Button Stop             <--> Board Pin 13 (GPIO 27)

GND <--> Button Info control     <--> Board Pin 15 (GPIO 22)


GND <--> 220R <--> LED Data Copy <--> Board Pin 29 (GPIO 27)

GND <--> 220R <--> LED Power     <--> Board Pin 33 (GPIO 13)

GND <--> 220R <--> LED Power     <--> Board Pin 37 (GPIO 26)


ADXL345 VCC/3V3 <--> Board Pin 1 (3V3)

ADXL345 GND     <--> Board Pin 9 (GND)

ADXL345 CS      <--> Board Pin 24 (GPIO 8 / SPIO CE0)

ADXL345 SD0     <--> Board Pin 21 (GPIO 9 / SPIO MISO)

ADXL345 SDA     <--> Board Pin 19 (GPIO 10 / SPIO MOSI)

ADXL345 SCL     <--> Board Pin 23 (GPIO 11 / SPIO SCLK)
