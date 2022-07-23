# pi-dashcam

This application follows the idea to setup an OpenSource dashcam
that can be run on a low-cost hardware like the Raspberry PI Zero.
Main purpose is to have a trustfull software following the requirements
of GDPR rules in Germany (DSGVO) to store data only temporary and save
video chunks only in cases of accidents/emergencies.

Requirements:
    - 32-Bit Raspberry Pi OS (necessary to run picamera v1!)
    - min. 1 CPU
    - min. 128MB RAM
    - Pi Camera attached
    - legacy camera support enabled in raspi-config

A single core and 512MB of RAM is plenty enough to have a 1080p 
dashcam running.
For a nicer interaction, this application allows the usage of a button
to trigger a copy of all legal files at the moment (by default, the last
10 minutes) to a separate folder on the disk, to be available later.
In addition, two LEDs can be controlled; one is a Power-LED, that indicates
a running system (by default a slow heartbeat pulsar) next to a Data-Copy-LED,
that lights up when current legal video chunks are stored separately and blinks
for 2 seconds when that process is done.

More parameter can be set (e.g. resolution, chunk size and count), but the
default values should optimal for the most cases (1080p, 10 video chunks of 60s).

For any question, do not hesitate to contact me.

Best regards,
Lars




___________________________
Default PIN scheme:

GND <--> button <--> Board Pin 11 (GPIO 17)

GND <--> 220R <--> LED Data Copy <--> Board Pin 12 (GPIO 18)

GND <--> 220R <--> LED Power <--> Board Pin 13 (GPIO 27)