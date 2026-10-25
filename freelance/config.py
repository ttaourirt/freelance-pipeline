"""Configuration : config.toml + variables d'environnement."""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv(*_a, **_k):
        return False

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
CONFIG_FILE = ROOT / "config.toml"

DEFAULT_CONFIG = """
[profile]
name = "Your Name"
email = "you@example.com"
timezone = "Europe/Paris"
languages = ["en", "fr"]
rate = "EUR 500-900 fixed price per project"
positioning = "I build small, reliable automations and tools for small teams."
skills = ["Python", "automation", "web apps", "data pipelines", "API integration"]
portfolio = []
github = ""
linkedin = ""

[filters]
sources = ["remotive", "himalayas", "remoteok"]
job_types = ["contract", "freelance", "contractor"]
allow_unknown_type = true
exclude_keywords = ["unpaid", "equity only", "commission only", "internship", "volunteer"]
min_score = 55
"""


@dataclass
class Profile:
    name: str = "Your Name"
    email: str = ""
    timezone: str = "Europe/Paris"
    languages: list[str] = field(default_factory=lambda: ["en", "fr"])
    rate: str = ""
    positioning: str = ""
    skills: list[str] = field(default_factory=list)
    portfolio: list[str] = field(default_factory=list)
    github: str = ""
    linkedin: str = ""


@dataclass
class Filters:
    sources: list[str] = field(default_factory=lambda: ["remotive", "himalayas", "remoteok"])
    job_types: list[str] = field(default_factory=lambda: ["contract", "freelance", "contractor"])
    allow_unknown_type: bool = True
    exclude_keywords: list[str] = field(default_factory=list)
    min_score: int = 55


@dataclass
class Config:
    profile: Profile
    filters: Filters
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-120b"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    provider: str = "auto"

    @classmethod
    def load(cls) -> "Config":
        load_dotenv(ROOT / ".env")
        if not CONFIG_FILE.exists():
            CONFIG_FILE.write_text(DEFAULT_CONFIG.lstrip(), encoding="utf-8")
        raw = tomllib.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        profile = Profile(**{k: v for k, v in raw.get("profile", {}).items() if k in Profile.__dataclass_fields__})
        filters = Filters(**{k: v for k, v in raw.get("filters", {}).items() if k in Filters.__dataclass_fields__})
        return cls(
            profile=profile,
            filters=filters,
            groq_api_key=os.environ.get("GROQ_API_KEY", ""),
            groq_model=os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b"),
            gemini_api_key=os.environ.get("GEMINI_API_KEY", ""),
            gemini_model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
            provider=os.environ.get("LLM_PROVIDER", "auto"),
        )

    def profile_gaps(self) -> list[str]:
        gaps = []
        if not self.profile.portfolio and not self.profile.github:
            gaps.append("aucun portfolio ni GitHub : les propositions seront faibles")
        if "example.com" in self.profile.email or not self.profile.email:
            gaps.append("email de contact non renseigne")
        if not self.profile.positioning:
            gaps.append("positionnement non renseigne")
        return gaps
