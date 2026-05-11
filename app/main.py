"""Main FastAPI file. Provides the app ASGI entry point."""
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

import fitz  # PyMuPDF
import markdown
import requests
import uvicorn
from bs4 import BeautifulSoup
from fastapi import Depends, FastAPI, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware

from .auth import get_current_username
from .config import AppSettings, LLMSettings
from .rendering import render_summary_markdown, summary_to_jsonable
from .schema import CTISummary
from .settings import log
from .summarizer import CTISummarizer, SummarizationError

try:
    with open(Path(__file__).resolve().parent.parent / 'VERSION.txt', encoding='utf-8') as _f:
        VERSION = _f.readline().rstrip('\n')
except Exception:
    log.error("could not find VERSION.txt, bailing out.")
    sys.exit(-1)


BASE_DIR = Path(__file__).resolve().parent.parent
app_settings = AppSettings()
llm_settings = LLMSettings()
app = FastAPI(version=VERSION)
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

log.info("llm_settings_loaded", extra={"provider": llm_settings.provider.value, "model": llm_settings.model})


def template_context(
    request: Request,
    username: str,
    *,
    text: str | None = None,
    url: str | None = None,
    system_prompt: str | None = None,
    result: str | None = None,
    success: bool | None = None,
    model: str | None = None,
    sensitivity: str | None = None,
    input_mode: str | None = None,
) -> dict:
    """Build common template context for the web UI."""
    return {
        "request": request,
        "text": text,
        "url": url,
        "system_prompt": system_prompt or app_settings.system_prompt,
        "result": result,
        "success": success,
        "username": username,
        "model": model or llm_settings.model,
        "sensitivity": sensitivity or "PA",
        "input_mode": input_mode or ("url" if url else "text"),
        "version": VERSION,
        "repo_url": "https://github.com/EC-DIGIT-CSIRC/openai-cti-summarizer",
    }


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """HTTP to HTTPS redirection"""
    async def dispatch(self, request: Request, call_next):
        if 'X-Forwarded-Proto' in request.headers and request.headers['X-Forwarded-Proto'] == 'https':
            request.scope['scheme'] = 'https'
        response = await call_next(request)
        return response


app.add_middleware(HTTPSRedirectMiddleware)


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
    return templates.TemplateResponse(
        request,
        "index.html",
        template_context(request, username),
    )


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
                system_prompt: str = Form(None), model: str = Form(None),
                sensitivity: str = Form(None), input_mode: str = Form(None),
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
        return templates.TemplateResponse(
            request,
            "index.html",
            template_context(
                request,
                username,
                text=text,
                url=url,
                system_prompt=system_prompt,
                result=error,
                success=False,
                model=model,
                sensitivity=sensitivity,
                input_mode=input_mode,
            ),
            status_code=400,
        )

    request_llm_settings = llm_settings.with_overrides(model=model)
    prompt = system_prompt or app_settings.system_prompt

    if url:
        try:
            text = await fetch_text_from_url(url)
        except Exception as ex:
            return templates.TemplateResponse(
                request,
                "index.html",
                template_context(
                    request,
                    username,
                    text=text,
                    url=url,
                    system_prompt=prompt,
                    result=f"Could not fetch URL. Reason {str(ex)}",
                    success=False,
                    model=request_llm_settings.model,
                    sensitivity=sensitivity,
                    input_mode=input_mode or "url",
                ),
                status_code=400,
            )

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
            Path(tmp_pdf_path).unlink()
        except Exception as ex:
            return templates.TemplateResponse(
                request,
                "index.html",
                template_context(
                    request,
                    username,
                    text=text,
                    url=url,
                    system_prompt=prompt,
                    result=f"Could not process the PDF file. Reason {str(ex)}",
                    success=False,
                    model=request_llm_settings.model,
                    sensitivity=sensitivity,
                    input_mode=input_mode or "file",
                ),
                status_code=400,
            )

    # we got the text from the URL or the pdffile was converted... now check if we should actually summarize
    if app_settings.dry_run:
        summary = CTISummary(
            summary="This is a sample response because DRY_RUN is enabled.",
            key_points=["No request was sent to an LLM provider."],
            ttps=[],
            indicators=[],
            threat_actors=[],
            confidence_score=1.0,
            report_metadata={"mode": "dry_run"},
            yara_rules=[],
        )
    else:
        try:
            summary = (await CTISummarizer(request_llm_settings).summarize(text, prompt)).summary
        except SummarizationError as ex:
            return templates.TemplateResponse(
                request,
                "index.html",
                {
                    "request": request,
                    "text": text,
                    "url": url,
                    "system_prompt": prompt,
                    "result": str(ex),
                    "success": False,
                    "username": username,
                    "model": request_llm_settings.model,
                    "sensitivity": sensitivity or "PA",
                    "input_mode": input_mode or ("url" if url else "text"),
                    "version": VERSION,
                    "repo_url": "https://github.com/EC-DIGIT-CSIRC/openai-cti-summarizer",
                },
                status_code=400,
            )

    if app_settings.output_json:
        return JSONResponse(summary_to_jsonable(summary))

    result = markdown.markdown(render_summary_markdown(summary), extensions=["tables", "fenced_code"])
    return templates.TemplateResponse(
        request,
        "index.html",
        template_context(
            request,
            username,
            text=text,
            url=url,
            system_prompt=prompt,
            result=result,
            success=True,
            model=request_llm_settings.model,
            sensitivity=sensitivity,
            input_mode=input_mode,
        ),
    )


if __name__ == "__main__":
    uvicorn.run('app.main:app', host="localhost", port=9999, reload=True)
