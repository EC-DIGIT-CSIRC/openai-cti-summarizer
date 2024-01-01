"""Main FastAPI file. Provides the app WSGI entry point."""
import os
import sys
import json

import uvicorn
from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import markdown

from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv, find_dotenv

from summarizer import Summarizer
# from settings import Settings
from auth import get_current_username
from distutils.util import strtobool


from settings import log


# first get the env parametting
if not load_dotenv(find_dotenv(), verbose=True, override=False):     # read local .env file
    log.warning("Could not find .env file! Assuming ENV vars work")

try:
    VERSION = open('../VERSION.txt', encoding='utf-8').readline().rstrip('\n')
except Exception as e:
    log.error("could not find VERSION.txt, bailing out.")
    sys.exit(-1)


app = FastAPI(version=VERSION)
templates = Jinja2Templates(directory="/templates")
app.mount("/static", StaticFiles(directory="/static"), name="static")
GO_AZURE = False    # default
OUTPUT_JSON = bool(strtobool(os.getenv('OUTPUT_JSON', 'false'))) 
DRY_RUN = bool(strtobool(os.getenv('DRY_RUN', 'false')))


# First detect if we should invoke OpenAI via MS Azure or directly
try:
    GO_AZURE = bool(strtobool(os.getenv('USE_MS_AZURE', 'false')))
except Exception as e:
    log.warning(f"Could not read 'USE_MS_AZURE' env var. Reason: '{str(e)}'. Reverting to false.")
    GO_AZURE = False


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if 'X-Forwarded-Proto' in request.headers and request.headers['X-Forwarded-Proto'] == 'https':
            request.scope['scheme'] = 'https'
        response = await call_next(request)
        return response


app.add_middleware(HTTPSRedirectMiddleware)

summarizer = Summarizer(go_azure=GO_AZURE, model='gpt-4-1106-preview', max_tokens=8192, output_json=OUTPUT_JSON)


async def fetch_text_from_url(url: str) -> str:
    """Fetch the text behind url and try to extract it via beautiful soup.
    Returns text or raises an exception.
    """
    parsed_url = urlparse(url)
    if not all([parsed_url.scheme, parsed_url.netloc]):
        raise ValueError("Invalid URL")

    response = requests.get(url, timeout=5)
    soup = BeautifulSoup(response.text, 'html.parser')
    text = soup.get_text()
    return text


@app.get("/", response_class=HTMLResponse)
def get_index(request: Request, username: str = Depends(get_current_username)):
    """Return the default page."""
    return templates.TemplateResponse("index.html", {"request": request, "system_prompt": os.environ['SYSTEM_PROMPT'], "username": username})


@app.post("/", response_class=HTMLResponse)
async def index(request: Request, text: str = Form(None), url: str = Form(None),
                system_prompt: str = Form(None), model: str = Form('gpt-4'), token_count: int = Form(100),
                username: str = Depends(get_current_username)):
    """HTTP POST method for the default page. This gets called when the user already HTTP POSTs a text which should be summarized."""

    if not url and not text:
        error = "Expected either url field or text field. Please specify one at least."
        result = None
        return templates.TemplateResponse("index.html", {"request": request, "text": text, "system_prompt": system_prompt, "result": error, "success": False, "username": username}, status_code=400)

    summarizer.model = model
    summarizer.max_tokens = token_count

    if url:
        # go and fetch it
        try:
            text = await fetch_text_from_url(url)
        except Exception as ex:
            return templates.TemplateResponse("index.html", {"request": request, "text": url, "system_prompt": system_prompt, "result": f"Could not fetch URL. Reason {str(ex)}", "success": False}, status_code=400)

    if DRY_RUN:
        result = "This is a sample response, we are in dry-run mode. We don't want to waste money for querying the API."
        error = None
    else:
        result, error = summarizer.summarize(text, system_prompt)

    if error:
        return templates.TemplateResponse("index.html", {"request": request, "text": text, "system_prompt": system_prompt, "result": error, "success": False, "username": username}, status_code=400)

    result = markdown.markdown(result)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "text": text,
        "system_prompt": system_prompt,
        "result": result,
        "success": True,
        "model": model,
        "username": username,
        "token_count": token_count})


if __name__ == "__main__":
    uvicorn.run('main:app', host="localhost", port=9999, reload=True)
