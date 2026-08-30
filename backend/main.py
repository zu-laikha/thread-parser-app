import json
import os
import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl
from google import genai
from google.genai import types

load_dotenv()

app = FastAPI(title="Thread Link Summarizer API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8081",
        "http://127.0.0.1:8081",
        "http://localhost:8082",
        "http://127.0.0.1:8082",
        "http://192.168.100.95:8081",
        "http://192.168.100.95:8082",
        "exp://192.168.100.95:8081",
        "exp://192.168.100.95:8082",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
    image_url: str = ""
    image_urls: list[str] = []


URL_CACHE: dict[str, ParsedPost] = {}


@app.get("/health")
def health_check():
    return {"status": "ok"}


def is_threads_url(url: str) -> bool:
    hostname = (urlparse(url).hostname or "").lower()
    return hostname in {"threads.net", "www.threads.net", "threads.com", "www.threads.com"}


def normalize_threads_url(url: str) -> str:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if hostname not in {"threads.net", "www.threads.net", "threads.com", "www.threads.com"}:
        return url

    if "/share/" in parsed.path.lower():
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ThreadLinkSummarizer/1.0)"},
                timeout=15,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            canonical = soup.find("link", rel="canonical")
            if canonical and canonical.get("href"):
                canonical_url = canonical.get("href").strip()
                if canonical_url.startswith("http"):
                    return canonical_url
        except Exception:
            pass

    return url


def looks_like_generic_threads_text(value: str) -> bool:
    if not value:
        return True

    cleaned = re.sub(r"\s+", " ", value).strip()
    if not cleaned:
        return True

    lower = cleaned.lower()
    if lower in {"n/a", "na", "🙌", "👍", "👌", "❤️", "😄", "🎉", "thread", "threads", "threads post", "threads page"}:
        return True
    if "threads post" in lower or "thread" in lower and "post" in lower:
        return True
    if cleaned.startswith("@") and "threads" in lower:
        return True
    return False


def choose_image_urls(soup: BeautifulSoup) -> list[str]:
    image_candidates = []
    for tag in soup.find_all("meta"):
        property_name = (tag.get("property") or tag.get("name") or "").lower()
        content = (tag.get("content") or "").strip()
        if property_name in {"og:image", "og:image:url", "twitter:image", "twitter:image:src"} and content.startswith("http"):
            image_candidates.append(content)

    for tag in soup.find_all("img"):
        src = tag.get("src") or tag.get("data-src") or ""
        if src.startswith("http"):
            image_candidates.append(src)

    unique_images = []
    seen = set()
    for image_url in image_candidates:
        if image_url not in seen:
            seen.add(image_url)
            unique_images.append(image_url)
    return unique_images


def ocr_image_text(image_url: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "replace_with_your_gemini_api_key":
        return ""

    try:
        image_response = requests.get(image_url, timeout=20)
        image_response.raise_for_status()
        content_type = image_response.headers.get("Content-Type", "image/jpeg")
        if not image_response.content:
            return ""

        client = genai.Client(api_key=api_key)
        image_part = types.Part.from_bytes(data=image_response.content, mime_type=content_type)
        prompt = "Read every visible word in this image. If it is a sale or catalogue, extract the products, prices, dates, and location exactly as shown. Return only the extracted text."
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[image_part, prompt],
        )
        return (response.text or "").strip()
    except Exception:
        return ""


def extract_post_text_from_html(html: str, original_url: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    metadata = {}
    for tag in soup.find_all("meta"):
        property_name = tag.get("property") or tag.get("name")
        content = tag.get("content")
        if property_name and content:
            metadata[property_name.lower()] = content.strip()

    title = metadata.get("og:title", "")
    description = metadata.get("og:description", "")
    text_parts = [part for part in (title, description) if part]
    image_urls = choose_image_urls(soup)

    has_generic_text = any(looks_like_generic_threads_text(part) for part in text_parts)
    if not has_generic_text:
        return "\n".join(text_parts), image_urls

    if not image_urls:
        cleaned_text = "\n".join(part for part in text_parts if part and not looks_like_generic_threads_text(part))
        return cleaned_text or "\n".join(text_parts), image_urls

    primary_image = image_urls[0]
    ocr_text = ocr_image_text(primary_image)
    if not ocr_text:
        cleaned_text = "\n".join(part for part in text_parts if part and not looks_like_generic_threads_text(part))
        return cleaned_text or "\n".join(text_parts), image_urls

    text_bits = [part for part in text_parts if part and not looks_like_generic_threads_text(part)]
    text_bits.append(ocr_text)
    return "\n".join(bit for bit in text_bits if bit).strip(), image_urls


def fetch_open_graph(url: str) -> tuple[str, list[str]]:
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ThreadLinkSummarizer/1.0)"},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        raise HTTPException(status_code=502, detail=f"Could not fetch the Threads post: {error}") from error

    text, image_urls = extract_post_text_from_html(response.text, url)
    if not text:
        raise HTTPException(status_code=422, detail="The Threads page did not contain readable text or image OCR data.")
    return text, image_urls


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


def summarize_with_gemini(text: str, original_url: str, image_urls: list[str] | None = None) -> ParsedPost:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "replace_with_your_gemini_api_key":
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured in backend/.env.")

    image_list = image_urls or []
    prompt = f"""Extract structured information from this Threads post.
Return only JSON matching the supplied schema. Use \"N/A\" when a value is unavailable.
Choose a broad category such as Property, Promo, Free Course, Review, Event, Job,
Product, Service, Food, Travel, or General. Use a specific subcategory when possible.
If this is a grocery sale, promotion, or catalogue flyer, classify it as category=\"Promo\"
with subcategory=\"Groceries\". Do not classify a property listing as Promo unless it
explicitly advertises a discount or special deal. Use General only when no category reasonably applies.

Threads URL: {original_url}
Image URLs: {', '.join(image_list) if image_list else 'N/A'}
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
        data["image_url"] = (image_urls or [""])[0]
        data["image_urls"] = image_urls or []
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

    normalized_url = normalize_threads_url(original_url)
    cached = URL_CACHE.get(normalized_url)
    if cached is not None:
        return cached

    post_text, image_urls = fetch_open_graph(normalized_url)
    parsed = summarize_with_gemini(post_text, normalized_url, image_urls)
    URL_CACHE[normalized_url] = parsed
    return parsed
