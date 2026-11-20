"""Resolve identical group abbreviations only from a complete, consistent matrix."""
import re
from ttscore import Document, clean
from import_csv import DataError


def classes(node):return node.attrs.get('class','').split()


def score_matrices(body):
    matrices={};conflicts=set()
    for table in Document(body).find('table'):
        if 'groupTable' not in classes(table):continue
        groups={m[1] for node in [*table.find('button'),*table.find('a')]
                if (m:=re.search(r"loadSchedule\('(\d+)'",node.attrs.get('onclick','')))}
        columns=[node.attrs['data-playerid'] for node in table.find('th') if 'data-playerid' in node.attrs]
        if len(groups)!=1 or len(columns)<2 or len(columns)!=len(set(columns)):continue
        scores={};players=set();valid=True
        for row in table.find('tr'):
            links=[m[1] for node in row.find('a')
                   if (m:=re.search(r'loadPlayer\(24,\d+,(\d+)',node.attrs.get('onclick','')))]
            if not links:continue
            cells=list(row.find('td'));versus=[c for c in cells if 'vs' in classes(c)]
            wins=[clean(c.text()) for c in cells if 'wins' in classes(c)]
            losses=[clean(c.text()) for c in cells if 'lost' in classes(c)]
            if (len(links)!=1 or links[0] not in columns or links[0] in players
                    or len(versus)!=len(columns) or len(wins)!=1 or len(losses)!=1
                    or not wins[0].isdigit() or not losses[0].isdigit()
                    or int(wins[0])+int(losses[0])!=len(columns)-1):
                valid=False;break
            home=links[0];players.add(home)
            row_wins=0
            for away,cell in zip(columns,versus):
                value=clean(cell.text())
                if home==away:
                    if value:valid=False
                    continue
                match=re.fullmatch(r'(\d+)\s*-\s*(\d+)',value)
                if not match:valid=False;break
                a,b=map(int,match.groups())
                if max(a,b) not in (3,4) or a==b:valid=False;break
                scores[home,away]=(a,b);row_wins+=a>b
            if row_wins!=int(wins[0]):valid=False
        if not valid or players!=set(columns):continue
        if any(scores.get((b,a))!=(y,x) for (a,b),(x,y) in scores.items()):continue
        group=next(iter(groups))
        if group in matrices and matrices[group]!=scores:conflicts.add(group)
        matrices[group]=scores
    return {g:scores for g,scores in matrices.items() if g not in conflicts}


def resolve_group(rows,names,matrix,score_parser,cutoff=None):
    """Require a unique bijection between all scheduled games and matrix pairs.

    Never resolve using a name alone, a partial table, a walkover, an unplayed
    game or a repeated pairing. Existing unambiguous imports remain unaffected
    when this optional evidence cannot establish the entire group.
    """
    if not matrix or len(rows)!=len(names)*(len(names)-1)//2:return {}
    if {p for pair in matrix for p in pair}!=set(names):return {}
    bindings={};used=set()
    for game,cells in rows:
        try:result=score_parser(cells)
        except (DataError,ValueError,TypeError,IndexError):return {}
        if not result or (cutoff and result['date']>cutoff):return {}
        a,b=int(result['score1']),int(result['score2'])
        candidates=[(home,away) for home,hn in names.items() for away,an in names.items()
                    if home!=away and cells[3]==hn+' - '+an
                    and matrix.get((home,away))==(a,b) and matrix.get((away,home))==(b,a)]
        if len(candidates)!=1 or game in bindings:return {}
        pair=frozenset(candidates[0])
        if pair in used:return {}
        used.add(pair);bindings[game]=list(candidates[0])
    return bindings
