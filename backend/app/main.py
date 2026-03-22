from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env.local"))

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
from app.db import engine, Base

app = FastAPI()

# automatically create tables on startup
Base.metadata.create_all(bind=engine)

# connecting to frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

