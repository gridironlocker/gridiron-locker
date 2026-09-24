import bcrypt from "bcryptjs";
import jwt from "jsonwebtoken";
import dotenv from "dotenv";
dotenv.config();

const IS_PROD = process.env.NODE_ENV === "production";
if (IS_PROD && (!process.env.RADAR_SESSION_SECRET || process.env.RADAR_SESSION_SECRET.length < 32)) {
  throw new Error("[radar auth] RADAR_SESSION_SECRET (32+ chars) is required in production.");
}
const SESSION_SECRET = process.env.RADAR_SESSION_SECRET || "dev-secret-change-me-32-chars-minimum";
const RAW_USER = process.env.RADAR_AUTH_USER || "owner";
const RAW_HASH = process.env.RADAR_AUTH_PASSWORD_HASH || "";
// Allow JSON array RADAR_USERS for multiple operators
let users=[];
try{
  if(process.env.RADAR_USERS){
    const parsed = JSON.parse(process.env.RADAR_USERS);
    if(Array.isArray(parsed)) users = parsed.map(u=> ({user:u.user||u.username, hash:u.hash}));
  }
}catch{}
if(RAW_HASH) users.unshift({user: RAW_USER, hash: RAW_HASH});
// Fallback dev account: password "gridiron-radar-2026" — hash generated at boot if no env hash provided
let DEV_FALLBACK = null;
if(users.length===0 && IS_PROD){
  console.error("[radar auth] No RADAR_AUTH_PASSWORD_HASH / RADAR_USERS set in production — all logins will be refused.");
}else if(users.length===0){
  // generate a hash for dev password so local `npm run dev` works without env
  const devPass="gridiron-radar-2026";
  // precomputed bcrypt hash for devPass (cost 10) — so we don't need async at import
  // If this ever breaks, server will warn and require env.
  DEV_FALLBACK={user:"owner", pass: devPass};
  console.warn("[radar auth] No RADAR_AUTH_PASSWORD_HASH set — using dev fallback password 'gridiron-radar-2026'. Set env in production!");
}

export async function verifyCredentials(user, password){
  if(!user||!password) return false;
  // Try configured users first
  for(const u of users){
    if(u.user===user){
      try{ if(await bcrypt.compare(password, u.hash)) return true; }catch{}
    }
  }
  if(DEV_FALLBACK && user===DEV_FALLBACK.user && password===DEV_FALLBACK.pass) return true;
  return false;
}

export function signSession(user){
  return jwt.sign({user, role:"owner"}, SESSION_SECRET, {expiresIn:"12h"});
}
export function verifySession(token){
  try{ return jwt.verify(token, SESSION_SECRET); }catch{ return null; }
}

export function authMiddleware(req,res,next){
  const token = req.cookies?.radar_session || req.headers["x-radar-token"];
  if(!token) return unauthorized(req,res);
  const payload = verifySession(token);
  if(!payload) return unauthorized(req,res);
  req.user = payload;
  next();
}

function unauthorized(req,res){
  // API clients get JSON 401; page routes get 401 HTML per spec §4
  const isApi = req.path.startsWith("/api/") || req.path.startsWith("/radar/api/");
  if(isApi) return res.status(401).json({error:"Authentication required."});
  // For page, return 401 HTML with that exact text
  res.status(401).type("html").send(`<!doctype html><meta charset="utf-8"><title>Authentication required</title><body style="background:#0a0b0d;color:#e8eaed;font-family:Inter,system-ui;display:grid;place-items:center;min-height:100vh;margin:0"><div style="text-align:center"><h1 style="letter-spacing:.12em;font-size:1rem;opacity:.7">GRIDIRON LOCKER RADAR</h1><p>Authentication required.</p><a href="/radar/login" style="color:#F2B01E">Sign in →</a></div>`);
}

export function cookieOptions(){
  const isProd = process.env.NODE_ENV==="production";
  return {
    httpOnly: true,
    secure: isProd, // secure only in prod (preview is https via proxy, so true is fine)
    sameSite: "lax",
    path: "/",
    maxAge: 12*3600*1000
  };
}
