"""Select the predeclared matched pairs from frozen10k output, no searches."""
import json
from pathlib import Path
from surprise.position import Position
from surprise.research import write_json

HERE=Path(__file__).resolve().parent
data=json.loads((HERE/'evidence.json').read_text())
positions=[]
root=Position.from_sfen(data['root_sfen'])
for b in data['branches']:
    c=next(c for c in b['candidates'] if c['move']==b['our_response'])
    child=root.apply_move(b['opponent_move']).apply_move(c['move'])
    displayed=[next(r for r in c['responses'] if r['move']==m) for m in c['displayed_replies']]
    best=next((r for r in displayed if r['gap']==0),None)
    wrong=next((r for r in displayed if r['gap'] and r['gap']>=300),None)
    for role,r in [('best10k',best),('highest_salience_error10k',wrong)]:
        if r:
            positions.append({'branch':b['opponent_move'],'candidate':c['move'],'reply':r['move'],'role':role,
                              'sfen':child.apply_move(r['move']).sfen,'value10k':r['result']['score']})
write_json(HERE/'confirmation_plan.json',{'scope':'Predeclared8 positions maximum; matched100k pairs, not full100k best-defense rankings','positions':positions})
print([(r['branch'],r['reply']) for r in positions])
