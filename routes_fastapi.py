from fastapi import APIRouter, FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import Middleware
from starlette.requests import Request as StarletteRequest
from google.oauth2 import id_token
from google.auth.transport import requests
import requests
import os
from pathlib import Path

from db import collection_account

app = FastAPI()
Router = APIRouter()

app.add_middleware(SessionMiddleware, secret_key="dVu9jfC1PPVGRkq-X5nKaP_vDHC63CxQ2K4W0QVpFJo", session_cookie="user_session")

client_secrets_file = "client_secret.json"

GOOGLE_CLIENT_ID = "642643535438-mm2947mq2360qr4429tmcjec7lje530j.apps.googleusercontent.com"
flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="https://fastapi-ytfv.onrender.com/google/callback"
)

def login_is_required(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if "google_id" not in request.session:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
        return await func(request, *args, **kwargs)
    return wrapper

@app.get("/google/login")
async def login(request: StarletteRequest):
    authorization_url, state = flow.authorization_url()
    request.session["state"] = state
    return RedirectResponse(authorization_url)

@app.get("/google/callback")
async def callback(request: StarletteRequest):
    flow.fetch_token(authorization_response=str(request.url))

    if not request.session["state"] == request.query_params["state"]:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="State does not match!")

    credentials = flow.credentials
    request_session = requests.Session()
    token_request = google.auth.transport.requests.Request(session=request_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials.id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    request.session["google_id"] = id_info.get("sub")
    request.session["name"] = id_info.get("name")

    if(collection_account.find_one({"sub": id_info.get("sub")}) is None):
        user = collection_account.insert_one(id_info)

    return RedirectResponse("localhost:4200/login/callback")


# @app.get("/logout")
# async def logout(request: StarletteRequest):
#     request.session.clear()
#     return RedirectResponse("/")

# @app.get("/protected_area")
# async def protected_area(request: StarletteRequest):
#     return f"Hello {request.session['name']}! <br/> <a href='/logout'><button>Logout</button></a>"


@app.get("/")
async def index():
    return "Hello World <a href='/login'><button>Login</button></a>"

