import urllib.request, urllib.error, json, pathlib, time, base64, hmac, hashlib
ROOT=pathlib.Path(__file__).resolve().parent
cfg=dict(line.strip().split('=',1) for line in (ROOT/'.env').read_text().splitlines() if '=' in line)
proxy=urllib.request.build_opener(urllib.request.ProxyHandler({'http':'http://127.0.0.1:8089'}))
base='http://api:3000'
def request(path,method='GET',body=None,token=None):
    headers={'Content-Type':'application/json'}
    if token is not None: headers['Authorization']='Bearer '+token
    req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers,method=method)
    try:
        with proxy.open(req,timeout=20) as r: return r.status,json.loads(r.read())
    except urllib.error.HTTPError as e: return e.code,json.loads(e.read())
for _ in range(30):
    try:
        if request('/health')[0]==200:break
    except Exception:time.sleep(1)
else:raise RuntimeError('API or ZAP proxy unavailable')
admin=request('/auth/login','POST',{'username':'admin','password':cfg['LAB_ADMIN_PASSWORD']})[1]['token']
user=request('/auth/login','POST',{'username':'alumno','password':cfg['LAB_USER_PASSWORD']})[1]['token']
def b64(b):return base64.urlsafe_b64encode(b).rstrip(b'=')
def sign(**overrides):
    payload={'sub':'admin','role':'admin','iss':'actividad3-local','aud':'actividad3-api','iat':int(time.time()),'exp':int(time.time())+900}
    payload.update(overrides)
    a=b64(json.dumps({'alg':'HS256','typ':'JWT'}).encode())+b'.'+b64(json.dumps(payload).encode())
    return (a+b'.'+b64(hmac.new(cfg['JWT_SECRET'].encode(),a,hashlib.sha256).digest())).decode()
tamper=admin.split('.');claims=json.loads(base64.urlsafe_b64decode(tamper[1]+'==='));claims['sub']='intruder';tamper[1]=b64(json.dumps(claims).encode()).decode()
none=b64(b'{"alg":"none","typ":"JWT"}').decode()+'.'+b64(json.dumps({'sub':'admin','role':'admin'}).encode()).decode()+'.'
cases=[
 ('Health público','/health',None,200),
 ('Sin token','/api/admin',None,401),
 ('Token mal formado','/api/admin','invalid',401),
 ('Firma alterada','/api/admin','.'.join(tamper),401),
 ('Token vencido','/api/admin',sign(exp=int(time.time())-60),401),
 ('Emisor incorrecto','/api/admin',sign(iss='otro-emisor'),401),
 ('Audiencia incorrecta','/api/admin',sign(aud='otra-api'),401),
 ('Algoritmo none','/api/admin',none,401),
 ('Usuario sin permiso admin','/api/admin',user,403),
 ('Usuario con perfil permitido','/api/profile',user,200),
 ('Administrador válido','/api/admin',admin,200),
]
results=[]
for name,path,token,expected in cases:
    status,body=request(path,token=token)
    results.append({'caso':name,'ruta':path,'esperado':expected,'obtenido':status,'resultado':'PASS' if status==expected else 'FAIL','respuesta':body})
# Client-supplied role must not change the server-assigned user role.
status,body=request('/auth/login','POST',{'username':'alumno','password':cfg['LAB_USER_PASSWORD'],'role':'admin'})
status,body=request('/api/admin',token=body['token'])
results.append({'caso':'Escalamiento por role en login','ruta':'/api/admin','esperado':403,'obtenido':status,'resultado':'PASS' if status==403 else 'FAIL','respuesta':body})
status,body=request('/auth/login','POST',{'username':'admin','password':'incorrecta'})
results.append({'caso':'Contraseña incorrecta','ruta':'/auth/login','esperado':401,'obtenido':status,'resultado':'PASS' if status==401 else 'FAIL','respuesta':body})
data={'fecha_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'transporte':'HTTP a través del proxy OWASP ZAP en 127.0.0.1:8089','total':len(results),'correctas':sum(r['resultado']=='PASS' for r in results),'pruebas':results}
(ROOT/'evidence/api-tests.json').write_text(json.dumps(data,indent=2,ensure_ascii=False))
for r in results:print(f"{r['resultado']:4} | {r['caso']:34} | esperado {r['esperado']} | obtenido {r['obtenido']}")
assert data['correctas']==data['total'], 'JWT test failure'
# Short-lived lab token is used only by the local scanner and excluded from the deliverable.
t=ROOT/'zap/admin-token.txt';t.write_text(admin);t.chmod(0o600)
