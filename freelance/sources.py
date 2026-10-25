"""Recuperation des offres depuis des API publiques (aucun scraping interdit)."""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone

import requests

USER_AGENT = "freelance-pipeline/0.1 (usage personnel)"
TIMEOUT = 30


def _clean(raw: str, limit: int = 4000) -> str:
    if not raw:
        return ""
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(p|div|li|h\d)>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip()[:limit]


def _norm_type(value: str) -> str:
    v = (value or "").strip().lower()
    v = v.replace(" ", "").replace("-", "").replace("_", "")
    mapping = {
        "contract": "contract",
        "contractor": "contract",
        "freelance": "freelance",
        "fulltime": "full_time",
        "parttime": "part_time",
        "temporary": "contract",
        "internship": "internship",
        "intern": "internship",
        "unknown": "unknown",
        "": "unknown",
    }
    return mapping.get(v, v)


def _get(url: str, **params) -> requests.Response:
    resp = requests.get(
        url, params=params, headers={"User-Agent": USER_AGENT}, timeout=TIMEOUT
    )
    resp.raise_for_status()
    return resp


def fetch_remotive(limit: int = 150) -> list[dict]:
    data = _get("https://remotive.com/api/remote-jobs", limit=limit).json()
    offers = []
    for job in data.get("jobs", []):
        offers.append(
            {
                "source": "remotive",
                "external_id": str(job.get("id")),
                "title": job.get("title", ""),
                "company": job.get("company_name", ""),
                "url": job.get("url", ""),
                "job_type": _norm_type(job.get("job_type", "")),
                "location": job.get("candidate_required_location", ""),
                "salary": job.get("salary", ""),
                "tags": ", ".join(job.get("tags", []) or []),
                "description": _clean(job.get("description", "")),
                "published_at": job.get("publication_date", ""),
            }
        )
    return offers


def fetch_himalayas(limit: int = 100) -> list[dict]:
    """L'API plafonne a 20 resultats par page : on pagine avec offset."""
    offers: list[dict] = []
    page_size = 20
    offset = 0
    while offset < limit:
        data = _get("https://himalayas.app/jobs/api", limit=page_size, offset=offset).json()
        batch = data.get("jobs", [])
        if not batch:
            break
        for job in batch:
            micro = job.get("pubDate")
            published = ""
            if micro:
                try:
                    published = datetime.fromtimestamp(int(micro), tz=timezone.utc).isoformat()
                except (ValueError, OSError):
                    published = ""
            offers.append(
                {
                    "source": "himalayas",
                    "external_id": str(job.get("guid") or job.get("applicationLink") or job.get("title")),
                    "title": job.get("title", ""),
                    "company": job.get("companyName", ""),
                    "url": job.get("applicationLink") or job.get("guid", ""),
                    "job_type": _norm_type(job.get("employmentType", "")),
                    "location": ", ".join(job.get("locationRestrictions", []) or []),
                    "salary": _himalayas_salary(job),
                    "tags": ", ".join(job.get("parentCategories", []) or []),
                    "description": _clean(job.get("description") or job.get("excerpt") or ""),
                    "published_at": published,
                }
            )
        offset += page_size
    return offers


def _himalayas_salary(job: dict) -> str:
    low, high = job.get("minSalary"), job.get("maxSalary")
    if not low or low == "None":
        return ""
    if high and high != "None":
        return f"{low}-{high} {job.get('currency', '')} {job.get('salaryPeriod', '')}".strip()
    return f"{low} {job.get('currency', '')} {job.get('salaryPeriod', '')}".strip()


def fetch_remoteok(limit: int = 120) -> list[dict]:
    data = _get("https://remoteok.com/api").json()
    offers = []
    for job in data:
        if not isinstance(job, dict) or "position" not in job:
            continue  # premier element = mention legale
        tags = job.get("tags", []) or []
        description = _clean(job.get("description", ""))
        job_type = "unknown"
        lowered = f"{job.get('position','')} {description}".lower()
        if re.search(r"\b(contract|freelance|contractor)\b", lowered):
            job_type = "contract"
        elif re.search(r"\bfull[- ]?time\b", lowered):
            job_type = "full_time"
        salary = ""
        if job.get("salary_min"):
            salary = f"{job['salary_min']}-{job.get('salary_max', '')} USD/year"
        offers.append(
            {
                "source": "remoteok",
                "external_id": str(job.get("id") or job.get("slug")),
                "title": job.get("position", ""),
                "company": job.get("company", ""),
                "url": job.get("url", ""),
                "job_type": job_type,
                "location": job.get("location", "") or "Remote",
                "salary": salary,
                "tags": ", ".join(tags),
                "description": description,
                "published_at": job.get("date", ""),
            }
        )
        if len(offers) >= limit:
            break
    return offers


FETCHERS = {
    "remotive": fetch_remotive,
    "himalayas": fetch_himalayas,
    "remoteok": fetch_remoteok,
}


def fetch_all(sources: list[str], log=print) -> list[dict]:
    collected: list[dict] = []
    for name in sources:
        fetcher = FETCHERS.get(name)
        if not fetcher:
            log(f"  source inconnue: {name}")
            continue
        try:
            batch = fetcher()
            log(f"  {name}: {len(batch)} offres")
            collected.extend(batch)
        except (requests.RequestException, ValueError) as exc:
            log(f"  {name}: echec ({exc})")
    return collected
