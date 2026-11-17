"""Baseline reproduction. Rectangle clipping below is test-only, not a general solution."""
import copy, json, tempfile
from fractions import Fraction
from pathlib import Path
from regions import RegionCatalog
from warehouse import TrackWarehouse

def point(pid,t,x,y):
    return {'track_id':'truck','point_id':pid,'revision':1,'t':t,'x':x,'y':y,'retracted':False}

def one_rectangle_fixture(left,right,cells):
    # Accurate test-only continuous clipping for exactly one closed rectangle.
    # It does not implement normalization, union, holes, revision handling, or UNKNOWN.
    assert len(cells)==1
    a,b,c,d=cells[0]
    lo,hi=Fraction(0),Fraction(1)
    for value,delta,low,high in ((left['x'],right['x']-left['x'],a,c),(left['y'],right['y']-left['y'],b,d)):
        if delta==0:
            if not low<=value<=high: return []
        else:
            u,v=sorted((Fraction(low-value,delta),Fraction(high-value,delta)))
            lo=max(lo,u); hi=min(hi,v)
    if hi<=lo: return []
    dt=right['t']-left['t']
    return [(left['t']+lo*dt,left['t']+hi*dt)]

class ObservedProvider:
    def __init__(self,real,frozen_cells=None):
        self.real=real; self.frozen_cells=frozen_cells; self.last=None
    def snapshot(self):
        product=self.real.snapshot()
        if self.frozen_cells is not None:
            product['regions'][0]['cells']=copy.deepcopy(self.frozen_cells)
        self.last=copy.deepcopy(product)
        return product

def expected_fact(snapshot,lo,hi):
    return {'facts':[{'snapshot_id':snapshot['snapshot_id'],'region_id':'yard','region_revision':snapshot['regions'][0]['revision'],'track_id':'truck','left_point_id':'p0','left_revision':1,'right_point_id':'p1','right_revision':1,'start':[lo,1],'end':[hi,1],'duration':[hi-lo,1]}], 'summary':{'yard':[hi-lo,1]},'unknown':[]}

def main():
    with tempfile.TemporaryDirectory(prefix='geofence614-') as tmp:
        catalog_path=str(Path(tmp)/'regions.sqlite')
        catalog=RegionCatalog(catalog_path)
        catalog.replace('yard',1,[[-1,-1,1,1]],[])
        snap_a=catalog.publish()
        ordinary_client={label:catalog.classify(snap_a['snapshot_id'],'yard',Fraction(x),Fraction(y)) for label,x,y in [('inside',0,0),('edge',1,0),('outside',2,0)]}
        try:
            catalog.replace('hole',1,[[-2,-2,2,2]],[[-1,-1,1,1]])
            source_failure={'unexpected':'accepted'}
        except NotImplementedError as exc:
            source_failure={'input':{'positive':[[-2,-2,2,2]],'exclude':[[-1,-1,1,1]]},'actual':type(exc).__name__+': '+str(exc),'required':'published ring; center OUT, hole boundary BOUNDARY'}
        baseline=TrackWarehouse(str(Path(tmp)/'baseline.sqlite'),catalog)
        baseline.put_points([point('p0',0,0,0),point('p1',4,0,0)])
        ordinary=baseline.query('truck',0,4,4)
        baseline.put_points([point('p0',0,-2,0),point('p1',4,2,0)])
        crossing=baseline.query('truck',0,4,4)
        h1={'business_input':{'points':[point('p0',0,-2,0),point('p1',4,2,0)],'query':['truck',0,4,4]},'actual':crossing,'oracle_expected':expected_fact(snap_a,1,3),'oracle_basis':'x(t)=-2+t; -1<=x<=1 iff 1<=t<=3; both endpoints OUT'}
        baseline.close()
        # Same actual warehouse, isolated exact-one-rectangle test kernel. Actual source products are consumed.
        observed=ObservedProvider(catalog)
        witness=TrackWarehouse(str(Path(tmp)/'witness.sqlite'),observed,one_rectangle_fixture)
        pts=[point('p0',0,-2,0),point('p1',4,2,0)]
        witness.put_points(pts)
        business={'points':pts,'query':{'track_id':'truck','start':0,'end':4,'max_gap':4}}
        before_result=witness.query('truck',0,4,4)
        before={'business_input':business,'producer_projection':snap_a,'consumer_projection':observed.last,'downstream_observation':before_result,'oracle_expected':expected_fact(snap_a,1,3)}
        catalog.replace('yard',2,[[0,-1,1,1]],[])
        snap_b=catalog.publish()
        after_result=witness.query('truck',0,4,4)
        after={'business_input':business,'producer_projection':snap_b,'consumer_projection':observed.last,'downstream_observation':after_result,'oracle_expected':expected_fact(snap_b,2,3)}
        observed.frozen_cells=snap_a['regions'][0]['cells']
        disconnected_result=witness.query('truck',0,4,4)
        disconnected={'business_input':business,'producer_projection':catalog.snapshot(snap_b['snapshot_id']),'consumer_projection':observed.last,'downstream_observation':disconnected_result,'oracle_expected':expected_fact(snap_b,2,3)}
        persisted=witness.persisted_results()
        witness.close(); catalog.close()
        reopened=RegionCatalog(catalog_path)
        reopen={'snapshot_a':reopened.snapshot(snap_a['snapshot_id']),'snapshot_b':reopened.snapshot(snap_b['snapshot_id'])}
        reopened.close()
        output={'ordinary_region_client':ordinary_client,'source_failure':source_failure,'ordinary_endpoint_baseline':ordinary,'double_outside_crossing':h1,'coupling':{'before':before,'after':after,'disconnected':disconnected},'persisted_actual_query_rows':persisted,'reopen':reopen,'scope':'Baseline probe only: full geometry, revisions, UNKNOWN and plan CLI unfinished. Exact clipping kernel is one-rectangle test fixture.'}
        assert ordinary_client=={'inside':'IN','edge':'BOUNDARY','outside':'OUT'}
        assert ordinary['summary']=={'yard':[4,1]}
        assert crossing['summary']=={'yard':[0,1]}
        assert before_result==before['oracle_expected'] and after_result==after['oracle_expected']
        assert disconnected_result!=after['oracle_expected']
        assert len(persisted)==3 and persisted==[before_result,after_result,disconnected_result]
        assert reopen['snapshot_a']==snap_a and reopen['snapshot_b']==snap_b
        print(json.dumps(output,ensure_ascii=False,sort_keys=True,indent=2))

if __name__=='__main__': main()
