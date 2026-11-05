"""Shared content-time events (picture and sound) — v4, the full story with three RubUp breaks.
Line times come from the selected takes (timeline.py); word anchors are estimated from the takes (words.py)."""
from timeline import DUR, ON, END, KEY
from words import wt


def on(k):
    return ON[KEY[k]]


def end(k):
    return END[KEY[k]]


AD1 = end('lead1') + 0.15          # «…испытай удачу в РубАп» (Dima is about to be scammed)
AD2 = end('lead2') + 0.15          # «Свидание назначено… загляни в РубАп»
AD3 = end('lead3') + 0.15          # «Пока Петя гуляет на чужие подарки — испытай удачу в РубАп»
ADS = [AD1, AD2, AD3]

T = {}
# hook
T['hook_msg'] = 0.12
T['shock'] = end('hook_msg') - 0.25
T['rewind'] = wt('hook', 'Но') - 0.1
# Petya's room → the friend's chat
T['room'] = on('room') - 0.05
T['buzz'] = on('boss') - 0.05
T['fly1'] = on('boss') + 0.6
T['try_doubt'] = on('try') + 0.05
T['try_ok'] = wt('try', 'Ладно') - 0.1
# Dima (walks the corridor during «И почти сразу — удача» and the RubUp lead)
T['dima'] = on('dima') - 0.05
T['to_dima_chat'] = AD1 + 0.02
T['trust_sent'] = end('trust1') - 0.05
T['ask_sent'] = end('ask') - 0.05
T['dima_reply'] = on('dima_ok')
T['calendar'] = end('dima_ok') + 0.2
T['loser_sent'] = end('loser') - 0.1
T['threat'] = on('threat')
T['threat2'] = wt('threat', 'Верни')
T['threat3'] = wt('threat', 'найду')
T['block1'] = end('threat') + 0.12
T['dima_cry'] = end('threat') + 0.35
T['simple'] = end('threat') + 0.85
T['sleep'] = on('sleep') - 0.1
T['thought'] = end('sleep') + 0.05             # «Жизнь-то… не такая уж и плохая» as a thought
# months → Katya → the search → the dating site → the AI
T['tunnel'] = on('months') - 0.05
T['katya'] = wt('katya', 'Катя') - 0.15
T['search'] = end('katya') + 0.1
T['found'] = on('found') - 0.08
T['profile'] = on('profile_p') - 0.15
T['wishes'] = [wt('profile_p', 'Брюнет'), wt('profile_p', 'щетина'), wt('profile_p', 'дело')]
T['ai'] = on('alex') - 0.08
T['alex_name'] = wt('alex', 'биография')
T['chat_k'] = AD2 + 0.4                          # «ДЕНЬ X»: Petya writes to Katya
T['days'] = on('days')
T['date_msg'] = on('date')
T['katya_love'] = end('invite') + 0.1
T['lead2'] = end('date') + 0.15                   # Petya smirks: he is not going to go
# after RubUp 2: the cancelled date
T['cancel'] = end('knew') + 0.1
T['fly_cancel'] = on('cancel') + 1.0
T['cancel_sent'] = end('cancel') - 0.02
T['why_msg'] = on('why')
T['katya_worried'] = on('why') + 0.9
T['lie'] = end('why') + 0.12
T['lie_sent'] = end('lie') - 0.02
T['genius'] = end('lie') + 0.12
T['help'] = end('genius') + 0.05
T['help_msg'] = on('help')
T['gifts'] = [end('help') + 0.15, end('help') + 0.65, end('help') + 1.15]
T['all_msg'] = on('all')
T['katya_sad'] = on('all') + 0.9
T['smile'] = end('all') + 0.1
T['transfer'] = end('smile') + 0.02
T['transfer_done'] = T['transfer'] + 1.25
T['mock_draft'] = max(on('mock') - 0.05, T['transfer_done'] + 0.15)
T['mock_sent'] = end('mock') - 0.02
T['five'] = wt('wait', 'Пять')
T['ten'] = wt('wait', 'десять')
T['uneasy'] = on('uneasy') - 0.1
T['block2_shot'] = wt('uneasy', 'Совсем') - 0.15
T['block2'] = T['block2_shot'] + 0.5
# the party → RubUp 3 → the last message
T['party'] = AD3 + 0.02
T['party_all'] = wt('party', 'Всё')
T['buzz2'] = wt('incoming', 'пришло')
T['fly_final'] = end('incoming') - 0.25
T['final_msg'] = on('final') + 0.02
T['shock2'] = end('final') + 0.25
T['endcard'] = on('outro') + 1.1
T['end'] = DUR
