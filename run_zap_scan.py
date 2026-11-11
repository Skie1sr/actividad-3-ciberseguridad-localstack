import urllib.request,urllib.parse,json,time,pathlib
R=pathlib.Path(__file__).resolve().parent
cfg=dict(line.split('=',1) for line in (R/'.env').read_text().splitlines() if '=' in line)
def zap(component,kind,method,**params):
 params['apikey']=cfg['ZAP_API_KEY']
 url=f'http://127.0.0.1:8089/JSON/{component}/{kind}/{method}/?'+urllib.parse.urlencode(params)
 req=urllib.request.Request(url,headers={'Host':'zap'})
 for attempt in range(10):
  try:
   with urllib.request.urlopen(req,timeout=30) as r:return json.loads(r.read())
  except Exception:
   if attempt==9:raise
   time.sleep(1)
print('ZAP version:',zap('core','view','version'))
print('OpenAPI import:',zap('openapi','action','importFile',file='/zap/wrk/openapi.json',target='http://api:3000'))
policies=zap('ascan','view','scanPolicyNames')
print('Available scan policies:',policies)
if 'API Minimal' not in policies.get('scanPolicyNames',[]):
 print('API scan policy:',zap('ascan','action','importScanPolicy',path='/zap/wrk/API-Minimal.policy'))
token=(R/'zap/admin-token.txt').read_text().strip()
if any(r.get('description')=='JWT lab admin' for r in zap('replacer','view','rules').get('rules',[])):
 zap('replacer','action','removeRule',description='JWT lab admin')
print('Authenticated scan rule:',zap('replacer','action','addRule',description='JWT lab admin',enabled='true',matchType='REQ_HEADER',matchRegex='false',matchString='Authorization',replacement='Bearer '+token))
scan=zap('ascan','action','scan',url='http://api:3000',recurse='true',inScopeOnly='false',scanPolicyName='API Minimal')['scan']
start=time.time()
while True:
 status=zap('ascan','view','status',scanId=scan)['status']
 print('Active scan progress:',status,flush=True)
 if status=='100':break
 if time.time()-start>360:
  zap('ascan','action','stop',scanId=scan)
  raise RuntimeError('Active scan exceeded six minutes; stopped')
 time.sleep(5)
while int(zap('pscan','view','recordsToScan')['recordsToScan']):time.sleep(1)
alerts=zap('core','view','alerts',baseurl='http://api:3000',start=0,count=1000)
# Remove transient tokens and credentials from exported alerts and HTTP examples.
def scrub(v):
 if isinstance(v,str):
  for secret in [token,cfg['JWT_SECRET'],cfg['LAB_ADMIN_PASSWORD'],cfg['LAB_USER_PASSWORD'],cfg['ZAP_API_KEY']]:v=v.replace(secret,'[REDACTED]')
  return v
 if isinstance(v,list):return [scrub(x) for x in v]
 if isinstance(v,dict):return {k:scrub(x) for k,x in v.items()}
 return v
alerts=scrub(alerts)
(R/'evidence/zap-alerts.json').write_text(json.dumps(alerts,indent=2,ensure_ascii=False))
with urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8089/OTHER/core/other/htmlreport/?'+urllib.parse.urlencode({'apikey':cfg['ZAP_API_KEY']}),headers={'Host':'zap'}),timeout=30) as r:
 html=scrub(r.read().decode())
(R/'evidence/zap-report.html').write_text(html)
summary={'fecha_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'version':zap('core','view','version')['version'],'target':'http://api:3000','scan_id':scan,'active_progress':status,'alerts':len(alerts['alerts']),'risk_counts':{},'rules':{}}
for a in alerts['alerts']:
 summary['risk_counts'][a['risk']]=summary['risk_counts'].get(a['risk'],0)+1
 summary['rules'][a['pluginId']]={'name':a['alert'],'risk':a['risk'],'confidence':a['confidence'],'solution':a['solution']}
summary['urls']=zap('core','view','urls',baseurl='http://api:3000')['urls']
(R/'evidence/zap-summary.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False))
print(json.dumps(summary,indent=2,ensure_ascii=False))
zap('replacer','action','removeRule',description='JWT lab admin')
