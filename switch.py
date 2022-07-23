#!/usr/bin/env python3
"""
This module provides classes that relate/beling to the physical class of switches.
It can be used to easily read state from switches and transform physical states
into computer and human readable values.
Each switch instance will represent exactly one physical switch, so that
a certain switch pin related to exact one Switch.
The developer/user has to make sure, that there are no overlapping instances used...
In addition some basic functionality tests are provide as stand-alone script.
Classes:
    Switch
Functions:
    main
    class_Switch_test
    class_Switch_functor
"""
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)
class Switch:
    """
    Class to handle input/states of physical switches in GPIO.BOARD configuration.
    Each class instance controls exactly one switch.
    Can be used for simple buttons aswell as binary tilt-switches or binary
    vibrations switches.
    Make sure pins are mutual exclusiv!
    Methods:
        __init__(pin, freq, is_inverse)
        bouncetime()
        set_bouncetime(bouncetime)
        functor()
        set_functor(functor)
        edge()
        set_edge(edge)
        _update_callback()
        _press_btn(*args)
        default_functor()
    """
    def map_edge(edge):
        """
        Translate users integer input to return corresponding
        GPIO edge detection states (GPIO.RISING, GPIO.FALLING, GPIO.BOTH).
        GPIO.RISING means callback connected to an voltage increase
        (e.g. pull-down-resistor with button pressed)

        Keyword Arguments:
            edge -- Integer to set/update the wished edge detection mode.
                    >0: RISING, ==0: BOTH, <0: FALLING
        """
        if edge > 0:
            return GPIO.RISING
        if edge < 0:
            return  GPIO.FALLING
        return GPIO.BOTH
    def __init__(self, pin, functor=None, bouncetime=10, edge_detector=0, pud=1):
        """
        Constructor to create connect to a single switch; bouncetime, edge detection,
        PUD and a functor (what should be called on switch interaction) can be set.
        Mandatory to set is the pin to read the signal/state from a button.
        Keyword Arguments:
            pin -- the GPIO.BOARD pin
            functor -- function pointer, what should be called on switch action; (default: None -> calls default functor)
            bouncetime -- switch sleepyness, in which periods signals are ignored (do not react on button flickering) (default: 10)
            edge_detector -- integer to indicate on which kind of signal change (edge) to be listened to (default: 0 -> GPIO.BOTH)
            pud -- Integer to indicate if it is pull-up or pull-down resistor (default: 1 -> GPIO.PUD_UP)
        """
        self._pin = pin
        self._functor = functor if functor is not None else Switch.default_functor
        self._bouncetime = bouncetime
        self._edge = Switch.map_edge(edge_detector)
        self._pud = GPIO.PUD_UP if pud >= 0 else GPIO.PUD_DOWN
        GPIO.setup(self._pin, GPIO.IN, pull_up_down=self._pud)
        self._update_callback()
    def pud(self):
        """
        Return the PUD (pull up or down) resistor state of switch.
        Cannot be set, only during creation of switch instance.

        Returns: GPIO.PUD_UP or GPIO.PUD_DOWN
        """
        return self._pud
    def bouncetime(self):
        """
        Return the currently used bouncetime; bouncetime indicates how fast a signal change (edge)
        should/can trigger the callback function.
        Returns: bouncetime -- integer
        """
        return self._bouncetime
    def set_bouncetime(self, bouncetime):
        """
        Override the currently used bouncetime; will trigger an update of the callback function
        by removing and adding (with new values) an event_detection to button signal pin.
        Bouncetime indicates how fast a signal change (edge) should/can trigger the callback function.
        Keyword Arguments:
            bouncetime -- switch sleepyness, after which time periods signals are recognised.
        """
        self._bouncetime = bouncetime
        self._update_callback()
    def functor(self):
        """
        Returns the currently used functor that is used within callback triggering of the switch.
        No real usage except comporing somewhere maybe ...
        Returns: functor -- function pointer
        """
        return self._functor
    def set_functor(self, functor):
        """
        Set the functor, function pointer that is used during the callback triggering; the input
        for the functor is the current state of the button when pressed/released (typical: 0,1).
        Allows the overriding for general purpose usage.
        Keyword Arguments:
            functor -- function pointer
        """
        self._functor = functor
    def edge(self):
        """
        Returns the currently used edge detection for the switch.
        Indicates if it is configured to listen on GPIO.RISING, -.FALLING or -.BOTH.
        Returns: GPIO.BOTH, GPIO.FALLING or GPIO.RISING
        """
        return self._edge
    def set_edge(self, edge_detector):
        """
        Allows overwriting of the edge detectiong during the callback triggering.
        Based on the PUD resitor type, we can listen to a falling, rising or both
        voltage changes.
        Input is an integer, that is mapped accordingly to the three states
        RISING, BOTH, FALLING (>0, ==0 , <0).
        Keyword Arguments:
            edge_detector  -- integer, where the sign indicates for the edge_detection
                                (RISING, BOTH, FALLING)
        """
        self._edge = Switch.map_edge(edge_detector)
        self._update_callback()
    def _update_callback(self):
        """
        Internal function that is used to update the callback by removing and adding
        the event_detection with adjusted values.
        Is used in order to included changes on edge or bouncetime.
        """
        GPIO.remove_event_detect(self._pin)
        GPIO.add_event_detect(self._pin, self._edge, callback=self._press_btn, bouncetime=self._bouncetime)
    def _press_btn(self, *args):
        """
        Internal callback function that is used when a switch is triggered;
        generically makes use of the given functor (default or adjusted by needs);
        the current button/pin state is provided to the functor.
        Keyword Arguments:
            args -- generic arguments from the callback, currently not used.
        """
        self._functor(GPIO.input(self._pin))

    def default_functor(input):
        """
        Static method, default functor that is used if not specified otherwise in
        constructor.
        Gets an input (button state) and prints based on the current state some
        information (button pressed or not).
        Keyword Arguments:
            input -- integer, 0,1 and the current button state if pressed/released
        """
        if input == 0:
            print("Switch pressed")
        elif input == 1:
            print("Switch released")
        else:
            print("WARNING! UNKNOWN Switch STATE")
def class_switch_functor(input):
    """
    Example switch functor that mutual exclusively turns
    two LEDs on and off according to button pressing.
    LED1+2 are set globally in main function in order to not
    disturb the class functionality.
    Keyword Arguments:
        input -- integer, 0,1 and the current button state if pressed/released
    """
    if input == 0:
        LED1.set_on()
        LED2.set_off()
    elif input == 1:
        LED1.set_off()
        LED2.set_on()
    else:
        LED1.set_off()
        LED2.set_off()
def class_switch_test():
    """
    Example function to test the basic functionality of the switch class.
    Makes use of in main globally setup LED1+2 instances. Is only called whe
    library is called as it's own script (not imported).
    Will call the default switch functor and a functor turning off and on
    LEDs in pin 12 and 13.
    """
    BTN1 = Switch(11)
    print("Please press Switch (default test) ... 10s")
    time.sleep(10)
    print("Done!")
    print("Now again please press Switch (functor test) ... 10s")
    BTN1.set_functor(class_switch_functor)
    time.sleep(10)
    print("Done!")
    GPIO.cleanup()
if __name__ == "__main__":
    """
    A main function that is used, when this module is used as a stand-alone script.
    Local imports in order not to disturb library import functionality (keeping it clean!)
    """
    import time
    from led import LED
    LED1 = LED(12)
    LED2 = LED(13)
    class_switch_test()
