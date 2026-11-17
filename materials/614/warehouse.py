"""Ordinary endpoint-inside prototype, intentionally incomplete."""
import json, sqlite3
from fractions import Fraction

def rational(v):
    v=Fraction(v)
    return [v.numerator,v.denominator]

def endpoint_inside(left, right, cells):
    def inside(p):
        return any(a<=p['x']<=c and b<=p['y']<=d for a,b,c,d in cells)
    return [(Fraction(left['t']),Fraction(right['t']))] if inside(left) and inside(right) else []

class TrackWarehouse:
    def __init__(self, path, provider, interval_kernel=endpoint_inside):
        self.db=sqlite3.connect(path)
        self.db.execute('create table if not exists point(track text, id text, body text, primary key(track,id))')
        self.db.execute('create table if not exists query_result(id integer primary key, body text)')
        self.db.commit()
        self.provider=provider
        self.interval_kernel=interval_kernel
    def put_points(self,batch):
        # Ordinary inserts only; revision ordering and atomic conflict checks unfinished.
        for p in batch:
            self.db.execute('insert or replace into point values(?,?,?)',(p['track_id'],p['point_id'],json.dumps(p,sort_keys=True)))
            self.db.commit()
    def query(self,track_id,start,end,max_gap):
        snapshot=self.provider.snapshot()
        pts=[json.loads(row[0]) for row in self.db.execute('select body from point where track=?',(track_id,))]
        pts=sorted((p for p in pts if not p['retracted']),key=lambda p:p['t'])
        facts=[]
        for left,right in zip(pts,pts[1:]):
            if right['t']-left['t']>max_gap: continue
            for region in snapshot['regions']:
                for lo,hi in self.interval_kernel(left,right,region['cells']):
                    lo=max(lo,Fraction(start)); hi=min(hi,Fraction(end))
                    if hi<=lo: continue
                    facts.append({'snapshot_id':snapshot['snapshot_id'],'region_id':region['region_id'],'region_revision':region['revision'],'track_id':track_id,'left_point_id':left['point_id'],'left_revision':left['revision'],'right_point_id':right['point_id'],'right_revision':right['revision'],'start':rational(lo),'end':rational(hi),'duration':rational(hi-lo)})
        result={'facts':facts, 'summary':{r['region_id']:rational(sum((Fraction(*f['duration']) for f in facts if f['region_id']==r['region_id']),Fraction())) for r in snapshot['regions']},'unknown':[]}
        # Persists the actual produced relation for inspection; not an immutable query API yet.
        self.db.execute('insert into query_result(body) values(?)',(json.dumps(result,sort_keys=True),))
        self.db.commit()
        return result
    def persisted_results(self):
        return [json.loads(x[0]) for x in self.db.execute('select body from query_result order by id')]
    def close(self): self.db.close()
