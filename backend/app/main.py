from fastapi import FastAPI, responses
from fastapi.middleware.cors import CORSMiddleware
from routes import store, chat, others


app = FastAPI(
    title="docAI",
    summary="Your best document AI assistant",
    version="0.1.0",
    description="Assist users with document-based queries"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=store.router)
app.include_router(router=chat.router)
app.include_router(router=others.router)

# redirect to auto-docs on app start
@app.get("/")
def index() -> responses.RedirectResponse:
    return responses.RedirectResponse("/docs")
