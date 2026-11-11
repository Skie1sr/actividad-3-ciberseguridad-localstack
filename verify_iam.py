import subprocess,json,pathlib,time
R=pathlib.Path(__file__).resolve().parent
script=r'''
import boto3,json
endpoint='http://localhost:4566'
kwargs=dict(endpoint_url=endpoint,region_name='us-east-1',aws_access_key_id='test',aws_secret_access_key='test')
iam=boto3.client('iam',**kwargs);sts=boto3.client('sts',**kwargs)
role='Actividad3LecturaS3';arn='arn:aws:iam::000000000000:role/'+role
creds=sts.assume_role(RoleArn=arn,RoleSessionName='evidencia-rubrica')['Credentials']
s3=boto3.client('s3',endpoint_url=endpoint,region_name='us-east-1',aws_access_key_id=creds['AccessKeyId'],aws_secret_access_key=creds['SecretAccessKey'],aws_session_token=creds['SessionToken'])
stsr=boto3.client('sts',endpoint_url=endpoint,region_name='us-east-1',aws_access_key_id=creds['AccessKeyId'],aws_secret_access_key=creds['SecretAccessKey'],aws_session_token=creds['SessionToken'])
r={'role_arn':arn,'assumed_identity':stsr.get_caller_identity()['Arn'],'inline_policy':iam.get_role_policy(RoleName=role,PolicyName='LeerSoloEvidencia')['PolicyDocument']}
obj=s3.get_object(Bucket='actividad3-seguro-2024',Key='evidencia.txt')
r['get_object_http']=obj['ResponseMetadata']['HTTPStatusCode'];r['object_bytes']=len(obj['Body'].read())
try:
 result=s3.put_object(Bucket='actividad3-seguro-2024',Key='intento-escritura.txt',Body=b'Prueba negativa IAM')
 r['put_object_http']=result['ResponseMetadata']['HTTPStatusCode']
 s3.delete_object(Bucket='actividad3-seguro-2024',Key='intento-escritura.txt')
except Exception as e:r['put_object_error']=str(e)
r['lectura_permitida']=r['get_object_http']==200
r['escritura_rechazada']=r.get('put_object_http') is None and 'AccessDenied' in r.get('put_object_error','')
print(json.dumps(r,indent=2))
'''
p=subprocess.run(['docker','exec','-i','actividad3-seguridad-localstack-1','python'],input=script,text=True,capture_output=True)
if p.returncode:raise RuntimeError(p.stderr)
j=json.loads(p.stdout);j['fecha_utc']=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())
(R/'evidence/iam-validation.json').write_text(json.dumps(j,indent=2,ensure_ascii=False))
print(json.dumps(j,indent=2,ensure_ascii=False))
assert j['lectura_permitida']
