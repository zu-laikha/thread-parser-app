import json
import os
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from google import genai
from google.genai import types

load_dotenv()

app = FastAPI(title="Thread Link Summarizer API")


class ParseRequest(BaseModel):
    url: HttpUrl


class ParsedPost(BaseModel):
    category: str
    subcategory: str
    title: str
    brand_or_creator: str
    location: str
    dates_or_validity: str
    key_highlights: list[str]
    original_url: str


@app.get("/health")
def health_check():
    return {"status": "ok"}


def is_threads_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return hostname in {"threads.net", "www.threads.net", "threads.com", "www.threads.com"}


def fetch_open_graph(url: str) -> str:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ThreadLinkSummarizer/1.0)"},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail=f"Could not fetch the Threads post: {error}") from error

    soup = BeautifulSoup(response.text, "html.parser")
    metadata = {}
    for tag in soup.find_all("meta"):
        property_name = tag.get("property") or tag.get("name")
        content = tag.get("content")
        if property_name and content and property_name in {"og:title", "og:description"}:
            metadata[property_name] = content.strip()

    title = metadata.get("og:title", "")
    description = metadata.get("og:description", "")
    text = "\n".join(value for value in (title, description) if value)
    if not text:
        raise HTTPException(status_code=422, detail="The Threads page did not contain readable Open Graph text.")
    return text


def parse_gemini_json(response_text: str | None) -> dict:
    if not response_text:
        raise ValueError("Gemini returned an empty response.")

    cleaned_text = response_text.strip()
    if cleaned_text.startswith("```"):
        cleaned_text = cleaned_text.removeprefix("```").removeprefix("json").removesuffix("```").strip()

    parsed = json.loads(cleaned_text)
    if not isinstance(parsed, dict):
        raise ValueError("Gemini response was not a JSON object.")
    return parsed


def summarize_with_gemini(text: str, original_url: str) -> ParsedPost:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "replace_with_your_gemini_api_key":
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured in backend/.env.")

    prompt = f"""Extract structured information from this Threads post.
Return only JSON matching the supplied schema. Use \"N/A\" when a value is unavailable.
Choose a broad category such as Property, Promo, Free Course, Review, Event, Job,
Product, Service, Food, Travel, or General. Use a specific subcategory when possible.
Do not classify a property listing as Promo unless it explicitly advertises a discount
or special deal. Use General only when no category reasonably applies.

Threads URL: {original_url}
Post text:
{text}"""

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=ParsedPost,
            ),
        )
        data = parse_gemini_json(response.text)
        data["original_url"] = original_url
        return ParsedPost.model_validate(data)
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise HTTPException(status_code=502, detail="Gemini returned an invalid structured response.") from error
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Gemini request failed: {error}") from error


@app.post("/parse", response_model=ParsedPost)
def parse_thread(request: ParseRequest):
    original_url = str(request.url)
    if not is_threads_url(original_url):
        raise HTTPException(status_code=422, detail="Only Threads URLs are supported.")

    post_text = fetch_open_graph(original_url)
    return summarize_with_gemini(post_text, original_url)
