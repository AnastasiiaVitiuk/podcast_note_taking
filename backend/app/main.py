from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router

app = FastAPI(title="Podcast Note Taking API")

# connecting to frondend
app.add.middleware(
    CORSMiddleware, 
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

