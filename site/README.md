# Page de service

Une page statique, un seul fichier, zéro dépendance (pas de police Google, pas de JS,
pas de framework). Elle s'ouvre en double-cliquant sur `index.html` et se charge en
moins de 30 Ko.

## À remplacer avant de publier (3 minutes)

Cherche et remplace ces valeurs dans `index.html` :

| Rechercher | Remplacer par |
| --- | --- |
| `Taourirt` | ton nom ou le nom de ton activité |
| `you@example.com` | ton email professionnel (2 occurrences + le lien `mailto`) |
| `https://github.com/your-account` | ton GitHub |
| `from €500` / `from €900` | tes prix réels |

```bash
# vérifier qu'il ne reste rien
grep -n "example.com\|your-account\|Taourirt" index.html
```

## Pourquoi cette structure

| Section | Rôle |
| --- | --- |
| Hero | une promesse concrète + le problème du client, pas ton CV |
| Terminaison animée | montre le *avant / après* en 3 lignes, sans capture d'écran |
| Services | 3 offres, 3 prix, une seule phrase chacune |
| Selected work | 2 projets réels, problème → décisions → stack → limites |
| Process | 4 étapes, rassure sur le risque |
| FAQ | traite les 5 objections réelles, surtout « tu n'as pas de références » |
| Contact | une phrase de demande, une promesse de délai de réponse |

## Ce qu'il ne faut PAS changer

- **Les étiquettes `Personal project` / `Training project`.** Elles sont vraies.
  Les remplacer par « Client work » est un mensonge qui se découvre au premier appel.
- **Le bloc `Limitation:`** sur DataShare. Dire ce qui n'est pas prêt inspire plus
  confiance que prétendre que tout l'est.
- **La FAQ « no client testimonials yet »**. Elle désarme l'objection avant qu'elle
  soit posée. C'est la section qui convertit le plus.

## Publier gratuitement

### Option 1 — GitHub Pages (recommandé, gratuit à vie)

```bash
cd site
git init
git add index.html
git commit -m "Service page"
# crée le dépôt sur github.com puis :
git remote add origin https://github.com/TON-COMPTE/service-page.git
git push -u origin main
```

Puis dans le dépôt : **Settings → Pages → Source: Deploy from a branch → main / (root)**.
URL : `https://TON-COMPTE.github.io/service-page/`

### Option 2 — Cloudflare Pages

`dash.cloudflare.com` → Workers & Pages → Create → Pages → Upload assets → glisse `site/`.
URL en `*.pages.dev`, personnalisable avec ton domaine.

### Option 3 — Netlify Drop

`app.netlify.com/drop` → glisse le dossier `site/`. Le plus rapide pour tester.

## Aperçu local

```bash
cd site && python3 -m http.server 8000
# http://localhost:8000
```

(Le double-clic sur `index.html` marche aussi, mais un vrai serveur évite les
surprises de chemins relatifs si tu ajoutes des pages plus tard.)

## Quand tu auras un vrai client

Remplace l'étude de cas la plus faible par la mission réelle, avec la même structure :

```
Problem      ce qui n'allait pas, en une phrase que le client reconnaîtrait
What I built ce que tu as livré, sans jargon
Decisions    pourquoi tu as fait ces choix (c'est ce que les clients paient)
Stack        les technos
Result       un chiffre vérifiable, ou "delivered on time" si tu n'en as pas
```

Ne mets **jamais** un chiffre que tu ne peux pas justifier. Un « 40h économisées »
inventé se fait démonter en appel.

Et demande l'autorisation écrite avant de citer un client.
