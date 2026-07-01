from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
import os

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

@router.post("/login")
async def login(credentials: LoginRequest):
    auth_username = os.getenv("AUTH_USERNAME")
    auth_password = os.getenv("AUTH_PASSWORD")
    api_token = os.getenv("API_TOKEN")

    if not auth_username or not auth_password or not api_token:
        # If not configured, deny access or handle graceful failure
        raise HTTPException(status_code=500, detail="Authentication not configured properly in .env")

    if credentials.username == auth_username and credentials.password == auth_password:
        return {"token": api_token}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

@router.get("/token")
async def get_token(authorization: str = Header(None)):
    """Returns the token if the user is authenticated (used by Settings UI)."""
    api_token = os.getenv("API_TOKEN")
    
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")
        
    token = authorization.split(" ")[1]
    if token != api_token:
        raise HTTPException(status_code=401, detail="Invalid token")
        
    return {"token": api_token}

from fastapi import Query

def verify_token(authorization: str = Header(None), token: str = Query(None)):
    api_token = os.getenv("API_TOKEN")
    if not api_token:
        raise HTTPException(status_code=500, detail="API Token not configured")
        
    provided_token = None
    if authorization and authorization.startswith("Bearer "):
        provided_token = authorization.split(" ")[1]
    elif token:
        provided_token = token
        
    if not provided_token:
        raise HTTPException(status_code=401, detail="Missing or invalid token")
        
    if provided_token != api_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    return provided_token
