import re
import time
from datetime import datetime,timedelta,timezone
import bcrypt
import jwt
from fastapi import APIRouter,Depends,HTTPException,Request,Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import config
from .db import get_db
from .models import user

router=APIRouter(prefix="/api/auth",tags=["auth"])
cookie_name="mp_session"
email_re=re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
attempts={}
dummy_hash=bcrypt.hashpw(b"not-a-real-password",bcrypt.gensalt()).decode()

class registerin(BaseModel):
    email:str
    password:str
    name:str=""

class loginin(BaseModel):
    email:str
    password:str

class googlein(BaseModel):
    credential:str

class userout(BaseModel):
    id:int
    email:str
    name:str
    role:str="user"

class authconfig(BaseModel):
    google_client_id:str|None=None

def hash_password(pw):
    return bcrypt.hashpw(pw.encode("utf-8")[:72],bcrypt.gensalt()).decode()

def check_password(pw,hashed):
    try:
        return bcrypt.checkpw(pw.encode("utf-8")[:72],hashed.encode())
    except ValueError:
        return False

def make_token(uid):
    exp=datetime.now(timezone.utc)+timedelta(days=config.session_days)
    return jwt.encode({"sub":str(uid),"exp":exp},config.secret_key,algorithm="HS256")

def set_session(response,uid):
    response.set_cookie(cookie_name,make_token(uid),max_age=config.session_days*86400,httponly=True,samesite="lax",secure=config.cookie_secure,path="/")

def throttle(key):
    now=time.time()
    recent=[t for t in attempts.get(key,[]) if now-t<600]
    if len(recent)>=10:
        attempts[key]=recent
        raise HTTPException(429,"too many attempts, try again in a few minutes")
    recent.append(now)
    attempts[key]=recent

def clean_email(email):
    e=email.strip().lower()
    if not email_re.match(e) or len(e)>255:
        raise HTTPException(422,"enter a valid email address")
    return e

def current_user(request:Request,db:Session=Depends(get_db)):
    token=request.cookies.get(cookie_name)
    if not token:
        raise HTTPException(401,"not signed in")
    try:
        data=jwt.decode(token,config.secret_key,algorithms=["HS256"])
        row=db.get(user,int(data["sub"]))
    except (jwt.PyJWTError,KeyError,ValueError):
        raise HTTPException(401,"session expired")
    if row is None:
        raise HTTPException(401,"not signed in")
    return row

def require_admin(row:user=Depends(current_user)):
    if row.role!="admin":
        raise HTTPException(403,"admin only")
    return row

def ensure_admin(db):
    row=db.scalar(select(user).where(user.email==config.admin_email))
    if row is None:
        row=user(email=config.admin_email,name=config.admin_name,password_hash=hash_password(config.admin_password),role="admin")
        db.add(row)
    elif row.role!="admin":
        row.role="admin"
        row.name=config.admin_name
        row.password_hash=hash_password(config.admin_password)
        row.google_sub=None
    db.commit()
    return row

@router.get("/config",response_model=authconfig)
def auth_config():
    return {"google_client_id":config.google_client_id or None}

@router.post("/register",response_model=userout,status_code=201)
def register(body:registerin,response:Response,request:Request,db:Session=Depends(get_db)):
    throttle("reg:"+(request.client.host if request.client else "?"))
    email=clean_email(body.email)
    if len(body.password)<8:
        raise HTTPException(422,"password must be at least 8 characters")
    if len(body.password.encode("utf-8"))>72:
        raise HTTPException(422,"password must be at most 72 bytes")
    if db.scalar(select(user.id).where(user.email==email)):
        raise HTTPException(409,"an account with this email already exists")
    row=user(email=email,name=body.name.strip()[:120] or email.split("@")[0],password_hash=hash_password(body.password))
    db.add(row)
    db.commit()
    set_session(response,row.id)
    return row

@router.post("/login",response_model=userout)
def login(body:loginin,response:Response,db:Session=Depends(get_db)):
    email=body.email.strip().lower()
    throttle("login:"+email)
    row=db.scalar(select(user).where(user.email==email))
    hashed=row.password_hash if row and row.password_hash else dummy_hash
    ok=check_password(body.password,hashed)
    if not row or not row.password_hash or not ok:
        if row and not row.password_hash:
            raise HTTPException(401,"this account uses Google sign-in")
        raise HTTPException(401,"incorrect email or password")
    set_session(response,row.id)
    return row

@router.post("/google",response_model=userout)
def google_login(body:googlein,response:Response,db:Session=Depends(get_db)):
    if not config.google_client_id:
        raise HTTPException(503,"google sign-in is not configured")
    from google.oauth2 import id_token
    from google.auth.exceptions import TransportError
    from google.auth.transport import requests as grequests
    try:
        info=id_token.verify_oauth2_token(body.credential,grequests.Request(),config.google_client_id)
    except TransportError:
        raise HTTPException(503,"could not reach Google to verify the sign-in, try again")
    except ValueError:
        raise HTTPException(401,"google sign-in failed")
    if not info.get("email") or not info.get("email_verified"):
        raise HTTPException(401,"your google email is not verified")
    sub=info["sub"]
    email=info["email"].lower()
    row=db.scalar(select(user).where(user.google_sub==sub))
    if row is not None and row.role=="admin":
        raise HTTPException(403,"the admin account must sign in with its password")
    if row is None:
        row=db.scalar(select(user).where(user.email==email))
        if row is not None and row.role=="admin":
            raise HTTPException(403,"the admin account must sign in with its password")
        if row is None:
            row=user(email=email,name=(info.get("name") or email.split("@")[0])[:120],google_sub=sub)
            db.add(row)
        else:
            row.google_sub=sub
        db.commit()
    set_session(response,row.id)
    return row

@router.post("/logout")
def logout(response:Response):
    response.delete_cookie(cookie_name,path="/")
    return {"ok":True}

@router.get("/me",response_model=userout)
def me(row:user=Depends(current_user)):
    return row
