"""Общие события картинки и звука (время содержания, без рекламы)."""
from timeline import DUR, AT, END_OF
from script import TIMER

SLIDE = 0.4                                   # Планктон с моделью уезжает вниз / возвращается
AD_STOP = END_OF['N6'] + 0.5                  # раунд 3: вопрос прозвучал, Планктон уехал — RubUp (после 50 % ролика: превью без баннера)
RETURN = (AD_STOP, AD_STOP + SLIDE)
TRANSITIONS = [AT['TR1'], AT['TR2'], AT['TR3']]      # середина пузырей закрывает кадр
ROUNDS = [  # (вопрос, начало таймера, ответ)
    (AT['N2'], END_OF['N2'], AT['N3']),
    (AT['N4'], END_OF['N4'], AT['N5']),
    (AT['N6'], None, AT['N7']),
]
PLANKTON_PICK = [AT['P2'], AT['P4'], AT['P6']]
FAIL = [AT['P3'], AT['P5'], AT['P7']]       # реплика Планктона после каждой неудачи
FINAL = AT['P7']
KAREN = (AT['P4'] - 0.6, AT['P4'] + 3.9)      # Карен в кепке Дурова едет слева направо на заднем плане
