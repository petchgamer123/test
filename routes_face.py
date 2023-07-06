import httpx
from fastapi import APIRouter, Request, HTTPException, FastAPI
from starlette.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jose import jwt
from datetime import datetime, timedelta

from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware
from starlette.requests import Request as StarletteRequest

from dotenv import load_dotenv
import os

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
SOCIAL_AUTH_FACEBOOK_KEY = os.getenv("SOCIAL_AUTH_FACEBOOK_KEY")
SOCIAL_AUTH_FACEBOOK_SECRET = os.getenv("SOCIAL_AUTH_FACEBOOK_SECRET")

router = APIRouter()
templates = Jinja2Templates(directory="templates")
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, session_cookie="user_session")


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, "SECRET_KEY", algorithm="HS256")
    return encoded_jwt

async def fetch_facebook_user_info(access_token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://graph.facebook.com/v12.0/me",
            params={"access_token": access_token, "fields": "id,name"},
        )
        response.raise_for_status()
        return response.json()

def login_required(func):
    async def wrapper(request: Request, *args, **kwargs):
        if "user" not in request.session:
            raise HTTPException(status_code=401, detail="Login required")
        return await func(request, *args, **kwargs)
    return wrapper

@app.get('/')
async def root():
    return {"message": "Hello, World!"}

# @app.get('/Privacy')
# async def Privacy():
#     return {"message": "PrivacyPrivacyPrivacyPrivacyPrivacyPrivacyPrivacyPrivacyPrivacy"}

# @app.get('/rules')
# async def rules():
#     return {"message": "*************************   rules   *************************"}

@app.get("/logi")
def login_facebook():
    # Redirect to Facebook login
    facebook_redirect_url = "https://www.facebook.com/v12.0/dialog/oauth"
    params = {
        "client_id": SOCIAL_AUTH_FACEBOOK_KEY,
        "redirect_uri": "https://fastapi-ytfv.onrender.com/callback",
        "state": "YOUR_STATE",
        "scope": "email",  # กำหนด scope ตามความต้องการ
    }
    redirect_url = f"{facebook_redirect_url}?{'&'.join([f'{key}={value}' for key, value in params.items()])}"
    return RedirectResponse(url=redirect_url)

@app.get("/callbackk")
async def facebook_callback(request: Request, code: str, state: str):
    # ใช้ code ในการสร้าง access_token และรับข้อมูลผู้ใช้จาก Facebook
    facebook_token_url = "https://graph.facebook.com/v12.0/oauth/access_token"
    home = "https://fastapi-ytfv.onrender.com"
    params = {
        "client_id": SOCIAL_AUTH_FACEBOOK_KEY,
        "client_secret": SOCIAL_AUTH_FACEBOOK_SECRET,
        "redirect_uri": "https://fastapi-ytfv.onrender.com/callback",
        "code": code,
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(facebook_token_url, params=params)
        response.raise_for_status()
        token_data = response.json()
    
    access_token = token_data["access_token"]
    user_data = await fetch_facebook_user_info(access_token)
    request.session["user"] = user_data

    # สร้าง access token และเก็บไว้ใน session
    user_data["access_token"] = create_access_token(user_data)

    query_params = {
        "facebook_id": token_data.get("sub"),
        "name": token_data.get("name")
    }

    print(token_data)

    redirect_url = f"{home}?{'&'.join([f'{key}={value}' for key, value in query_params.items()])}"
    return RedirectResponse(url=redirect_url)
    # return {"message": "Facebook callback"}


