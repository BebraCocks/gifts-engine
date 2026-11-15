"""Shared content-time events. Add word anchors here for picture and sound together."""
from timeline import DUR, ON, END
from words import wt

# Place an ad in the pause nearest the middle, with room for deceleration.
gaps = [(abs((END[k] + ON[k+1])/2 - DUR/2), k) for k in range(len(ON)-1)]
if not gaps:
    raise ValueError('Use at least two lines and plan a speech pause for RubUp')
k = min(gaps)[1]
AD_STOP = (END[k] + ON[k+1]) / 2
