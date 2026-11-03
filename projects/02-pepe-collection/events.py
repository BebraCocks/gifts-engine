"""Shared content-time events. One map for picture and sound."""
from timeline import DUR, ON, END

# RubUp: after line 5 («…прячется под землёй…»), the open question before the Turtles reveal.
AD_LINE = 4
AD_STOP = (END[AD_LINE] + ON[AD_LINE + 1]) / 2
