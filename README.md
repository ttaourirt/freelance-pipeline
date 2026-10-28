# freelance-pipeline

Veille d'offres, scoring et génération de propositions. **Sources légales uniquement, 0 €.**

```bash
fp fetch          # récupère les offres (API publiques)
fp score          # note chaque offre selon ton profil
fp list           # shortlist triée par score
fp propose 42     # rédige la proposition dans output/proposals/
fp status 42 applied
fp followups      # qui relancer aujourd'hui
fp stats          # taux de réponse, conversion
```

## À lire avant de l'utiliser : ce que cet outil ne fera pas

**Il ne trouvera pas 20 missions freelance par jour.** Les vraies plateformes de freelance
(Malt, Upwork, ComeUp, Fiverr) n'ont pas d'API et interdisent le scraping. Ce serait un
bannissement, pas une stratégie.

Ce que les sources publiques contiennent réellement :

| Source | Contenu | Volume utile |
| --- | --- | --- |
| **Codeur.com** (RSS) | **missions freelance françaises**, budget affiché | ~35 offres par passage, **la plupart exploitables** |
| Remotive | API publique, remote | ~9 offres/req, peu de freelance |
| Himalayas | API publique, remote | ~100 offres, majoritairement plein temps |
| RemoteOK | API publique, remote | ~99 offres, majoritairement plein temps |

Les trois dernières sont des job boards d'emploi : sur ~110 offres récupérées, **3 à 6
méritent une candidature**. Codeur est la seule source de vraies missions.

**Donc l'outil est bon pour deux choses :**

1. **Répondre aux missions Codeur** (`fp fetch --sources codeur`), et à celles que tu
   récupères à la main sur Malt / ComeUp (`fp lead --kind freelance`).
2. **La prospection directe** (`fp lead`), qui reste ta source de chiffre d'affaires la
   plus prévisible.

## Installation

```bash
python3.12 -m venv .venv
.venv/bin/pip install -e .
cp config.example.toml config.toml   # puis remplis-le
```

Optionnel mais fortement recommandé — clé LLM gratuite pour un scoring fin :
<https://console.groq.com/keys> → `GROQ_API_KEY=...` dans `.env`

Sans clé, le scoring fonctionne par mots-clés (moins pertinent) et les propositions
sortent d'un gabarit.

## Le workflow qui produit des clients

### 1. Les flux (5 min, 2 fois par semaine)

```bash
.venv/bin/python -m freelance.cli fetch
.venv/bin/python -m freelance.cli score --limit 120
.venv/bin/python -m freelance.cli list --min-score 65
```

Traite les 3-5 offres retenues :

```bash
.venv/bin/python -m freelance.cli show 12
.venv/bin/python -m freelance.cli propose 12
```

Lis la proposition, corrige-la, envoie-la **à la main**.

### 2. La prospection directe (le vrai levier)

Tu identifies une entreprise, tu observes un problème concret, tu l'ajoutes :

```bash
.venv/bin/python -m freelance.cli lead \
  --company "Cabinet Dupont" \
  --url "https://dupont-expertise.fr" \
  --note "Le formulaire de contact renvoie une 500 depuis la refonte. Les demandes arrivent par mail et sont recopiées à la main dans Excel." \
  --title "Réparation du formulaire + envoi automatique dans leur outil" \
  --rate "700 EUR"

.venv/bin/python -m freelance.cli propose 112
```

Voir `OUTREACH.md` pour la méthode complète (où trouver ces entreprises, quoi observer,
quoi écrire).

> Note tes observations en **anglais** si tu es en mode hors ligne : le gabarit insère
> ton texte tel quel dans un message anglais. Avec une clé Groq, le modèle traduit et
> reformule correctement.

### 3. Le suivi

```bash
.venv/bin/python -m freelance.cli status 112 applied
.venv/bin/python -m freelance.cli followups   # relances dues à J+3
.venv/bin/python -m freelance.cli status 112 won
```

`fp stats` est le seul tableau de bord qui compte : **taux de réponse**. Sous 10 % sur
30 envois, le problème est le message. Sous 5 %, c'est la cible.

## La page de service

`site/index.html` : une page statique en anglais (un seul fichier, zéro dépendance) à
envoyer dans le premier message ou à héberger gratuitement sur GitHub Pages.

Elle contient les 2 études de cas, les 3 offres avec prix, le process et une FAQ qui
traite l'objection « tu n'as pas de références ». Voir `site/README.md` pour la
personnalisation et la mise en ligne.

```bash
cd site && python3 -m http.server 8000   # http://localhost:8000
```

## Ce que la proposition contient, et pourquoi

Chaque proposition est plafonnée à 150 mots et suit 4 blocs : preuve que tu as compris,
premier livrable concret, méthode de travail, une seule question.

Le générateur a l'interdiction explicite d'inventer une expérience, un client ou un chiffre.
C'est la seule façon d'envoyer 10 messages par jour sans te faire griller.

`output/proposals/offer-<id>.md` contient aussi une section **« à vérifier avant d'envoyer »**
qui liste tes angles morts (pas de portfolio, email manquant…).

## Commandes

| Commande | Effet |
| --- | --- |
| `check` | config, LLM, état du pipeline |
| `fetch [-v] [--sources ...]` | récupère et filtre les offres |
| `score [--limit N] [--min-score N]` | note les offres non notées |
| `list [--min-score] [--status] [--limit]` | shortlist |
| `show <id>` | détail + raisons du score + signaux d'alerte |
| `propose <id>` | génère la proposition |
| `lead --company ...` | ajoute un prospect manuel |
| `status <id> <état>` | new / applied / replied / won / lost / skipped |
| `followups` | relances dues |
| `stats` | indicateurs |

## Fichiers

```
freelance/
  config.py    profil + filtres (config.toml)
  llm.py       Groq / Gemini
  sources.py   Remotive / Himalayas / RemoteOK (API publiques)
  store.py     SQLite : offres, scores, candidatures
  score.py     pré-filtre mots-clés + scoring LLM
  proposal.py  génération et rendu des messages
  cli.py       commandes
```

## Limites assumées

- Pas de scraping de Malt / Upwork / LinkedIn : illégal ou interdit par les CGU.
- Les flux ne contiennent pas les missions freelance francophones : pour ça, `fp lead`.
- Le scoring LLM coûte ~0 € mais dépend des quotas gratuits (Groq : généreux).
- L'outil ne remplit pas les formulaires à ta place, et c'est volontaire : un message
  envoyé à la main convertit mieux qu'un envoi automatisé.
