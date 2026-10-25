"""Generation des propositions (message court, concret, verifiable)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from . import llm
from .config import Config, OUTPUT_DIR

SYSTEM = (
    "You write short freelance proposals that get replies. "
    "Rules: no flattery, no buzzwords, no fake experience, no invented numbers, "
    "no emoji. Short sentences. Sound like a competent human, not a salesperson. "
    "Reply with JSON only."
)


def _prompt(offer: dict, cfg: Config, score_row: dict | None) -> str:
    p = cfg.profile
    angle = (score_row or {}).get("angle") or ""
    kind = (
        "This is COLD OUTREACH to a company you found yourself, not a reply to a job post. "
        "Open with the specific thing you observed about them."
        if offer.get("source") == "manual"
        else "This is a reply to a published job post. Show you read it."
    )
    return f"""FREELANCER
Name: {p.name}
Positioning: {p.positioning}
Skills: {', '.join(p.skills)}
Rate: {p.rate}
Portfolio: {', '.join(p.portfolio) or 'none yet'}
GitHub: {p.github or 'none'}

CONTEXT
{kind}

TARGET / OFFER
Title: {offer.get('title','')}
Company: {offer.get('company','')}
URL: {offer.get('url','')}
Details:
{(offer.get('description','') or '')[:2500]}
Suggested angle: {angle or 'not provided'}

Write a message in ENGLISH, 110-150 words maximum.

Structure:
1. One line showing you understood their actual problem (reference something specific in their post).
2. What you would build first, concretely (one sentence, no jargon).
3. How you work: small steps, fixed price, you share progress.
4. One question that moves the conversation forward.

Hard rules:
- Never claim experience you were not given. If there is no portfolio, do not pretend otherwise.
- No "I am the perfect fit", no "passionate", no "cutting-edge", no "leverage".
- Do not mention the price unless the offer asks for it.
- Do not invent a client name, a metric, or a testimonial.

Also write a 1-sentence follow-up to send after 4 days if there is no reply.

Reply exactly:
{{"subject": "email subject, max 8 words",
  "message": "the proposal text",
  "first_step": "what you would deliver first, max 12 words",
  "question": "the single question you ask",
  "follow_up": "one sentence"}}"""


def _offline(offer: dict, cfg: Config) -> dict:
    title = offer.get("title", "your project")
    skills = ", ".join(cfg.profile.skills[:3])
    if offer.get("source") == "manual":
        opening = (
            f"Hi,\n\n"
            f"I had a look at {offer.get('company', 'your site')} and noticed this: "
            f"{(offer.get('description', '') or '')[:180].strip()}\n\n"
            f"That is the kind of thing I fix. I build small tools with {skills} and I work "
            f"in short steps: a working piece, then your feedback, then the next one. "
            f"Fixed price, no surprises.\n\n"
            f"Is this something you would like handled this month?\n\n"
            f"{cfg.profile.name}"
        )
    else:
        opening = (
            f"Hi,\n\n"
            f"I read your post about {title}. The part I would focus on first is the one that "
            f"blocks everything else, not the full scope.\n\n"
            f"I build small tools with {skills} and I work in short steps: a working piece, "
            f"then your feedback, then the next one. Fixed price, no surprises.\n\n"
            f"What has to work on day one for this to be useful?\n\n"
            f"{cfg.profile.name}"
        )
    return {
        "subject": f"{offer.get('company', '')} - quick question about your {title[:30]}".strip(" -"),
        "message": opening,
        "first_step": "a working proof of concept on the core case",
        "question": "What has to work on day one for this to be useful?",
        "follow_up": "Just checking in - happy to share how I would approach the first step.",
        "provider": "offline",
    }


def generate(offer: dict, cfg: Config, score_row: dict | None = None) -> dict:
    if llm.resolve_provider(cfg) == "offline":
        return _offline(offer, cfg)
    try:
        data = llm.chat_json(_prompt(offer, cfg, score_row), SYSTEM, cfg)
        data["provider"] = llm.resolve_provider(cfg)
        return data
    except llm.LLMError as exc:
        result = _offline(offer, cfg)
        result["reasons"] = [f"LLM indisponible ({exc})"]
        return result


def render(offer: dict, proposal: dict, cfg: Config, score_row: dict | None = None) -> str:
    gaps = cfg.profile_gaps()
    warnings = "\n".join(f"> - {g}" for g in gaps) if gaps else "> - aucun blocage detecte"
    red_flags = (score_row or {}).get("red_flags") or []
    flags = "\n".join(f"> - {f}" for f in red_flags) if red_flags else "> - aucun"
    return f"""# Proposition - offre #{offer.get('id')}

**{offer.get('title','')}** — {offer.get('company','')}
<{offer.get('url','')}>
Score : {(score_row or {}).get('score', '?')}/100 — {(score_row or {}).get('verdict','?')}
Genere le {datetime.now().strftime('%Y-%m-%d %H:%M')} ({proposal.get('provider','?')})

## A verifier avant d'envoyer

> - Je n'affirme rien que je n'ai pas vraiment fait
> - Le nom de l'entreprise est correct
> - J'ai repondu a UNE question concrete de l'annonce
{warnings}

## Signaux d'alerte detectes

{flags}

## Objet

{proposal.get('subject','')}

## Message

{proposal.get('message','')}

## Premier livrable propose

{proposal.get('first_step','')}

## Question posee

{proposal.get('question','')}

## Relance (J+4)

{proposal.get('follow_up','')}
"""


def save(offer: dict, proposal: dict, cfg: Config, score_row: dict | None = None) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_DIR / "proposals" / f"offer-{offer.get('id')}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(offer, proposal, cfg, score_row), encoding="utf-8")
    return path
