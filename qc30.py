# Author: dracode
# Last revised: 2017-08-08

# This code is public domain.  Do whatever you like with it.

# This code was tested and worked with a Tronsmart Presto 10400mAh power bank.

# This is probably over-engineered, but I wanted to implement as many features as possible for the sake of demonstration.
# If this is too verbose to fit within your memory constraints, a more minimal version could be written by reducing this to just the handshake, switch to continuous mode, and increment/decrement pulses. 

from machine import Pin
import time


# since most devices apparently do NOT support the theoretical max of 20V, we'll default to a max voltage of 12V.  This can be overridden in the constructor if needed.  Doing this reduces the chances of the voltage tracked in this class from getting out of sync with reality.
DEFAULT_MAX_VOLTAGE = 12
DEFAULT_MIN_VOLTAGE = 3.6

# Minimum time in usec to remain in handshake mode
HANDSHAKE_TIMER = 1500000

# These two timers were derived through guessing and trying it out.  Someone with better documentation might be able to provide more suitable values.

# How long we should wait after switching voltage modes to let things settle
MODE_TIMER = 100000 # usec

# This is for how long we should pulse the voltage in Continuous mode.
CONT_TIMER = 200 # usec

# QC3.0 allows voltage settings in "discrete" modes with prespecified values, or "continuous" mode with any value you want in 0.2V increments
CONTINUOUS = 0
DISCRETE = 1

class QC30(object):

    def __init__(self, pin_dplus, pin_dminus_gnd, pin_dminus_3v3, voltage=None, minvoltage=None, maxvoltage=None):
        self.mode = DISCRETE
        self.voltage = 5
        self.event_complete_time = 0
        self.min_voltage = DEFAULT_MIN_VOLTAGE
        self.max_voltage = DEFAULT_MAX_VOLTAGE
        
        if(not minvoltage is None):
            self.min_voltage = minvoltage
        if(not maxvoltage is None):
            self.max_voltage = maxvoltage


        # For the GPIO pins that drive the voltage dividers -- Hopefully the user passes a Pin object, but if they pass the GPIO number instead we can create the Pin

        # USB's green wire: D+
        # This pin is wired with resistors in such a way as to produce 3 states: 3.3V, 0.6V, and GND
        self.pin_dplus = pin_dplus
        if(not type(pin_dplus) is Pin):
            self.pin_dplus = Pin(pin_dplus)

        # USB's white wire: D-
        # These pins are wired to be able to produce 4 states: 3.3V, 0.6V, GND, and Disconnected
        # The Disconnected state is required during the QC2.0 handshake
        self.pin_dminus_gnd = pin_dminus_gnd # This pin connects D- to GND through a 1k resistor
        self.pin_dminus_3v3 = pin_dminus_3v3 # This pin connects D+ to 3v3 through a 4k7 resistor
        if(not type(pin_dminus_gnd) is Pin):
            self.pin_dminus_gnd = Pin(pin_dminus_gnd)
        if(not type(pin_dminus_3v3) is Pin):
            self.pin_dminus_3v3 = Pin(pin_dminus_3v3)

        self.handshake()
        if(not voltage is None and voltage != self.voltage):
            self.set(voltage)

    # Some operations take time to complete.  Rather than block with a sleep call, we will set a timer after each of these operations, then check it before we proceed to a new operation.  That way, we prevent unnecessary sleeps if your code is doing other things between function calls already.
    def __event_timer_wait(self):
        # Busy loop until the timer has expired
        while(time.ticks_diff(self.event_complete_time, time.ticks_us()) > 0):
            pass

    def __event_timer_set(self, time_us):
        self.event_complete_time = time.ticks_add(time.ticks_us(), time_us)

    # Methods to put our two wires into the required states to communicate to the power source
    def __dplus_gnd(self):
        self.pin_dplus.init(Pin.OUT, value=0)

    def __dplus_3v3(self):
        self.pin_dplus.init(Pin.OUT, value=1)

    def __dplus_0v6(self):
        self.pin_dplus.init(Pin.IN)


    def __dminus_gnd(self):
        self.pin_dminus_3v3.init(Pin.IN)
        self.pin_dminus_gnd.init(Pin.OUT, value=0)

    def __dminus_3v3(self):
        self.pin_dminus_gnd.init(Pin.IN)
        self.pin_dminus_3v3.init(Pin.OUT, value=1)

    def __dminus_0v6(self):
        self.pin_dminus_gnd.init(Pin.OUT, value=0)
        self.pin_dminus_3v3.init(Pin.OUT, value=1)

    def __dminus_disc(self):
        self.pin_dminus_gnd.init(Pin.IN)
        self.pin_dminus_3v3.init(Pin.IN)

    # This handshake lets the power source know that the recipient device is Quick Charge compatible and can request other voltages.  Without this handshake first, the power source will ignore all your other signalling.
    def handshake(self):
        self.mode = DISCRETE
        self.voltage = 5
        self.__dminus_disc()
        self.__dplus_0v6()
        self.__event_timer_set(HANDSHAKE_TIMER)


    # We put the supply into Continuous Mode after setting it to any discrete value, because it's safer.  If you leave the supply in discrete mode and the MCU reboots/fails/whatever, the pins could end up in an undefined state, meaning you could accidentally enter a mode you didn't intend!
    def set_9v(self):
        if(self.mode != DISCRETE):
            self.__set_5v()
        self.__event_timer_wait()
        self.voltage=9
        self.__dminus_0v6()
        self.__dplus_3v3()
        self.__event_timer_set(MODE_TIMER)
        self.set_cont()

    def set_12v(self):
        if(self.mode != DISCRETE):
            self.__set_5v()
        self.__event_timer_wait()
        self.voltage=12
        self.__dminus_0v6()
        self.__dplus_0v6()
        self.__event_timer_set(MODE_TIMER)
        self.set_cont()

    # If your power supply does not support 20V mode, this call will do nothing and voltage will remain whatever it was previously.  There is no way for this package to sense compliance.  That's on you.
    def set_20v(self):
        if(self.mode != DISCRETE):
            self.__set_5v()
        self.__event_timer_wait()
        self.voltage=20
        self.__dminus_3v3()
        self.__dplus_3v3()
        self.__event_timer_set(MODE_TIMER)
        self.set_cont()

    # Per page 10 of the NCP4371 datasheet, this is the only valid discrete mode allowable to switch to directly from continuous mode
    def __set_5v(self):
        self.__event_timer_wait()
        self.mode=DISCRETE
        self.voltage=5
        self.__dplus_0v6()
        self.__dminus_gnd()
        self.__event_timer_set(MODE_TIMER)

    def set_5v(self):
        self.__set_5v()
        self.set_cont()

    # switch to Continuous Mode, where voltage is adjustable in 0.2V increments
    def set_cont(self):
        self.__event_timer_wait()
        self.mode=CONTINUOUS
        self.__dplus_0v6()
        self.__dminus_3v3()
        self.__event_timer_set(MODE_TIMER)

    # Increment current voltage by 0.2V
    def inc(self):
        self.voltage = min(self.voltage + 0.2, self.max_voltage)
        if(self.mode != CONTINUOUS):
            self.set_cont()
        self.__event_timer_wait()
        # Briefly pulse D+ high to signal an increment
        self.__dplus_3v3()
        time.sleep_us(CONT_TIMER)
        self.__dplus_0v6()
        self.__event_timer_set(CONT_TIMER)

    # Decrement current voltage by 0.2V
    def dec(self):
        self.voltage = max(self.voltage - 0.2, self.min_voltage)
        if(self.mode != CONTINUOUS):
            self.set_cont()
        self.__event_timer_wait()
        # Briefly pulse D- low to signal a decrement
        self.__dminus_gnd()
        time.sleep_us(CONT_TIMER)
        self.__dminus_3v3()
        self.__event_timer_set(CONT_TIMER)

    # This is just computed based on the commands given previously, not measured from the line.  That means that it's possible for this to get out of sync with reality.  For example: if your power supply does not support voltages over 12V, but you increment to 12.2V then decrement 0.2V, this will report 12V, but in actuality the power supply will be outputting 11.8V.
    def get(self):
        return self.voltage

    # Set an arbitrary voltage
    def set(self, voltage):
        if(voltage < self.min_voltage):
            voltage = self.min_voltage
        if(voltage > self.max_voltage):
            voltage = self.max_voltage

        # Dealing with ints simplifies things a bit
        v_int = int(voltage * 10 + 0.5)

        # If our target voltage is a preset discrete value, we'll use those
        if(v_int == 200):
            self.set_20v()
            return
        elif(v_int == 120):
            self.set_12v()
            return
        elif(v_int == 90):
            self.set_9v()
            return
        elif(v_int == 50):
            self.set_5v()
            return

        v_current = int(self.voltage * 10 + 0.5)
        steps = int(abs(v_int - v_current) / 2)
        # print('target voltage %d, which is %d steps from current voltage %d' % (v_int, steps, v_current))
        if(v_int < v_current):
            for x in range(steps):
                self.dec()
        else:
            for x in range(steps):
                self.inc()
    

