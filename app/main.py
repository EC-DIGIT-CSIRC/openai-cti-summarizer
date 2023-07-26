import uvicorn
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import markdown

from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

from app.summarizer import Summarizer
from app.settings import Settings
from app.auth import get_current_username


settings = Settings()
print(settings)

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


# First detect if we should invoke OpenAI via MS Azure or directly
try:
    go_azure = settings.USE_MS_AZURE
except Exception as e:
    go_azure = False


summarizer = Summarizer(API_KEY=settings.OPENAI_API_KEY, go_azure=go_azure, model='gpt-3.5-turbo-16k', max_tokens=500)


async def fetch_text_from_url(url: str) -> str:
    """Fetch the text behind url and try to extract it via beautiful soup.
    Returns text or raises an exception.
    """
    parsed_url = urlparse(url)
    if not all([parsed_url.scheme, parsed_url.netloc]):
        raise ValueError("Invalid URL")

    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text()
    return text


@app.get("/", response_class=HTMLResponse)
def get_index(request: Request, username: str = Depends(get_current_username)):
    return templates.TemplateResponse("index.html", {"request": request, "api_key": settings.OPENAI_API_KEY, "system_prompt": settings.SYSTEM_PROMPT})


@app.post("/", response_class=HTMLResponse)
async def index(request: Request, text: str = Form(None), url: str = Form(None), API_KEY: str = Form(None), system_prompt: str = Form(None), model: str = Form('gpt-4'), word_count: int = Form(100), username: str = Depends(get_current_username)):
    if API_KEY:
        summarizer.API_KEY = API_KEY
    else:
        summarizer.API_KEY = settings.OPENAI_API_KEY

    if not url and not text:
        error = "Expected either url field or text field. Please specify one at least."
        result = None
        return templates.TemplateResponse("index.html", {"request": request, "text": text, "system_prompt": system_prompt, "result": error, "success": False}, status_code=400)

    summarizer.model = model
    summarizer.max_tokens = word_count

    if url:
        # go and fetch it
        try:
            text = await fetch_text_from_url(url)
        except Exception as ex:
            return templates.TemplateResponse("index.html", {"request": request, "text": url, "system_prompt": system_prompt, "result": f"Could not fetch URL. Reason {str(ex)}", "success": False}, status_code=400)


    if settings.DRY_RUN:
        result = "This is a sample response, we are in dry-run mode. We don't want to waste money for querying the API."
        error = None
    else:
        result, error = summarizer.summarize(text, system_prompt)

    if error:
        return templates.TemplateResponse("index.html", {"request": request, "text": text, "system_prompt": system_prompt, "result": error, "success": False}, status_code=400)

    result = markdown.markdown(result)
    return templates.TemplateResponse("index.html", {"request": request, "text": text, "system_prompt": system_prompt, "result": result, "success": True, "api_key": summarizer.API_KEY, "model": model, "word_count": word_count})


if __name__ == "__main__":
    uvicorn.run('main:app', host="localhost", port=9999, reload=True)
