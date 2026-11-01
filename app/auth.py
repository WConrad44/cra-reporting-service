from fastapi import Header, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi import Security

from .config import API_TOKEN

bearer = HTTPBearer(auto_error=False)


def require_token(credentials: HTTPAuthorizationCredentials | None = Security(bearer)) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer" or credentials.credentials != API_TOKEN:
        raise HTTPException(status_code=401, detail="Missing or invalid bearer token")
    return credentials.credentials


def require_actor(x_actor: str | None = Header(default=None, alias="X-Actor")) -> str:
    if not x_actor or not x_actor.strip():
        raise HTTPException(status_code=400, detail="X-Actor header is required")
    actor = x_actor.strip()
    if len(actor) > 200:
        raise HTTPException(status_code=400, detail="X-Actor must be at most 200 characters")
    return actor
