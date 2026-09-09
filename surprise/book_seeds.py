"""Inspect an explicitly supplied YaneuraOu text-book; bounded book-edge BFS."""
import argparse
from collections import Counter, deque
import hashlib
import io
import json
from pathlib import Path
import statistics
from zipfile import ZipFile

import shogi

from .research import identity, write_json


def parse_book(lines):
    book={};key=None;records=0;conflicts=0
    for raw in lines:
        line=raw.strip()
        if not line or line.startswith(('#','//')):continue
        if line.startswith('sfen '):
            sfen=line[5:];key=' '.join(sfen.split()[:3]);records+=1
            book.setdefault(key,{'sfen':sfen,'moves':{},'recorded_move_numbers':[]})['recorded_move_numbers'].append(int(sfen.split()[3]))
        else:
            move,ponder,value,depth,count=line.split()[:5]
            entry={'move':move,'ponder':ponder,'value_side_to_move':int(value),'book_depth':int(depth),'book_count':int(count)}
            old=book[key]['moves'].get(move)
            if old and old!=entry:conflicts+=1
            # Preserve source conflicts explicitly; do not treat repeated records as frequency.
            if old is None:book[key]['moves'][move]=entry
    return book,{'source_position_records':records,'source_distinct_positions':len(book),'conflicting_move_records':conflicts}


def bounded_positions(book,max_ply):
    start=shogi.Board().sfen();key=' '.join(start.split()[:3])
    if key not in book:raise ValueError('book does not include initial position')
    queue=deque([(key,0,[])]);seen={key};rows=[];invalid=[];terminal_edges=0
    while queue:
        key,ply,history=queue.popleft();entry=book[key];b=shogi.Board(key+' '+str(ply+1))
        moves=list(entry['moves'].values())
        raw_best=max((m['value_side_to_move'] for m in moves),default=None)
        score=raw_best*(1 if b.turn==0 else -1) if raw_best is not None else None
        r={'position_id':identity(b.sfen()),'sfen':b.sfen(),'side_to_move':'sente' if b.turn==0 else 'gote',
            'ply':ply,'move_history':history,'source':'BOOK-700T-Shock',
            'book_branch_count':len(moves),'book_moves':moves,'recorded_move_numbers':entry['recorded_move_numbers'],
            'parent_book_eval_sente':score,'parent_engine_eval_sente':None,
            'book_score_numeric':score is not None and abs(score)<30000,
            'frequency_semantics':'book structure only; not human frequency'}
        rows.append(r)
        if ply==max_ply:continue
        for m in moves:
            try:move=shogi.Move.from_usi(m['move'])
            except ValueError:invalid.append([r['position_id'],m['move']]);continue
            if not b.is_legal(move):invalid.append([r['position_id'],m['move']]);continue
            b.push(move);child=' '.join(b.sfen().split()[:3]);b.pop()
            if child not in book:terminal_edges+=1;continue
            if child not in seen:
                seen.add(child);queue.append((child,ply+1,history+[m['move']]))
    return rows,{'invalid_edges':invalid,'edges_to_unstored_positions':terminal_edges}


def describe(values):
    v=sorted(values)
    return {'n':len(v),'min':min(v) if v else None,'median':statistics.median(v) if v else None,
        'p90':v[min(len(v)-1,int(.9*len(v)))] if v else None,'max':max(v) if v else None}


def run(archive,out,max_ply):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with ZipFile(archive) as z:
        with z.open('user_book1.db') as file:
            book,source=parse_book(io.TextIOWrapper(file,encoding='utf-8-sig'))
        notice=next(z.read(n).decode('utf-8-sig') for n in z.namelist() if n.endswith('.txt'))
    rows,diagnostic=bounded_positions(book,max_ply)
    summary={}
    for limit in (12,16,20):
        if limit>max_ply:continue
        group=[r for r in rows if r['ply']<=limit]
        summary[str(limit)]={'distinct_positions':len(group),'positions_by_min_ply':dict(sorted(Counter(r['ply'] for r in group).items())),
            'branching':describe([r['book_branch_count'] for r in group]),
            'branching_histogram':dict(sorted(Counter(r['book_branch_count'] for r in group).items())),
            'parent_book_eval_sente':describe([r['parent_book_eval_sente'] for r in group if r['book_score_numeric']]),
            'abs_book_eval_ge300':sum(abs(r['parent_book_eval_sente'])>=300 for r in group if r['book_score_numeric']),
            'parent_already_favorable_book_proxy':sum(r['parent_book_eval_sente']*(1 if r['side_to_move']=='sente' else -1)>=300 for r in group if r['book_score_numeric']),
            'engine_eval_available':0}
    manifest={'archive':str(archive),'archive_sha256':hashlib.sha256(Path(archive).read_bytes()).hexdigest(),
        'source_url':'https://github.com/yaneurao/YaneuraOu/releases/tag/BOOK-700T-Shock',
        'license_status':'no explicit redistribution license found in release or accompanying notice; local inspection only',
        'max_bfs_ply':max_ply,'symmetry_expansion':False,'source':source,**diagnostic}
    write_json(out/'manifest.json',manifest);write_json(out/'summary.json',summary)
    write_json(out/'positions.json',rows)
    write_json(out/'source_notice.json',{'notice':notice})
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--archive',default='assets/books/700T/700T-shock-book.zip')
    p.add_argument('--output',default='reports/terashock_seed_audit');p.add_argument('--max-ply',type=int,default=20)
    a=p.parse_args()
    if not 0<=a.max_ply<=20:raise ValueError('this audit is limited to 20 ply')
    run(a.archive,a.output,a.max_ply)
