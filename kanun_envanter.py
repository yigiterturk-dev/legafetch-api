import json, re, collections, urllib.request
import os
URL="http://127.0.0.1:6333/collections/lexordo_pasajlar/points/scroll"
KEY=os.environ.get("QK","")
def post(body):
    req=urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type":"application/json","api-key":KEY})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())
say=collections.Counter(); ad={}; off=None; tot=0
while True:
    b={"limit":2000,"with_payload":True,"with_vector":False,
       "filter":{"must":[{"key":"belgeSinifi","match":{"value":"mevzuat"}}]}}
    if off is not None: b["offset"]=off
    r=post(b)["result"]; pts=r["points"]; off=r.get("next_page_offset")
    if not pts: break
    for p in pts:
        pl=p.get("payload") or {}; md=pl.get("metadata") or pl
        did=str(md.get("docId") or ""); tot+=1
        m=re.match(r"mevzuat-([0-9A-Za-z]+)-madde", did)
        if m:
            say[m.group(1)]+=1; ad.setdefault(m.group(1), str(md.get("baslik") or "")[:70])
    if off is None: break
print("toplam mevzuat pasaji:",tot,"| kanun:",len(say))
for k,n in sorted(say.items(), key=lambda x:-x[1]):
    print(f"{k:<8}{n:>5}  {ad.get(k,)}")
