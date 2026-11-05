"""Shared content-time events for picture and sound (seconds). Word anchors come from Fish Audio ASR."""
from timeline import DUR, ON, END, KEY
from words import wt

L = KEY                                           # screen key -> line index

# RubUp: in the speech pause after the narrator's «…испытай удачу в РубАп», during the freeze frame.
AD_STOP = (END[L['ad']] + ON[L['misha']]) / 2

HOOK_CUT = wt('hook', 'ради') - 0.12              # face -> thumb over the button
CANTEEN = END[L['hook']] + 0.12
COINS = [wt('saving', 'копил'), wt('saving', 'крафт'), wt('saving', 'худел'), wt('saving', 'бледнел')]
FULL = wt('saving', 'накопил')                    # piggy bank full
VAULT = END[L['saving']] + 0.08                   # 3D scene 1 starts
VAULT_END = ON[L['first']] - 0.1
LEGEND_WORD = wt('vault3d', 'легендарных')

FIRST = VAULT_END                                 # hallway, «Наконец-то!»
PHONE1 = END[L['first']] + 0.12
SLOT_T = [PHONE1 + 0.12 + 0.22 * k for k in range(4)]
CHANCE0, CHANCE1 = SLOT_T[0] + 0.1, SLOT_T[3] + 0.55          # the chance climbs as slots fill: 89%
THUMB_IN = wt('press', 'ну') - 0.1
PRESS = wt('press', 'богом', end=True) + 0.08
VORTEX0, VORTEX1 = PRESS + 0.08, PRESS + 0.7
BURN0 = VORTEX1
ASH0 = BURN0 + 0.55
FAIL = BURN0 + 0.7
FACE = ON[L['burned']] - 0.05                     # close-up: the smile slides off
SMILE_GONE = wt('burned', 'названия')
REALISE = wt('burned', 'намекали')
RAGE = END[L['burned']] + 0.1
SCREAM = wt('rage', 'охуели')
THROW = SCREAM + 0.55
IMPACT = THROW + 0.32
FREEZE = ON[L['ad']] - 0.06                       # «Стоп-кадр»
FREEZE_AT = IMPACT + 0.12                         # the frozen moment
RESUME = AD_STOP + 0.02                           # after RubUp: Михаил walks in
MISHA_IN = RESUME + 0.02
TELLS = ON[L['tells']]
TRY = ON[L['try']]
THINK = wt('try', 'о')
PHONE_OUT = wt('try', 'один')
PHONE2 = END[L['try']] + 0.12
SLOT2 = PHONE2 + 0.1
CH2_0, CH2_1 = wt('one', 'двадцать') - 0.1, wt('one', 'процента', end=True)
PRESS2 = wt('one', 'жму', end=True) + 0.02
FLASH2 = PRESS2 + 0.22
LEGEND = FLASH2 + 0.06                            # 3D scene 2
LEGEND_END = ON[L['ugly']] + 0.45                  # J-cut: «Фу» starts over the 3D shot
UGLY = LEGEND_END
OFFER = wt('ugly', 'о')
HUNDRED = wt('ugly', 'сто')
ACCEPT = END[L['ugly']] + 0.12
PIZZA = ON[L['pizza']] - 0.05
LEAVE = wt('pizza', 'удачно') - 0.2
SHOCK = END[L['pizza']] + 0.12
WTF = ON[L['wtf']]
MORAL = ON[L['moral']] - 0.15
CTA = ON[L['cta']] - 0.12
LIKE = wt('cta', 'лайк')
