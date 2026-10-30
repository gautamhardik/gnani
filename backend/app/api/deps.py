from typing import Any, Dict
from fastapi import Depends
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.core.security import verify_merchant_token

def get_current_merchant(auth: Dict[str, Any] = Depends(verify_merchant_token)) -> Dict[str, Any]:
    return auth
