"""Main FastAPI file. Provides the app WSGI entry point."""
import os
import sys
import tempfile
from urllib.parse import urlparse
from distutils.util import strtobool        # pylint: disable=deprecated-module

import requests

import fitz  # PyMuPDF

import uvicorn
from fastapi import FastAPI, Request, Form, Depends, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import markdown

from bs4 import BeautifulSoup
from dotenv import load_dotenv, find_dotenv

from summarizer import Summarizer       # pylint: ignore=import-error
from auth import get_current_username   # pylint: ignore=import-error

from settings import log                # pylint: ignore=import-error


# first get the env parametting
if not load_dotenv(find_dotenv(), verbose=True, override=False):     # read local .env file
    log.warning("Could not find .env file! Assuming ENV vars work")

try:
    with open('../VERSION.txt', encoding='utf-8') as _f:
        VERSION = _f.readline().rstrip('\n')
except Exception as e:
    log.error("could not find VERSION.txt, bailing out.")
    sys.exit(-1)


app = FastAPI(version=VERSION)
templates = Jinja2Templates(directory="/templates")
app.mount("/static", StaticFiles(directory="/static"), name="static")
GO_AZURE = bool(strtobool(os.getenv('USE_AZURE', 'true')))
OUTPUT_JSON = bool(strtobool(os.getenv('OUTPUT_JSON', 'false')))
DRY_RUN = bool(strtobool(os.getenv('DRY_RUN', 'false')))
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

# First detect if we should invoke OpenAI via MS Azure or directly
try:
    GO_AZURE = bool(strtobool(os.getenv('USE_AZURE', 'false')))
except Exception as e:
    log.warning(
        f"Could not read 'USE_AZURE' env var. Reason: '{str(e)}'. Reverting to false.")
    GO_AZURE = False

# print out settings
log.info(f"{GO_AZURE=}")
log.info(f"{OUTPUT_JSON=}")
log.info(f"{DRY_RUN=}")
log.info(f"{OPENAI_MODEL=}")


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """HTTP to HTTPS redirection"""
    async def dispatch(self, request: Request, call_next):
        if 'X-Forwarded-Proto' in request.headers and request.headers['X-Forwarded-Proto'] == 'https':
            request.scope['scheme'] = 'https'
        response = await call_next(request)
        return response


app.add_middleware(HTTPSRedirectMiddleware)

summarizer = Summarizer(go_azure=GO_AZURE, model=OPENAI_MODEL,
                        max_tokens=8192, output_json=OUTPUT_JSON)


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


def convert_pdf_to_markdown(filename: str) -> str:
    """Convert a PDF file given by <filename> to markdown.

    Args:
      filename: str     the file on the filesystem

    Returns:
      markdown or "" empty string in case of error
    """
    # Open the PDF file
    doc = fitz.open(filename)

    # Initialize a variable to hold the text
    markdown_content = ""

    # Iterate through each page of the PDF
    for page_num in range(len(doc)):
        # Get the page
        page = doc.load_page(page_num)

        # Extract text from the page
        text = page.get_text()

        # Add the text to our markdown content, followed by a page break
        markdown_content += text + "\n\n---\n\n"

    return markdown_content


# The main POST method. Input can either be a URL or a PDF file or a textarea text
@app.post("/", response_class=HTMLResponse)
async def index(request: Request,           # request object
                text: str = Form(None),     # the text in the textarea
                url: str = Form(None),      # alternatively the URL
                pdffile: UploadFile = File(None),
                system_prompt: str = Form(None), model: str = Form('model'), token_count: int = Form(100),
                username: str = Depends(get_current_username)):
    """HTTP POST method for the default page. This gets called when the user already HTTP POSTs a text which should be summarized."""

    if url:
        log.warning(f"Got request with url: {url[:20]}")
    elif pdffile:
        log.warning(f"Got request with pdffile: {pdffile.filename}")
    elif text:
        log.warning(f"Got request with text: {text[:100]}")
    else:
        log.error("no pdffile, no text, no url. Bailing out.")
        error = "Expected either url field or text field or a PDF file. Please specify one at least."
        result = None
        return templates.TemplateResponse("index.html", {"request": request, "text": text, "system_prompt": system_prompt, "result": error, "success": False, "username": username}, status_code=400)

    summarizer.model = model
    summarizer.max_tokens = token_count

    if url:
        try:
            text = await fetch_text_from_url(url)
        except Exception as ex:
            return templates.TemplateResponse("index.html", {"request": request, "text": url, "system_prompt": system_prompt, "result": f"Could not fetch URL. Reason {str(ex)}", "success": False}, status_code=400)

    elif pdffile:
        log.warning("we got a pdffile")
        try:
            suffix = ".pdf"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(pdffile.file.read())
                tmp_pdf_path = tmp.name  # Temp file path
                log.warning(f"stored as {tmp_pdf_path}")

            # Convert PDF to Markdown
            text = convert_pdf_to_markdown(tmp_pdf_path)
            log.warning(f"converted as {text[:100]}")

            # Cleanup the temporary file
            os.unlink(tmp_pdf_path)
        except Exception as ex:
            return templates.TemplateResponse("index.html", {"request": request, "text": text, "system_prompt": system_prompt, "result": f"Could not process the PDF file. Reason {str(ex)}", "success": False}, status_code=400)

    # we got the text from the URL or the pdffile was converted... now check if we should actually summarize
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
