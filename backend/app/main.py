from fastapi import FastAPI, responses
from fastapi.middleware.cors import CORSMiddleware
from routes import chat, store


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

# Include routers
app.include_router(router=store.router)
app.include_router(router=chat.router)


@app.get("/")
def index() -> responses.RedirectResponse:
    return responses.RedirectResponse("/docs")
