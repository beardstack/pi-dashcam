 
#!/usr/bin/env python3
"""
This module provides a class to easy setup an LED instance for GPIO that
is capable to handle a real LED like switching on and off or to dim the light.
Each instance holds one pin and controls this pin.
The developer/user has to make sure, that there are no overlapping instances used...
In addition some basic functionality tests are provide as stand-alone script.
Classes:
    LED
Functions:
    main
    class_test
"""
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)
class LED:
    """
    Class to controll an LED via a GPIO PIN in GPIO.BOARD configuration.
    Each class instance controls exactly one pin.
    Make sure they are not overlapping!
    Methods:
        __init__(pin, freq, is_inverse)
        __del__()
        freq()
        set_freq(freq)
        duty_cycle()
        set_duty_cycle(duty_cycle)
        set_on()
        set_off()
    """
    def __init__(self, pin, freq=2000, is_inverse=False):
        """
        Constructor to create a single LED instance with one pin asociated.
        The frequency can be set and also an inverse_state.
        Keyword Arguments:
            pin -- the GPIO.BOARD pin
            freq -- the frequency for the LED (default: 2000)
            is_inverse -- boolean if the LED is inverted (connected to 3.3V instead of GND) (default: False)
        """
        self._pin = pin
        self._is_inverse = is_inverse
        GPIO.setup(self._pin, GPIO.OUT)
        GPIO.output(self._pin, GPIO.LOW)

        self._freq = freq
        self._duty_cycle = 0 if not self._is_inverse else 100
        self._pwm = GPIO.PWM(self._pin, self._freq)
        self._pwm.start(self._duty_cycle)
    def __del__(self):
        """
        Destructor to stop PWM activated on a pin and setup the output low.
        """
        self._pwm.stop()
        GPIO.output(self._pin, GPIO.LOW)
    def freq(self):
        """
        Function to get the current used frequency.
        Returns: freq
        """
        return self._freq
    def set_freq(self, freq):
        """
        Function to set the frequency for the LED.
        Keyword Arguments:
            freq -- the frequency to be set
        """
        self._freq = freq
        self._pwm.ChangeFrequency(freq)
    def duty_cycle(self):
        """
        Function to get the current used duty cycle (PWM; dimming).
        Is an integer 0 <= duty_cycle <= 100.
        Returns: duty_cycle
        """
        return self._duty_cycle
    def set_duty_cycle(self, duty_cycle):
        """
        Function to set the duty cycle (PWM; dimming) for the LED.
        Has to be an integer 0 <= duty_cycle <= 100.
        Keyword Arguments:
            duty_cycle -- the frequency to be set
        """
        dc = min(100,max(duty_cycle,0))
        self._duty_cycle = dc if not self._is_inverse else 100 - dc
        self._pwm.ChangeDutyCycle(self._duty_cycle)
    def set_on(self):
        """
        Function to switch an LED on and set the duty cycle to max.
        """
        self.set_duty_cycle(100)
        GPIO.output(self._pin, GPIO.HIGH)
    def set_off(self):
        """
        Function to switch an LED off and set the duty cycle to min.
        """
        self.set_duty_cycle(0)
        GPIO.output(self._pin, GPIO.LOW)
def class_test():
    """
    Class to provide basic functionality testing.
    Connect LED to pin 11,12 and GND.
    Run led.py locally. The LED should turn on, switch
    a bit and dim it self.
    For each LED on pin 11 and 12 individually
    """
    #Basic Testing
    pins = (11,12)
    for pin in pins:
        LED1 = LED(pin)
        #Basic Turn on and off
        LED1.set_on()
        time.sleep(1)
        LED1.set_off()
        time.sleep(1)

        # Use simple PWM and off
        LED1.set_duty_cycle(50)
        time.sleep(1)
        LED1.set_off()
        time.sleep(2)
        # Turn slowly down
        for dc in range(100,-1,-1):
            LED1.set_duty_cycle(dc)
            time.sleep(0.1)
        del LED1
    GPIO.cleanup()
if __name__ == "__main__":
    """
    A main function that is used, when this module is used as a stand-alone script.
    Local imports in order not to disturb library import functionality (keeping it clean!)
    """
    import time
    class_test()
