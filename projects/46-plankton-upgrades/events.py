"""Общие события картинки и звука (время содержания, без рекламы)."""
from timeline import DUR, AT, END_OF
from script import TIMER

SLIDE = 0.4                                   # Планктон с моделью уезжает вниз / возвращается
AD_STOP = END_OF['N4'] + 0.5                  # раунд 2: вопрос прозвучал, Планктон уехал — RubUp
RETURN = (AD_STOP, AD_STOP + SLIDE)
TRANSITIONS = [AT['TR1'], AT['TR2'], AT['TR3']]      # середина пузырей закрывает кадр
ROUNDS = [  # (вопрос, начало таймера, ответ)
    (AT['N2'], END_OF['N2'], AT['N3']),
    (AT['N4'], None, AT['N5']),
    (AT['N6'], END_OF['N6'], AT['N7']),
]
PLANKTON_PICK = [AT['P2'], AT['P4'], AT['P6']]
FAIL = [AT['P3'], AT['SQ'], AT['P7']]
FINAL = AT['P7']
