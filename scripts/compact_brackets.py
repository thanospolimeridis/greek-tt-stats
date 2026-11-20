"""Read TTScore's public winner-relative point notation, without guessing results.

A player's score in the NEXT bracket column describes their PREVIOUS match.
The current column's winner flag and explicit participant IDs establish that
association. Unsupported/ambiguous markup returns no candidate; callers must
retrieve the ordinary match-detail table instead and validate every candidate.
"""
import re
from ttscore import Document, Node, clean


def classes(node):
    return node.attrs.get('class','').split()


def participant_id(node):
    ids=re.findall(r'loadPlayer\(24,\d+,(\d+)',
                   ' '.join(a.attrs.get('onclick','') for a in node.find('a')))
    return ids[0] if len(ids)==1 else None


def bracket_byes(body):
    """Identify an explicit BYE with one identified, advancing opponent.

    Blank/unfilled positions, two byes, contradictory identities and unknown
    winner flags remain detail-page requests, never inferred exclusions.
    """
    candidates={};ambiguous=set()
    for round_ in Document(body).find('ul'):
        if 'koround' not in classes(round_):continue
        entries=[n for n in round_.children if isinstance(n,Node) and n.tag=='li']
        for index,node in enumerate(entries):
            if 'data-gameid' not in node.attrs or 'data-groupid' not in node.attrs:continue
            if not 0<index<len(entries)-1:continue
            sides=[entries[index-1],entries[index+1]]
            byes=[any('ko-bye' in classes(n) for n in side.find('div')) for side in sides]
            if sum(byes)!=1:continue
            bye=byes.index(True);other=1-bye
            ids=[participant_id(side) for side in sides]
            if ids[bye] is not None or ids[other] is None:continue
            if 'winner' not in classes(sides[other]) or 'winner' in classes(sides[bye]):continue
            group=node.attrs['data-groupid']
            candidate={'game':node.attrs['data-gameid'],'participants':ids,'player':ids[other]}
            if group in candidates and candidates[group]!=candidate:ambiguous.add(group)
            candidates[group]=candidate
    return {g:r for g,r in candidates.items() if g not in ambiguous}


def compact_games(body):
    """Return candidates keyed by group; never treat missing scores as results."""
    candidates={}; ambiguous=set()
    for parent in Document(body).find('div'):
        rounds=[n for n in parent.children if isinstance(n,Node)
                and n.tag=='ul' and 'koround' in classes(n)]
        for current, following in zip(rounds,rounds[1:]):
            entries=[n for n in current.children if isinstance(n,Node) and n.tag=='li']
            positions=[n for n in following.find('div') if 'ko-position' in classes(n)]
            for index,node in enumerate(entries):
                if 'data-gameid' not in node.attrs or 'data-groupid' not in node.attrs:
                    continue
                if not 0<index<len(entries)-1:continue
                sides=[entries[index-1],entries[index+1]]
                ids=[participant_id(n) for n in sides]
                winners=[i for i,n in enumerate(sides) if 'winner' in classes(n)]
                if len(winners)!=1 or None in ids or ids[0]==ids[1]:continue
                winner=winners[0]
                advance=[n for n in positions if participant_id(n)==ids[winner]]
                if len(advance)!=1:continue
                scores=[clean(n.text()) for n in advance[0].find('span')
                        if 'position-counter' not in classes(n)]
                # WO, BYE, missing scores, aggregate team scores and unknown
                # notation all require the original detail-page path.
                if len(scores)!=1 or not re.fullmatch(r'-?\d+(?:,-?\d+){2,6}',scores[0]):continue
                games=[]
                for token in scores[0].split(','):
                    points=abs(int(token))
                    pair=[points,max(11,points+2)] if token.startswith('-') else [max(11,points+2),points]
                    if winner==1:pair.reverse()
                    games.append(pair)
                totals=[sum(pair[i]>pair[1-i] for pair in games) for i in (0,1)]
                if totals[winner]<=totals[1-winner]:continue
                dates=[clean(n.text()) for n in node.find('div') if 'game-info' in classes(n)]
                if len(dates)!=1:continue
                cells=['0',dates[0].split(' / Table:')[0],'','',
                       ' '.join(f'{a}-{b}' for a,b in games),f'{totals[0]} - {totals[1]}']
                group=node.attrs['data-groupid']
                candidate={'game':node.attrs['data-gameid'],'participants':ids,'cells':cells}
                if group in candidates and candidates[group]!=candidate:ambiguous.add(group)
                candidates[group]=candidate
    return {g:r for g,r in candidates.items() if g not in ambiguous}
