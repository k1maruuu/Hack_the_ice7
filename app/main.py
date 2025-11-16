from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.routers import auth_main, users, news, chat, ai
from app.database import engine
from app import models
from dotenv import load_dotenv
import os

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
limiter = Limiter(key_func=get_remote_address, default_limits=["100 per minute"]) 

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_main.router)
app.include_router(users.router)
app.include_router(ai.router)