import httpx
from fastapi import APIRouter, Request, HTTPException, FastAPI
from starlette.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from jose import jwt
from datetime import datetime, timedelta
from fastapi.middleware.session import SessionMiddleware

app.add_middleware(SessionMiddleware, secret_key="dVu9jfC1PPVGRkq-X5nKaP_vDHC63CxQ2K4W0QVpFJo")

router = APIRouter()
templates = Jinja2Templates(directory="templates")
app = FastAPI()


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

@app.get("/login")
def login_facebook():
    # Redirect to Facebook login
    facebook_redirect_url = "https://www.facebook.com/v12.0/dialog/oauth"
    params = {
        "client_id": "1300273574255667",
        "redirect_uri": "https://fastapi-ytfv.onrender.com/callback",
        "state": "YOUR_STATE",
        "scope": "email",  # กำหนด scope ตามความต้องการ
    }
    redirect_url = f"{facebook_redirect_url}?{'&'.join([f'{key}={value}' for key, value in params.items()])}"
    return RedirectResponse(url=redirect_url)

@app.get("/callback")
async def facebook_callback(request: Request, code: str, state: str):
    # ใช้ code ในการสร้าง access_token และรับข้อมูลผู้ใช้จาก Facebook
    facebook_token_url = "https://graph.facebook.com/v12.0/oauth/access_token"
    params = {
        "client_id": "1300273574255667",
        "client_secret": "e7c85850d410d960ae41c6554a4c8cdd",
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

    return {"message": "Facebook callback"}

@app.get("/success", response_class=HTMLResponse)
@login_required
async def facebook_success(request: Request):
    user_data = request.session["user"]
    return templates.TemplateResponse("fb-github-success.html", {"request": request, "user": user_data})

@app.get("/error")
def facebook_error():
    return {"message": "Error logging in via Facebook"}

@app.get("/signout")
def facebook_signout(request: Request):
    request.session.clear()
    return {"message": "Sign out success"}

