"""Stockage SQLite + suivi du pipeline."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import DATA_DIR

DB_FILE = DATA_DIR / "pipeline.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    external_id TEXT NOT NULL,
    title TEXT, company TEXT, url TEXT, job_type TEXT, location TEXT,
    salary TEXT, tags TEXT, description TEXT, published_at TEXT,
    fetched_at TEXT,
    UNIQUE(source, external_id)
);
CREATE TABLE IF NOT EXISTS scores (
    offer_id INTEGER PRIMARY KEY REFERENCES offers(id) ON DELETE CASCADE,
    score INTEGER, verdict TEXT, reasons TEXT, red_flags TEXT, angle TEXT, scored_at TEXT
);
CREATE TABLE IF NOT EXISTS applications (
    offer_id INTEGER PRIMARY KEY REFERENCES offers(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'new',
    proposal_path TEXT,
    applied_at TEXT,
    follow_up_at TEXT,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS idx_scores_score ON scores(score DESC);
CREATE INDEX IF NOT EXISTS idx_apps_status ON applications(status);
"""


def connect() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate(conn)
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Petites migrations idempotentes, versionnees avec PRAGMA user_version."""
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < 1:
        # Les titres issus du flux RSS contenaient des entites HTML (&#39;).
        import html as _html

        rows = conn.execute("SELECT id, title FROM offers").fetchall()
        for row in rows:
            fixed = _html.unescape(row["title"] or "")
            if fixed != row["title"]:
                conn.execute("UPDATE offers SET title = ? WHERE id = ?", (fixed, row["id"]))
        conn.execute("PRAGMA user_version = 1")
        conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def offer_age_days(published_at: str) -> int | None:
    parsed = _parse_date(published_at)
    if parsed is None:
        return None
    return (datetime.now(timezone.utc) - parsed).days


def is_relevant(
    offer: dict,
    job_types: list[str],
    exclude_keywords: list[str],
    allow_unknown: bool,
    max_age_days: int = 0,
) -> tuple[bool, str]:
    kind = offer.get("job_type", "unknown")
    if kind == "unknown":
        if not allow_unknown:
            return False, "type inconnu"
    elif kind not in job_types:
        return False, f"type {kind}"

    if max_age_days > 0:
        age = offer_age_days(offer.get("published_at", ""))
        if age is not None and age > max_age_days:
            return False, f"annonce perimee ({age} j)"

    blob = f"{offer.get('title','')} {offer.get('description','')[:1500]}".lower()
    for word in exclude_keywords:
        if word.lower() in blob:
            return False, f"exclu: {word}"
    return True, ""


def upsert_offers(conn: sqlite3.Connection, offers: list[dict]) -> int:
    inserted = 0
    for offer in offers:
        cur = conn.execute(
            """INSERT OR IGNORE INTO offers
            (source, external_id, title, company, url, job_type, location, salary,
             tags, description, published_at, fetched_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                offer["source"], offer["external_id"], offer.get("title", ""),
                offer.get("company", ""), offer.get("url", ""), offer.get("job_type", ""),
                offer.get("location", ""), offer.get("salary", ""), offer.get("tags", ""),
                offer.get("description", ""), offer.get("published_at", ""), _now(),
            ),
        )
        inserted += cur.rowcount
    conn.commit()
    return inserted


def add_manual(conn, company: str, url: str, note: str, title: str = "", rate: str = "", kind: str = "outreach") -> int:
    """Ajoute a la main soit un prospect (demarchage), soit une offre publiee.

    kind='outreach' : tu as trouve l'entreprise et observe un probleme.
    kind='freelance' : l'entreprise a publie une offre, tu y reponds.
    """
    external_id = f"manual-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    cur = conn.execute(
        """INSERT INTO offers
        (source, external_id, title, company, url, job_type, location, salary,
         tags, description, published_at, fetched_at)
        VALUES ('manual', ?, ?, ?, ?, ?, 'direct', ?, '', ?, ?, ?)""",
        (
            external_id, title or f"Prospect: {company}", company, url, kind, rate,
            note, datetime.now(timezone.utc).date().isoformat(), _now(),
        ),
    )
    conn.commit()
    return int(cur.lastrowid)


def prune_stale(conn: sqlite3.Connection, max_age_days: int) -> int:
    """Supprime les annonces perimees jamais utilisees (aucune candidature liee)."""
    if max_age_days <= 0:
        return 0
    cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
    rows = conn.execute(
        """SELECT id, published_at FROM offers o
        WHERE NOT EXISTS (SELECT 1 FROM applications a WHERE a.offer_id = o.id)"""
    ).fetchall()
    removed = 0
    for row in rows:
        parsed = _parse_date(row["published_at"])
        if parsed is not None and parsed.isoformat() < cutoff:
            conn.execute("DELETE FROM offers WHERE id = ?", (row["id"],))
            removed += 1
    conn.commit()
    return removed


def unscored(conn: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return conn.execute(
        """SELECT o.* FROM offers o
        LEFT JOIN scores s ON s.offer_id = o.id
        WHERE s.offer_id IS NULL
        ORDER BY o.fetched_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()


def save_score(conn, offer_id: int, score: int, verdict: str, reasons: list[str], red_flags: list[str], angle: str) -> None:
    conn.execute(
        """INSERT INTO scores (offer_id, score, verdict, reasons, red_flags, angle, scored_at)
        VALUES (?,?,?,?,?,?,?)
        ON CONFLICT(offer_id) DO UPDATE SET
        score=excluded.score, verdict=excluded.verdict, reasons=excluded.reasons,
        red_flags=excluded.red_flags, angle=excluded.angle, scored_at=excluded.scored_at""",
        (offer_id, score, verdict, json.dumps(reasons, ensure_ascii=False),
         json.dumps(red_flags, ensure_ascii=False), angle, _now()),
    )


def list_offers(conn, min_score: int = 0, status: str | None = None, limit: int = 30) -> list[sqlite3.Row]:
    query = """SELECT o.*, s.score, s.verdict, s.angle, a.status
    FROM offers o
    LEFT JOIN scores s ON s.offer_id = o.id
    LEFT JOIN applications a ON a.offer_id = o.id
    WHERE COALESCE(s.score, -1) >= ?
    """
    params: list = [min_score]
    if status:
        query += " AND COALESCE(a.status, 'new') = ?"
        params.append(status)
    query += " ORDER BY COALESCE(s.score,0) DESC, o.fetched_at DESC LIMIT ?"
    params.append(limit)
    return conn.execute(query, params).fetchall()


def get_offer(conn, offer_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT o.*, s.score, s.verdict, s.reasons, s.red_flags, s.angle, a.status, a.notes
        FROM offers o
        LEFT JOIN scores s ON s.offer_id = o.id
        LEFT JOIN applications a ON a.offer_id = o.id
        WHERE o.id = ?""",
        (offer_id,),
    ).fetchone()


def set_status(conn, offer_id: int, status: str, proposal_path: str | None = None) -> None:
    now = datetime.now(timezone.utc)
    applied = now.isoformat(timespec="seconds") if status == "applied" else None
    follow_up = (now + timedelta(days=3)).isoformat(timespec="seconds") if status == "applied" else None
    conn.execute(
        """INSERT INTO applications (offer_id, status, proposal_path, applied_at, follow_up_at)
        VALUES (?,?,?,?,?)
        ON CONFLICT(offer_id) DO UPDATE SET
        status=excluded.status,
        proposal_path=COALESCE(excluded.proposal_path, applications.proposal_path),
        applied_at=COALESCE(excluded.applied_at, applications.applied_at),
        follow_up_at=COALESCE(excluded.follow_up_at, applications.follow_up_at)""",
        (offer_id, status, proposal_path, applied, follow_up),
    )
    conn.commit()


def due_follow_ups(conn) -> list[sqlite3.Row]:
    now = _now()
    return conn.execute(
        """SELECT o.id, o.title, o.company, o.url, a.follow_up_at
        FROM applications a JOIN offers o ON o.id = a.offer_id
        WHERE a.status = 'applied' AND a.follow_up_at IS NOT NULL AND a.follow_up_at <= ?
        ORDER BY a.follow_up_at""",
        (now,),
    ).fetchall()


def stats(conn) -> dict:
    def scalar(sql: str, *params):
        row = conn.execute(sql, params).fetchone()
        return row[0] if row else 0

    applied = scalar("SELECT COUNT(*) FROM applications WHERE status != 'new'")
    replied = scalar("SELECT COUNT(*) FROM applications WHERE status IN ('replied','won','lost')")
    won = scalar("SELECT COUNT(*) FROM applications WHERE status = 'won'")
    return {
        "offres": scalar("SELECT COUNT(*) FROM offers"),
        "scorees": scalar("SELECT COUNT(*) FROM scores"),
        "shortlist": scalar("SELECT COUNT(*) FROM scores WHERE score >= 55"),
        "candidatures": applied,
        "reponses": replied,
        "gagnees": won,
        "taux_reponse": f"{(replied / applied * 100):.0f}%" if applied else "-",
        "taux_conversion": f"{(won / applied * 100):.0f}%" if applied else "-",
    }
