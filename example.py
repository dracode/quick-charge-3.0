import qc30
from machine import Pin
import time

# define the GPIO pins that control our voltage dividers that signal on the USB D+ and D- lines
dplus = Pin(12)
dminus_gnd = Pin(14)
dminus_3v3 = Pin(16)

# initialize the module
power = qc30.QC30(dplus, dminus_gnd, dminus_3v3)

# command the power supply to output 9 Volts (a QC 2.0 mode)
power.set_9v()
# we could have done this all at once, too:
# power = qc30.QC30(dplus, dminus_gnd, dminus_3v3, voltage=9)

# these "sleep"s are just for demo purposes so you can see the power supply output each target voltage.  the module handles all required timing.
time.sleep(5)

# command the power supply to output 6.2 Volts
power.set(6.2)

time.sleep(3)

# command the power supply to increment the output voltage by 0.2 Volts
power.inc()

time.sleep(2)

# now decrement it back to where we started
power.dec()


