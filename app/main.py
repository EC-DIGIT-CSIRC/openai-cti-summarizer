import uvicorn
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from .summarizer import Summarizer
from .settings import Settings

settings = Settings()

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

summarizer = Summarizer(API_KEY=settings.OPENAI_API_KEY, model='gpt-4', max_tokens=100)

@app.get("/", response_class=HTMLResponse)
def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "api_key": settings.OPENAI_API_KEY})

@app.post("/", response_class=HTMLResponse)
async def index(request: Request, text: str = Form(...), API_KEY: str = Form(None), model: str = Form('gpt-4'), word_count: int = Form(100)):
    if API_KEY:
        summarizer.API_KEY = API_KEY
    else:
        summarizer.API_KEY = settings.OPENAI_API_KEY

    summarizer.model = model
    summarizer.max_tokens = word_count

    if settings.DRY_RUN:
        result = "This is a sample response, we are in dry-run mode. We don't want to waste money for querying the API."
        error = None
    else:
        result, error = summarizer.summarize(text)

    if error:
        return templates.TemplateResponse("index.html", {"request": request, "result": error, "success": False}, status_code=400)
    
    return templates.TemplateResponse("index.html", {"request": request, "result": result, "success": True, "api_key": summarizer.API_KEY, "model": model, "word_count": word_count})

if __name__ == "__main__":
    uvicorn.run('main:app', host="localhost", port=9999, reload=True)
