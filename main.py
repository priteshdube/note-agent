from fastapi import FastAPI, Depends, Header, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from routes.process import router as process_router
from config import settings

app = FastAPI(title="Lecture Notes Backend")

# Configure CORS - adjust origins as needed for your Chrome extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your extension's origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["10/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# API key verification (optional)
def verify_api_key(x_api_key: str | None = Header(None)):
    """
    If settings.api_key is set, require the X-API-Key header to match it.
    If settings.api_key is None, the check is skipped (useful for local dev).
    """
    if settings.api_key is not None and x_api_key != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return x_api_key

# Include routers with dependencies
app.include_router(
    process_router,
    prefix="/api",
    dependencies=[Depends(verify_api_key)],
)

@app.get("/")
async def root():
    return {"message": "Lecture Notes Backend is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
