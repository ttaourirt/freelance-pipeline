"""Scoring des offres : mots-cles d'abord, LLM si disponible."""
from __future__ import annotations

import re

from . import llm
from .config import Config

RED_FLAG_PATTERNS = [
    (r"\bunpaid\b", "non paye"),
    (r"\bequity only\b", "equity seule"),
    (r"\bcommission only\b", "commission seule"),
    (r"\bcrypto\b|\bweb3\b|\bnft\b", "crypto (souvent non solvable)"),
    (r"\bno experience (?:needed|required)\b", "aucune experience demandee"),
    (r"\bunpaid (?:test|trial)\b", "test non paye"),
    (r"\b\d+\s*(?:hours?|hrs?)\s*(?:unpaid|free)\b", "travail gratuit"),
    (r"\bmust be (?:based|located) in the (?:us|usa|united states)\b", "restriction geographique"),
]

TECH_TERMS = [
    # anglais
    "python", "automation", "automate", "scraping", "scraper", "api", "etl",
    "backend", "frontend", "web", "django", "flask", "fastapi", "node", "react",
    "sql", "postgres", "dashboard", "integration", "script", "bot", "data",
    # francais (les offres Codeur sont en FR)
    "developpeur", "développeur", "developpement", "développement", "automatisation",
    "automatiser", "donnees", "données", "base de donnees", "base de données",
    "site internet", "site web", "application", "logiciel", "migration", "refonte",
    "maintenance", "integration", "intégration", "tableau de bord", "reporting",
    "symfony", "wordpress", "shopify", "flutter", "serveur", "sauvegarde",
    "extraction", "formulaire", "crm", "erp", "api rest",
]

# Metiers qui n'ont rien a voir avec l'offre : a moins d'etre explicitement dans les skills
OFF_DOMAIN_TITLE = [
    "designer", "copywriter", "accountant", "legal", "recruiter", "nurse",
    "teacher", "sales representative", "marketing manager", "product manager",
    "finance manager", "operations specialist", "customer support",
    "data entry", "virtual assistant", "translator", "video editor",
]


def _blob(offer) -> tuple[str, str]:
    if isinstance(offer, dict):
        title = f"{offer.get('title','')} {offer.get('tags','')}".lower()
        desc = (offer.get("description", "") or "").lower()
        kind = offer.get("job_type", "")
    else:
        title = f"{offer['title'] or ''} {offer['tags'] or ''}".lower()
        desc = (offer["description"] or "").lower()
        kind = offer["job_type"] or ""
    return title, f"{title} {desc}", kind


def keyword_score(offer, cfg: Config) -> dict:
    title_blob, full_blob, kind = _blob(offer)
    reasons: list[str] = []
    red_flags: list[str] = []

    skills = [s.lower() for s in cfg.profile.skills]
    title_hits = [s for s in skills if s in title_blob]
    desc_hits = [s for s in skills if s in full_blob and s not in title_hits]
    tech_hits = [t for t in TECH_TERMS if t in title_blob]

    # Le titre decide : sans signal technique ou metier, l'offre n'est pas pour nous.
    relevant = bool(title_hits or tech_hits or desc_hits)
    off_domain = [w for w in OFF_DOMAIN_TITLE if w in title_blob]

    score = 20
    if kind == "outreach":
        score += 35
        reasons.append("prospect direct que tu as identifie")
    elif kind in {"contract", "freelance"}:
        score += 25
        reasons.append("mission freelance / contrat")
    elif kind == "full_time":
        score -= 30
        red_flags.append("temps plein")

    if title_hits:
        score += min(35, len(title_hits) * 12)
        reasons.append("competences dans le titre: " + ", ".join(title_hits[:4]))
    if tech_hits:
        score += min(15, len(tech_hits) * 5)
        reasons.append("technique: " + ", ".join(tech_hits[:4]))
    if desc_hits:
        score += min(8, len(desc_hits) * 2)

    if re.search(r"\bfixed[- ]price|\bfixed budget|\bproject[- ]based|\bper (?:task|project)\b", full_blob):
        score += 10
        reasons.append("budget au forfait / a la tache")
    if re.search(r"\bmvp\b|\bprototype\b|\bsmall\b|\bshort[- ]term\b", full_blob):
        score += 5
        reasons.append("perimetre court")

    if off_domain and not title_hits:
        score -= 35
        red_flags.append("metier hors domaine: " + off_domain[0])

    for pattern, label in RED_FLAG_PATTERNS:
        if re.search(pattern, full_blob):
            score -= 30
            red_flags.append(label)

    salary = (offer.get("salary", "") if isinstance(offer, dict) else offer["salary"]) or ""
    if "/year" in salary.lower() or "annual" in salary.lower():
        score -= 15
        red_flags.append("salaire annuel = poste salarie, pas une mission")

    if not relevant and (offer.get("source", "") if isinstance(offer, dict) else offer["source"]) != "manual":
        score = min(score, 30)
        reasons.append("aucun signal technique dans le titre")

    score = max(0, min(100, score))
    verdict = "apply" if score >= 70 else ("maybe" if score >= 50 else "skip")
    return {
        "score": score, "verdict": verdict, "reasons": reasons or ["peu de correspondance"],
        "red_flags": red_flags, "angle": "", "provider": "keywords",
    }


SYSTEM = (
    "You screen freelance job offers for a solo developer. "
    "You are blunt and realistic. You never inflate a score. "
    "Reply with JSON only."
)


def llm_score(offer, cfg: Config) -> dict:
    p = cfg.profile
    text = offer if isinstance(offer, dict) else dict(offer)
    prompt = f"""FREELANCER PROFILE
Positioning: {p.positioning}
Skills: {', '.join(p.skills)}
Rate: {p.rate}
Languages: {', '.join(p.languages)}
Timezone: {p.timezone}
Portfolio: {', '.join(p.portfolio) or 'none yet'}

OFFER
Title: {text.get('title','')}
Company: {text.get('company','')}
Type: {text.get('job_type','')}
Location: {text.get('location','')}
Salary: {text.get('salary','')}
Tags: {text.get('tags','')}
Description:
{(text.get('description','') or '')[:2500]}

SCORING RULES
- 100 = perfect fit: small scoped contract, matches stack, pays for a 500-900 EUR fixed price project.
- Penalise heavily: full-time employment, US-only, on-site, 6+ month engagements, huge scope,
  unpaid tests, equity/commission only, crypto speculation, "senior 10 years" requirements.
- Be honest about the user's lack of a portfolio.
- The angle must be one concrete thing the freelancer can offer in the first message, grounded
  in the offer text. Never invent experience, clients, or numbers.

Reply exactly:
{{"score": 0-100, "verdict": "apply|maybe|skip", "reasons": ["..."],
  "red_flags": ["..."], "angle": "one sentence in English, max 25 words"}}"""
    data = llm.chat_json(prompt, SYSTEM, cfg)
    score = int(data.get("score", 0))
    return {
        "score": max(0, min(100, score)),
        "verdict": data.get("verdict", "maybe"),
        "reasons": [str(r) for r in data.get("reasons", [])][:6],
        "red_flags": [str(r) for r in data.get("red_flags", [])][:6],
        "angle": str(data.get("angle", "")),
        "provider": llm.resolve_provider(cfg),
    }


def score_offer(offer, cfg: Config) -> dict:
    if llm.resolve_provider(cfg) == "offline":
        return keyword_score(offer, cfg)
    try:
        return llm_score(offer, cfg)
    except llm.LLMError as exc:
        result = keyword_score(offer, cfg)
        result["reasons"].append(f"LLM indisponible ({exc})")
        return result
