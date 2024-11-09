from fastapi import FastAPI, responses, Request
from fastapi.middleware.cors import CORSMiddleware
from api.v1.routes import chat, store
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse


app = FastAPI(
    title="docAI",
    summary="Your best document AI assistant",
    version="0.1.0",
    description="Assist users with document-based queries"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(router=store.router)
app.include_router(router=chat.router)

# @app.get("/")
# def index() -> responses.RedirectResponse:
#     return responses.RedirectResponse("/docs")

@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> dict:
    return templates.TemplateResponse("index.html", {"request": request})