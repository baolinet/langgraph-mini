# main.py - FastAPI 应用入口
import logging

from fastapi import FastAPI

from src.webapp.routers import router

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="LangGraph FastAPI Agent")
app.include_router(router)
