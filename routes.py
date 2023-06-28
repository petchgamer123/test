from fastapi import APIRouter, FastAPI, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware import MiddlewareStack
from starlette.requests import Request as StarletteRequest
from google.oauth2 import id_token
from google.auth.transport import requests
from functools import wraps

app = FastAPI()
Router = APIRouter()
app.add_middleware(MiddlewareStack, SessionMiddleware, secret_key="dVu9jfC1PPVGRkq-X5nKaP_vDHC63CxQ2K4W0QVpFJo", session_cookie="user_session")

client_secrets_file = "client_secret.json"

GOOGLE_CLIENT_ID = "642643535438-mm2947mq2360qr4429tmcjec7lje530j.apps.googleusercontent.com"
flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/userinfo.email openid"],
    redirect_uri="https://test-wqve.onrender.com/callback"
)


def login_is_required(func):
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if "google_id" not in request.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Login required")
        return await func(request, *args, **kwargs)
    return wrapper


@app.get("/google/login")
async def login(request: StarletteRequest):
    authorization_url, state = flow.authorization_url()
    request.session["state"] = state
    return RedirectResponse(authorization_url)


@app.get("/callback")
@login_is_required
async def callback(request: StarletteRequest):
    flow.fetch_token(authorization_response=str(request.url))

    if not request.session["state"] == request.query_params["state"]:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="State does not match!")

    credentials = flow.credentials
    request_session = requests.RequestsSession()
    cached_session = requests.session.CachedSession(request_session)
    token_request = requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials.id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    request.session["google_id"] = id_info.get("sub")
    request.session["name"] = id_info.get("name")
    return RedirectResponse("/protected_area")


@app.get("/logout")
@login_is_required
async def logout(request: StarletteRequest):
    request.session.clear()
    return RedirectResponse("/")


@app.get("/protected_area")
@login_is_required
async def protected_area(request: StarletteRequest):
    return f"Hello {request.session['name']}! <br/> <a href='/logout'><button>Logout</button></a>"


@app.get("/")
async def index():
    return "Hello World <a href='/google/login'><button>Login</button></a>"
