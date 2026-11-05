"""Shared content-time events (picture and sound). Line times come from the selected takes (timeline.py),
word anchors are estimated from the takes (words.py, no ASR timestamps without an API key)."""
from timeline import DUR, ON, END, KEY
from words import wt


def on(k):
    return ON[KEY[k]]


def end(k):
    return END[KEY[k]]


AD1 = end('sleep') + 0.15          # «…испытай удачу в РубАп» → RubUp 1 (≈33 s of output)
AD2 = end('smile') + 0.15          # «…загляни в РубАп» → RubUp 2 (≈88 s of output)

T = {}
T['hook_msg'] = 0.12
T['shock'] = end('hook_msg') - 0.25
T['rewind'] = wt('hook', 'Но') - 0.1
T['room'] = end('hook') + 0.1
T['buzz'] = on('boss') - 0.05
T['fly1'] = on('boss') + 0.6
T['dima'] = end('boss') + 1.2
T['to_dima_chat'] = on('ask') + 0.9
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
T['tunnel'] = AD1
T['katya'] = wt('katya', 'Катя') - 0.15
T['search'] = end('katya') + 0.05
T['found'] = on('found') - 0.08
T['profile'] = on('profile') - 0.1
T['ai'] = wt('profile', 'Будет') - 0.15
T['alex_name'] = T['ai'] + 0.75
T['chat_k'] = on('wow') - 0.55
T['date_msg'] = on('date')
T['katya_love'] = end('date') - 1.5
T['cancel'] = end('date') + 0.15
T['fly_cancel'] = on('cancel') + 1.0
T['cancel_sent'] = end('cancel') - 0.02
T['why_msg'] = on('why')
T['katya_worried'] = on('why') + 0.9
T['lie'] = end('why') + 0.12
T['lie_sent'] = end('lie') - 0.02
T['genius'] = end('lie') + 0.12
T['help'] = end('genius') + 0.05
T['help_msg'] = on('help')
T['gifts'] = [end('help') + 0.1, end('help') + 0.45, end('help') + 0.8]
T['all_msg'] = on('all')
T['katya_sad'] = on('all') + 0.9
T['smile'] = end('all') + 0.1
T['transfer'] = AD2 + 0.02
T['transfer_done'] = AD2 + 1.3
T['mock_draft'] = AD2 + 1.45
T['mock_sent'] = end('mock') - 0.02
T['five'] = end('silent') + 0.05
T['ten'] = end('silent') + 0.45
T['uneasy'] = on('uneasy') - 0.1
T['block2_shot'] = wt('uneasy', 'плевать') - 0.25
T['block2'] = T['block2_shot'] + 0.45
T['party'] = on('party') - 0.1
T['buzz2'] = end('party') + 0.1
T['fly_final'] = on('final') - 0.1
T['final_msg'] = on('final') + 0.02
T['shock2'] = end('final') + 0.25
T['endcard'] = on('outro') + 1.1
T['end'] = DUR
T['wishes'] = [wt('profile', 'Брюнет'), wt('profile', 'щетина'), wt('profile', 'дело')]
T['party_all'] = wt('party', 'Всё')
