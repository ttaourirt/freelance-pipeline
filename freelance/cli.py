"""Interface en ligne de commande."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime

from . import dashboard, llm, proposal, score, sources, store
from .config import Config

STATUSES = ["new", "applied", "replied", "won", "lost", "skipped"]


def _cfg() -> Config:
    return Config.load()


def cmd_check(_args) -> int:
    cfg = _cfg()
    print("Configuration\n")
    print(f"  profil      : {cfg.profile.name} <{cfg.profile.email}>")
    print(f"  offre       : {cfg.profile.positioning[:70]}")
    print(f"  tarif       : {cfg.profile.rate}")
    print(f"  sources     : {', '.join(cfg.filters.sources)}")
    provider = llm.resolve_provider(cfg)
    print(f"  LLM         : {provider}")
    if provider == "offline":
        print("                -> scoring par mots-cles seulement (moins fin)")
    gaps = cfg.profile_gaps()
    if gaps:
        print("\nA completer dans config.toml :")
        for gap in gaps:
            print(f"  - {gap}")
    conn = store.connect()
    s = store.stats(conn)
    print("\nPipeline")
    for key, value in s.items():
        print(f"  {key:<18}: {value}")
    return 0


def cmd_fetch(args) -> int:
    cfg = _cfg()
    conn = store.connect()
    print("Recuperation des offres...")
    found = sources.fetch_all(args.sources or cfg.filters.sources)
    kept, dropped = [], {}
    for offer in found:
        ok, reason = store.is_relevant(
            offer, cfg.filters.job_types, cfg.filters.exclude_keywords,
            cfg.filters.allow_unknown_type, cfg.filters.max_age_days,
        )
        if ok:
            kept.append(offer)
        else:
            dropped[reason] = dropped.get(reason, 0) + 1
    inserted = store.upsert_offers(conn, kept)
    pruned = store.prune_stale(conn, cfg.filters.max_age_days)
    print(f"\n  retenues : {len(kept)} | nouvelles en base : {inserted}")
    if pruned:
        print(f"  purgees  : {pruned} annonces de plus de {cfg.filters.max_age_days} jours")
    if dropped and args.verbose:
        for reason, count in sorted(dropped.items(), key=lambda x: -x[1]):
            print(f"    ecartees ({reason}): {count}")
    return 0


def cmd_score(args) -> int:
    cfg = _cfg()
    conn = store.connect()
    rows = store.unscored(conn, args.limit)
    if not rows:
        print("Rien a scorer. Lance `fetch` d'abord.")
        return 0
    print(f"Scoring de {len(rows)} offres ({llm.resolve_provider(cfg)})...\n")
    for index, row in enumerate(rows, start=1):
        result = score.score_offer(row, cfg)
        store.save_score(
            conn, row["id"], result["score"], result["verdict"],
            result["reasons"], result["red_flags"], result["angle"],
        )
        if result["score"] >= args.min_score:
            print(f"  [{result['score']:>3}] {row['title'][:58]}")
        if index % 20 == 0:
            conn.commit()
    conn.commit()
    print("\nTermine. `list` pour voir la shortlist.")
    return 0


def cmd_list(args) -> int:
    cfg = _cfg()
    conn = store.connect()
    rows = store.list_offers(conn, args.min_score, args.status, args.limit)
    if not rows:
        print("Aucune offre. Lance `fetch` puis `score`.")
        return 0
    print(f"{'ID':>4}  {'SCORE':>5}  {'AGE':>4}  {'TYPE':<10} {'SOURCE':<10} TITRE")
    print("-" * 100)
    for row in rows:
        value = row["score"] if row["score"] is not None else "-"
        status = row["status"] or "new"
        age = store.offer_age_days(row["published_at"])
        age_label = f"{age}j" if age is not None else "-"
        print(
            f"{row['id']:>4}  {str(value):>5}  {age_label:>4}  {row['job_type'][:10]:<10} "
            f"{row['source'][:10]:<10} {row['title'][:42]:<42} {status}"
        )
    print(f"\n{len(rows)} offre(s). `show <id>` pour le detail.")
    return 0


def cmd_show(args) -> int:
    conn = store.connect()
    row = store.get_offer(conn, args.id)
    if not row:
        print(f"Offre {args.id} introuvable.")
        return 1
    print(f"\n{row['title']} — {row['company']}")
    print(f"{row['url']}")
    print(f"source={row['source']} type={row['job_type']} lieu={row['location']}")
    print(f"salaire={row['salary'] or '-'}  publie={row['published_at'] or '-'}")
    if row["score"] is not None:
        print(f"\nSCORE {row['score']}/100 — {row['verdict']}")
        for reason in _json_list(row["reasons"]):
            print(f"  + {reason}")
        for flag in _json_list(row["red_flags"]):
            print(f"  ! {flag}")
        if row["angle"]:
            print(f"  angle: {row['angle']}")
    print(f"\nStatut: {row['status'] or 'new'}")
    print("\n--- description ---")
    print((row["description"] or "")[:1500])
    return 0


def _json_list(value) -> list:
    import json
    if not value:
        return []
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return [value]


def cmd_propose(args) -> int:
    cfg = _cfg()
    conn = store.connect()
    row = store.get_offer(conn, args.id)
    if not row:
        print(f"Offre {args.id} introuvable.")
        return 1
    offer = dict(row)
    result = proposal.generate(offer, cfg, offer, lang=args.lang)
    path = proposal.save(offer, result, cfg, offer)
    print(f"\nProposition -> {path}\n\nlangue detectee : {result.get('lang')}")
    print(result.get("message", ""))
    print("\n--- a verifier avant d'envoyer ---")
    for gap in cfg.profile_gaps():
        print(f"  ! {gap}")
    return 0


def cmd_status(args) -> int:
    if args.state not in STATUSES:
        print(f"Statut invalide. Choix: {', '.join(STATUSES)}")
        return 2
    conn = store.connect()
    store.set_status(conn, args.id, args.state, args.proposal)
    print(f"Offre {args.id} -> {args.state}")
    return 0


def cmd_lead(args) -> int:
    note = args.note or ""
    if args.note_file:
        if args.note_file == "-":
            note = sys.stdin.read()
        else:
            from pathlib import Path

            note = Path(args.note_file).read_text(encoding="utf-8")
    if not note.strip():
        print("Note vide : utilise --note ou --note-file (ou - pour coller depuis stdin).")
        return 2

    conn = store.connect()
    offer_id = store.add_manual(
        conn, company=args.company, url=args.url or "", note=note,
        title=args.title or "", rate=args.rate or "", kind=args.kind,
    )
    kind_label = "offre publiee" if args.kind == "freelance" else "prospect direct"
    print(f"{kind_label} ajoute: #{offer_id} — {args.company}")
    print(f"Ensuite: score --limit 1 puis propose {offer_id}")
    return 0


def _notify(title: str, message: str) -> None:
    """Notification macOS, ignoree si non disponible."""
    try:
        import subprocess

        subprocess.run(
            ["osascript", "-e",
             f'display notification {json.dumps(message)} with title {json.dumps(title)} sound name "Glass"'],
            check=False, capture_output=True, timeout=10,
        )
    except Exception:  # noqa: BLE001 - une notification ratee ne doit rien casser
        pass


def _watch_cycle(conn, cfg, sources_list: list[str], min_score: int, notify: bool) -> list[dict]:
    known = {src: store.known_ids(conn, src) for src in sources_list}
    found = sources.fetch_all(sources_list, log=lambda *_a, **_k: None)

    fresh: list[dict] = []
    for offer in found:
        src = offer.get("source", "")
        if offer.get("external_id") in known.get(src, set()):
            continue
        ok, _reason = store.is_relevant(
            offer, cfg.filters.job_types, cfg.filters.exclude_keywords,
            cfg.filters.allow_unknown_type, cfg.filters.max_age_days,
        )
        if not ok:
            continue
        fresh.append(offer)

    if not fresh:
        return []

    store.upsert_offers(conn, fresh)
    results = []
    for offer in fresh:
        row = conn.execute(
            "SELECT * FROM offers WHERE source = ? AND external_id = ?",
            (offer["source"], offer["external_id"]),
        ).fetchone()
        if row is None:
            continue
        scored = score.score_offer(row, cfg)
        store.save_score(
            conn, row["id"], scored["score"], scored["verdict"],
            scored["reasons"], scored["red_flags"], scored["angle"],
        )
        entry = {"id": row["id"], "title": row["title"], "url": row["url"],
                 "budget": row["salary"], "score": scored["score"]}
        results.append(entry)
        if scored["score"] >= min_score:
            stamp = datetime.now().strftime("%H:%M:%S")
            print(f"  [{stamp}] {scored['score']:>3}/100  {row['title'][:58]}")
            print(f"          {row['url']}")
            if notify:
                _notify(f"Nouvelle mission {scored['score']}/100", f"{row['title'][:70]} — {row['salary'] or 'budget ?'}")
    conn.commit()
    return results


def cmd_watch(args) -> int:
    cfg = _cfg()
    conn = store.connect()
    interval = max(60, args.interval)
    print(f"Veille demarree sur {', '.join(args.sources)} — toutes les {interval}s")
    print("Ctrl+C pour arreter. Seules les annonces inedites sont scorees.\n")
    cycles = 0
    try:
        while True:
            cycles += 1
            new = _watch_cycle(conn, cfg, args.sources, args.min_score, notify=not args.no_notify)
            path = dashboard.write(conn)
            if new:
                print(f"  {len(new)} nouvelle(s) — tableau de bord : {path}\n")
            if args.once:
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nVeille arretee.")
    return 0


def cmd_dashboard(args) -> int:
    conn = store.connect()
    path = dashboard.write(conn)
    print(f"Tableau de bord : {path}")
    if args.open:
        import subprocess

        subprocess.run(["open", str(path)], check=False)
    return 0


def cmd_followups(_args) -> int:
    conn = store.connect()
    rows = store.due_follow_ups(conn)
    if not rows:
        print("Aucune relance due.")
        return 0
    print("Relances a envoyer :\n")
    for row in rows:
        print(f"  #{row['id']}  {row['company'][:24]:<24} {row['title'][:40]}")
    return 0


def cmd_stats(_args) -> int:
    conn = store.connect()
    for key, value in store.stats(conn).items():
        print(f"{key:<18}: {value}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="fp", description="Pipeline de prospection freelance (sources legales uniquement)."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("check", help="Verifier config et etat du pipeline")
    p.set_defaults(func=cmd_check)

    p = sub.add_parser("fetch", help="Recuperer les offres")
    p.add_argument("--sources", nargs="*", help="remotive himalayas remoteok")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("score", help="Scorer les offres non scorees")
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--min-score", type=int, default=55)
    p.set_defaults(func=cmd_score)

    p = sub.add_parser("list", help="Lister les offres")
    p.add_argument("--min-score", type=int, default=0)
    p.add_argument("--status", choices=STATUSES)
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", help="Detail d'une offre")
    p.add_argument("id", type=int)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("propose", help="Generer la proposition")
    p.add_argument("id", type=int)
    p.add_argument(
        "--lang", choices=["auto", "fr", "en"], default="auto",
        help="Langue du message (auto = detectee depuis l'annonce)",
    )
    p.set_defaults(func=cmd_propose)

    p = sub.add_parser("status", help="Changer le statut d'une offre")
    p.add_argument("id", type=int)
    p.add_argument("state", choices=STATUSES)
    p.add_argument("--proposal")
    p.set_defaults(func=cmd_status)

    p = sub.add_parser("lead", help="Ajouter un prospect ou une offre publiee")
    p.add_argument("--company", required=True)
    p.add_argument("--url")
    p.add_argument("--note", help="Ce que tu as observe / le texte de l'offre")
    p.add_argument("--note-file", help="Fichier contenant le texte (ou - pour stdin)")
    p.add_argument("--title", help="Intitule de la mission")
    p.add_argument("--rate", help="Budget envisage")
    p.add_argument(
        "--kind", choices=["outreach", "freelance"], default="outreach",
        help="outreach = demarchage direct (defaut) | freelance = reponse a une offre publiee",
    )
    p.set_defaults(func=cmd_lead)

    p = sub.add_parser("watch", help="Veille en continu : detecte les nouvelles annonces")
    p.add_argument("--interval", type=int, default=300, help="Secondes entre deux passages (defaut 300)")
    p.add_argument("--sources", nargs="*", default=["codeur"])
    p.add_argument("--min-score", type=int, default=60, help="Seuil de notification")
    p.add_argument("--no-notify", action="store_true", help="Pas de notification macOS")
    p.add_argument("--once", action="store_true", help="Un seul passage puis sortie")
    p.set_defaults(func=cmd_watch)

    p = sub.add_parser("dashboard", help="Generer et ouvrir le tableau de bord")
    p.add_argument("--open", action="store_true", help="Ouvre dans le navigateur")
    p.set_defaults(func=cmd_dashboard)

    p = sub.add_parser("followups", help="Relances a envoyer")
    p.set_defaults(func=cmd_followups)
    p = sub.add_parser("stats", help="Statistiques")
    p.set_defaults(func=cmd_stats)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\nInterrompu.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
