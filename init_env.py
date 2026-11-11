from pathlib import Path
import secrets
p=Path(__file__).resolve().parent/'.env'
if not p.exists():
 p.write_text('JWT_SECRET='+secrets.token_hex(48)+'\nLAB_ADMIN_PASSWORD='+secrets.token_urlsafe(24)+'\nLAB_USER_PASSWORD='+secrets.token_urlsafe(24)+'\nZAP_API_KEY='+secrets.token_hex(24)+'\n')
 p.chmod(0o600)
 print('Secretos de laboratorio creados en .env; no compartir el archivo.')
else: print('.env existente conservado.')
