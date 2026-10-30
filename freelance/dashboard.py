"""Tableau de bord local : une page HTML regeneree a chaque cycle du veilleur.

Pas de serveur, pas de dependance : un fichier ouvert dans le navigateur qui se
rafraichit tout seul. Objectif unique : voir les annonces de moins de 30 minutes
et cliquer sur « Postuler » avant les 100 autres.
"""
from __future__ import annotations

import html
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import store
from .config import OUTPUT_DIR


def _age_label(published_at: str) -> tuple[str, int | None]:
    parsed = store._parse_date(published_at)
    if parsed is None:
        return "-", None
    minutes = int((datetime.now(timezone.utc) - parsed).total_seconds() // 60)
    if minutes < 60:
        return f"{minutes} min", minutes
    hours = minutes // 60
    if hours < 24:
        return f"{hours} h", minutes
    return f"{minutes // 1440} j", minutes


def write(conn: sqlite3.Connection, path: Path | None = None, limit: int = 40) -> Path:
    path = path or OUTPUT_DIR / "dashboard.html"
    rows = conn.execute(
        """SELECT o.id, o.title, o.url, o.salary, o.published_at, o.source,
                  s.score, s.verdict, a.status
        FROM offers o
        LEFT JOIN scores s ON s.offer_id = o.id
        LEFT JOIN applications a ON a.offer_id = o.id
        ORDER BY o.published_at DESC
        LIMIT ?""",
        (limit,),
    ).fetchall()

    fresh = 0
    body = []
    for row in rows:
        age_label, minutes = _age_label(row["published_at"])
        is_fresh = minutes is not None and minutes <= 30
        if is_fresh:
            fresh += 1
        score = row["score"] if row["score"] is not None else "-"
        css = " class=\"fresh\"" if is_fresh else ""
        status = row["status"] or "new"
        title = html.escape(row["title"] or "")
        budget = html.escape(row["salary"] or "-")
        body.append(
            f"""<tr{css}>
  <td class="age">{age_label}</td>
  <td class="score">{score}</td>
  <td class="budget">{budget}</td>
  <td class="title">{title}<div class="src">{row['source']} · #{row['id']} · {status}</div></td>
  <td class="act"><a href="{html.escape(row['url'] or '#')}" target="_blank" rel="noopener">Postuler</a></td>
</tr>"""
        )

    generated = datetime.now().strftime("%H:%M:%S")
    document = f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta http-equiv="refresh" content="30">
<title>Veille missions</title>
<style>
  body{{margin:0;background:#faf8f4;color:#14110f;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
  header{{padding:18px 24px;border-bottom:1px solid #dcd7cf;display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:12px}}
  h1{{font-size:16px;margin:0;letter-spacing:-.01em}}
  .meta{{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:#4a4642}}
  .warn{{background:#e7efe9;border-left:3px solid #15503a;padding:10px 14px;margin:14px 24px;font-size:13px;border-radius:0 4px 4px 0}}
  table{{width:100%;border-collapse:collapse;margin-top:6px}}
  th{{text-align:left;font-family:ui-monospace,Menlo,monospace;font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:#4a4642;padding:10px 8px;border-bottom:1px solid #dcd7cf}}
  td{{padding:11px 8px;border-bottom:1px solid #eee7dd;vertical-align:top}}
  tr.fresh td{{background:#fffdf5}}
  .age{{font-family:ui-monospace,Menlo,monospace;white-space:nowrap;color:#4a4642}}
  tr.fresh .age{{color:#15503a;font-weight:600}}
  .score{{font-family:ui-monospace,Menlo,monospace;text-align:right;white-space:nowrap}}
  .budget{{font-family:ui-monospace,Menlo,monospace;font-size:12px;color:#4a4642;white-space:nowrap}}
  .title{{font-weight:520}}
  .src{{font-family:ui-monospace,Menlo,monospace;font-size:11px;color:#8a8378;font-weight:400;margin-top:2px}}
  .act a{{color:#15503a;font-weight:560;text-decoration:none;white-space:nowrap}}
  .act a:hover{{text-decoration:underline}}
</style></head>
<body>
<header>
  <h1>Veille missions</h1>
  <div class="meta">{fresh} annonce(s) de moins de 30 min · maj {generated} · rafraichissement auto 30 s</div>
</header>
<div class="warn">
  <strong>Règle :</strong> ouvre la page et regarde « X freelances ont répondu ».
  Moins de 20 → réponds. Plus de 50 → passe. Génère le message avec
  <code>fp propose &lt;id&gt;</code>.
</div>
<table>
<thead><tr><th>Âge</th><th>Score</th><th>Budget</th><th>Titre</th><th></th></tr></thead>
<tbody>
{chr(10).join(body) if body else '<tr><td colspan="5">Aucune offre. Lance <code>fp fetch</code>.</td></tr>'}
</tbody></table>
</body></html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(document, encoding="utf-8")
    return path
