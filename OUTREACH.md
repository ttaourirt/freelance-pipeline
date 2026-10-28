# Prospection directe : la méthode

Le pipeline ne fait pas le travail difficile à ta place : **trouver 10 entreprises par jour
qui ont un problème visible et payant**. Voici comment, légalement.

---

## A. Répondre à une offre publiée (commence par là)

C'est plus facile que le démarchage : la demande est explicite, la personne cherche déjà.
Deux inconvénients : tu es en concurrence (5 à 20 réponses par offre), et le prix se
négocie souvent à la baisse.

### Où sont les vraies offres de mission

| Source | Ce que tu y trouves | Accès |
| --- | --- | --- |
| **Codeur.com** | projets freelance FR, budget souvent affiché, flux mis à jour en continu | ✅ **intégré** : `fp fetch --sources codeur` |
| **Malt** | la plus grosse place de marché FR, missions de 1 à 6 mois | Alertes email (gratuit) — pas d'API, scraping interdit |
| **ComeUp** | missions courtes, réponse avec devis | Compte gratuit |
| **Freelance-Info** | annonces FR, beaucoup de missions courtes | Inscription + alertes |
| **Upwork / Freelancer** | volume mondial, tarifs tirés vers le bas | Compte gratuit, commissions ~10-20 % |
| **LinkedIn** | posts « je cherche un freelance pour… » | Manuel, mais très réactif |

**Malt : active les alertes email** sur tes mots-clés (python, automatisation, scraping,
intégration API). Chaque matin, les nouvelles missions arrivent dans ta boîte. C'est le
remplaçant légal de l'API qui n'existe pas.

### Le workflow, 6 minutes par offre

```bash
# 1. lundi matin
fp fetch --sources codeur
fp score --limit 40
fp list --min-score 60

# 2. tu lis une offre
fp show 12

# 3. tu colles le texte de la mission (depuis Malt, un mail, un post)
pbpaste > /tmp/mission.txt          # macOS : le presse-papier
fp lead --company "Nom du client" \
        --url "https://lien-de-loffre" \
        --title "Le titre de la mission" \
        --rate "800 EUR" \
        --kind freelance \
        --note-file /tmp/mission.txt

# 4. tu génères la réponse
fp propose 36

# 5. tu la relis, tu la corriges, tu l'envoies
fp status 36 applied
```

### Les règles qui font la différence

1. **Réponds dans les 2 heures.** Sur une offre publiée, la moitié des contacts arrivent
   dans la première journée. Après 48 h, tu n'existes plus.
2. **Réponds à la question posée.** Si l'annonce demande « quelle est votre approche pour
   le scraping ? », tu y réponds à la première ligne. Pas de présentation générale.
3. **Ne t'aligne pas sur le prix le plus bas.** Il y a toujours quelqu'un pour proposer
   moins cher. Propose un **périmètre plus petit** au même prix, ou un premier livrable
   rapide.
4. **Une question concrète à la fin.** « Quel volume de rapports par mois ? » ouvre la
   conversation ; « êtes-vous disponible pour un appel ? » la ferme.
5. **Relance une fois à J+3.** Une phrase. Polie, sans pression.

### Le piège à éviter

Une offre avec un budget de 300 € pour « un site e-commerce complet avec paiement » n'est
pas une offre : c'est un piège. Filtre : si le budget est inférieur à 40 € de l'heure
estimée, passe. Le temps que tu perds dessus, tu ne le passes pas à chercher un vrai client.

---

## 1. Où trouver des prospects (sans scraping, sans spam)

Tout est public et consultable à la main. Tu notes, tu ne copies pas en masse.

| Source | Ce que tu cherches | Pourquoi ça marche |
| --- | --- | --- |
| Groupes Facebook / LinkedIn de ta ville ou de ton secteur | « quelqu'un sait faire… », « je cherche… » | la demande est explicite |
| Annonces Google « [métier] + [ville] » | sites avec formulaire cassé, site lent, pas de https | problème vérifiable en 2 min |
| Pages Facebook d'artisans / cabinets / associations | demandes traitées en commentaire, horaires de réponse | travail manuel visible |
| Salons / annuaires professionnels | petites structures sans outil interne | budget et decision-maker = le patron |
| Reddit r/smallbusiness, r/entrepreneur (lecture) | « how do I automate… » | besoin exprimé, en anglais |
| Ton propre entourage | quelqu'un qui tient des comptes sur Excel | confiance déjà établie |

**Interdit** : scraper LinkedIn, envoyer 500 mails depuis un outil, acheter des listes.
Résultat = domaine blacklisté et compte fermé, pas des clients.

## 2. Comment qualifier en 2 minutes

Garde le prospect seulement si **les 3** sont vrais :

1. **Le problème est visible** sans accéder à leur système (site cassé, process manuel
   annoncé, délai de réponse lent, PDF à remplir).
2. **Quelqu'un perd du temps ou de l'argent** à cause de ça, chaque semaine.
3. **Le décideur est joignable** : moins de 20 salariés = tu parles au patron.

Si tu n'as pas les 3, tu perds ton temps. Passe au suivant.

## 3. La structure du message (150 mots max)

```
1. Ce que tu as observé, précisément.       <- 1 phrase, aucun compliment
2. Ce que ça coûte / ce que tu ferais.      <- 1 phrase
3. Comment tu travailles.                   <- 2 phrases
4. Une seule question.                      <- 1 phrase
```

Exemple (à adapter, jamais à copier tel quel) :

> Hi Marc,
>
> Your quote form returns a 500 error — I tried it twice, it fails after the address field.
>
> If requests are arriving by email instead, that is probably 20-30 minutes of copy-paste per day. I would fix the form and push each request straight into your tool.
>
> I work in short steps: something working in a few days, then you tell me what to change. Fixed price, agreed before I start.
>
> Would it help if I sent you a 3-line plan by Thursday?
>
> Taourirt

**Ce qui tue un message :**
- « Je suis passionné par le développement » → personne ne s'en souvient
- « J'ai vu que votre entreprise est leader dans son domaine » → flagrant
- Un CV en pièce jointe → jamais ouvert
- Plus de 2 questions → l'autre n'en traite aucune

## 4. Cadence réellement tenable

| Moment | Action | Durée |
| --- | --- | --- |
| Lundi | 10 prospects qualifiés ajoutés (`fp lead`) | 45 min |
| Lundi | 10 messages envoyés | 30 min |
| Mardi-jeudi | idem, 10/jour | 30 min/jour |
| Vendredi | `fp followups` + relances J+3 | 20 min |

**50 messages par semaine.** C'est le minimum pour obtenir 2-5 réponses.
En dessous de 10 par semaine, tu ne peux rien conclure.

## 5. Prix

Tu affiches **500-900 € au forfait**, jamais un tarif horaire en premier contact.
Le forfait protège les deux côtés : lui sait ce qu'il paie, toi tu ne portes pas le risque
d'un périmètre flou.

Règle de découpage : **une seule chose livrée**. Si le client veut « tout automatiser »,
tu réponds : *« On commence par le formulaire, 700 €. Si ça marche, on regarde la suite
en janvier. »*

Acompte : 40 % avant de commencer. Sur un particulier ou une TPE, c'est normal et ça
filtre les curieux.

## 6. Objections (réponses courtes)

| Objection | Réponse |
| --- | --- |
| « C'est cher » | « Combien d'heures par semaine ça vous coûte aujourd'hui ? » |
| « On verra plus tard » | « Pas de souci. Je vous envoie le plan en 3 lignes, vous le gardez. » |
| « Vous avez des références ? » | Sois honnête si tu débutes, et propose : « Pas encore sur ce type de projet. Je vous montre une maquette sur votre cas avant tout engagement. » |
| « On a déjà quelqu'un » | « Très bien. Si ça bloque, gardez mon contact. » |
| Silence | J+3, une phrase. J+10, une phrase. Puis stop. |

Ne mens JAMAIS sur une expérience. Le mensonge se voit au premier appel technique, et un
client perdu se plaint publiquement.

## 7. Ce qu'il faut avant d'envoyer 50 messages

- [ ] Statut légal (micro-entreprise, gratuit, 15 min en ligne)
- [ ] Une page avec 2 projets réels, même petits, même personnels
- [ ] Un email professionnel (pas `pseudo@hotmail`)
- [ ] Un compte Stripe/Wise ou un IBAN pour facturer
- [ ] Un modèle de facture conforme (SIRET, mentions obligatoires)

Sans ces 5 points, les réponses positives n'aboutissent pas : tu gagnes des conversations
et zéro euro.

## 8. Le seul chiffre qui compte

```
30 messages  -> 3 réponses  -> 1 devis  -> 0,5 client
```

Si tu es sous 10 % de réponse sur 50 messages : retravaille le message.
Si tu es à 20 % de réponse mais 0 devis : retravaille l'offre (périmètre et prix).

Ne change jamais les deux en même temps, tu ne saurais pas ce qui a marché.
