'use strict';
const express = require('express');
const jwt = require('jsonwebtoken');
const helmet = require('helmet');
const {timingSafeEqual} = require('node:crypto');
const app = express();
const secret = process.env.JWT_SECRET;
if (!secret || Buffer.byteLength(secret) < 32) throw new Error('JWT_SECRET must contain at least 32 bytes');
const issuer = 'actividad3-local';
const audience = 'actividad3-api';
const accounts = {
  admin: {password: process.env.LAB_ADMIN_PASSWORD, role: 'admin'},
  alumno: {password: process.env.LAB_USER_PASSWORD, role: 'user'}
};
app.disable('x-powered-by');
app.use(helmet());
app.use(express.json({limit: '8kb'}));
app.use((req,res,next) => {res.set('Cache-Control','no-store'); next();});
function same(a,b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  const x=Buffer.from(a), y=Buffer.from(b);
  return x.length === y.length && timingSafeEqual(x,y);
}
app.get('/health', (req,res)=>res.json({status:'ok'}));
// Demo accounts are configured by the operator; the client cannot set a role.
app.post('/auth/login', (req,res)=>{
  const username = typeof req.body.username === 'string' ? req.body.username : '';
  const account = Object.hasOwn(accounts, username) ? accounts[username] : null;
  if (!account || !same(req.body.password, account.password)) return res.status(401).json({error:'Invalid credentials'});
  const token=jwt.sign({role:account.role},secret,{algorithm:'HS256',subject:username,issuer,audience,expiresIn:'15m'});
  res.json({token,token_type:'Bearer',expires_in:900});
});
function authenticate(req,res,next) {
  const match = /^Bearer ([^\s]+)$/.exec(req.get('Authorization') || '');
  if (!match) return res.status(401).json({error:'Bearer token required'});
  try {
    const claims=jwt.verify(match[1],secret,{algorithms:['HS256'],issuer,audience});
    if (typeof claims !== 'object' || typeof claims.sub !== 'string' || !Number.isFinite(claims.exp)) throw new Error('Required claims missing');
    req.auth=claims;
    next();
  } catch (_) { res.status(401).json({error:'Invalid or expired token'}); }
}
app.get('/api/profile',authenticate,(req,res)=>res.json({user:req.auth.sub,role:req.auth.role}));
app.get('/api/admin',authenticate,(req,res)=>{
  if (req.auth.role !== 'admin') return res.status(403).json({error:'Administrator role required'});
  res.json({message:'Authorized administrative access',user:req.auth.sub});
});
app.use((req,res)=>res.status(404).json({error:'Not found'}));
app.use((err,req,res,next)=>res.status(err.status===413?413:400).json({error:'Invalid request'}));
app.listen(3000,'0.0.0.0',()=>console.log('Lab API ready on port 3000; JWT HS256; issuer and audience validated'));
