import subprocess,json,pathlib,urllib.request,urllib.error,time
R=pathlib.Path(__file__).resolve().parent
def aws(*args):
    p=subprocess.run(['docker','exec','actividad3-seguridad-localstack-1','awslocal',*args],capture_output=True,text=True)
    if p.returncode:return {'error':p.stderr.strip(),'exit_code':p.returncode}
    return json.loads(p.stdout) if p.stdout.strip() else {}
b='actividad3-seguro-2024'
results={
 'bucket':b,
 'endpoint':'http://127.0.0.1:4566',
 'fecha_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
 'policy_status':aws('s3api','get-bucket-policy-status','--bucket',b),
 'bucket_policy':aws('s3api','get-bucket-policy','--bucket',b),
 'public_access_block':aws('s3api','get-public-access-block','--bucket',b),
 'encryption':aws('s3api','get-bucket-encryption','--bucket',b),
 'ownership':aws('s3api','get-bucket-ownership-controls','--bucket',b),
 'acl':aws('s3api','get-bucket-acl','--bucket',b)
}
subprocess.run(['docker','exec','actividad3-seguridad-localstack-1','sh','-c','printf "Objeto de prueba del laboratorio de seguridad\\n" > /tmp/actividad3-evidencia.txt'],check=True)
results['put_object']=aws('s3api','put-object','--bucket',b,'--key','evidencia.txt','--body','/tmp/actividad3-evidencia.txt')
results['head_object']=aws('s3api','head-object','--bucket',b,'--key','evidencia.txt')
try:
 with urllib.request.urlopen('http://127.0.0.1:4566/'+b+'/evidencia.txt') as r:results['anonymous_get_http']=r.status
except urllib.error.HTTPError as e:results['anonymous_get_http']=e.code
checks={
 'bucket_no_publico_segun_policy_status':results['policy_status'].get('PolicyStatus',{}).get('IsPublic'),
 'cuatro_bloqueos_activos':all(results['public_access_block']['PublicAccessBlockConfiguration'].values()),
 'cifrado_AES256':results['encryption']['ServerSideEncryptionConfiguration']['Rules'][0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']=='AES256',
 'objeto_AES256':results['head_object'].get('ServerSideEncryption')=='AES256',
 'propietario_forzado':results['ownership']['OwnershipControls']['Rules'][0]['ObjectOwnership']=='BucketOwnerEnforced',
 'lectura_anonima_rechazada':results['anonymous_get_http']==403
}
results['checks']=checks
(R/'evidence/s3-validation.json').write_text(json.dumps(results,indent=2,ensure_ascii=False))
print(json.dumps(results,indent=2,ensure_ascii=False))
assert all(checks[k] for k in ['cuatro_bloqueos_activos','cifrado_AES256','objeto_AES256','propietario_forzado']), 'S3 configuration validation failed'
