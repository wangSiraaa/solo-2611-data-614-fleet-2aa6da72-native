"""Ordinary rectangle-only prototype. Full region normalization is unfinished."""
import json, sqlite3
from fractions import Fraction

class RegionCatalog:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.execute('create table if not exists region(id text primary key, rev integer, cells text)')
        self.db.execute('create table if not exists snapshot(id integer primary key, body text)')
        self.db.commit()
    def replace(self, region_id, revision, positive, exclude):
        # Only the ordinary one-positive/no-exclusion case is implemented.
        if len(positive) != 1 or exclude:
            raise NotImplementedError('normalization/exclusions unfinished')
        cells = [list(positive[0])]
        self.db.execute('insert or replace into region values(?,?,?)', (region_id, revision, json.dumps(cells)))
        self.db.commit()
    def publish(self):
        rows = [{'region_id': i, 'revision': r, 'cells': json.loads(c)} for i,r,c in self.db.execute('select * from region order by id')]
        cur = self.db.execute('insert into snapshot(body) values(?)', (json.dumps(rows, sort_keys=True),))
        self.db.commit()
        return self.snapshot(str(cur.lastrowid))
    def snapshot(self, snapshot_id=None):
        if snapshot_id is None:
            row=self.db.execute('select max(id) from snapshot').fetchone()
            if row[0] is None: raise KeyError('no published snapshot')
            snapshot_id=str(row[0])
        body = self.db.execute('select body from snapshot where id=?',(snapshot_id,)).fetchone()
        if body is None: raise KeyError(snapshot_id)
        return {'snapshot_id': str(snapshot_id), 'regions': json.loads(body[0])}
    def classify(self, snapshot_id, region_id, x, y):
        cells = next(r['cells'] for r in self.snapshot(snapshot_id)['regions'] if r['region_id']==region_id)
        for a,b,c,d in cells:
            if a < x < c and b < y < d: return 'IN'
            if a <= x <= c and b <= y <= d: return 'BOUNDARY'
        return 'OUT'
    def close(self): self.db.close()
