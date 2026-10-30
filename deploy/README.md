# Déployer la veille sur un serveur (optionnel)

**Tu n'en as pas besoin pour commencer.** Le Mac suffit, avec Telegram branché
(voir `.env.example`). Ce dossier sert le jour où tu veux que la veille tourne
quand l'ordinateur est fermé.

## Ce que ça change réellement

| | Mac allumé | VPS à 5 €/mois |
| --- | --- | --- |
| Passe toutes les 2 minutes | ✅ | ✅ |
| Tourne quand tu fermes le laptop | ❌ | ✅ |
| Alerte Telegram | ✅ | ✅ |
| Coût | 0 € | ~5 €/mois |

La vitesse de détection est la même. Un VPS n'apporte que la **disponibilité**.

## Ce qu'il n'apporte pas

- **Pas plus de réactivité côté Codeur.** Le flux se met à jour chez eux.
- **Pas plus de chances d'être choisi.** Tu restes le 5e sur 100.
- **Pas de scraping possible.** Le serveur ne contourne aucune règle : il lit le
  même flux RSS public, juste depuis une autre machine.

Si le budget est limité, **paie plutôt un abonnement Codeur** : voir le profil du
client et répondre complètement pèse plus lourd que 3 minutes de vitesse.

## Fournisseurs corrects (4-6 €/mois)

| Fournisseur | Offre | Remarque |
| --- | --- | --- |
| Hetzner | CX22 (~4 €) | le meilleur rapport prix/perf, datacenter EU |
| Scaleway | DEV1-S (~6 €) | français, facturation à l'heure |
| OVH | VPS Value (~5 €) | français, support FR |

Prends **1 vCPU / 2 Go**, Debian 12. Rien de plus : le programme fait un `GET`
toutes les 2 minutes et écrit dans un fichier SQLite.

## Installation

Sur le serveur, en root :

```bash
apt-get update && apt-get install -y git
git clone https://github.com/ttaourirt/freelance-pipeline.git /tmp/fp
bash /tmp/fp/deploy/install.sh https://github.com/ttaourirt/freelance-pipeline.git
```

Le script installe Python, crée un utilisateur système `fpwatch` (pas de root),
clone le dépôt dans `/opt/freelance-pipeline`, crée le venv, installe le service
systemd et le démarre.

Puis renseigne les secrets :

```bash
nano /opt/freelance-pipeline/.env      # TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
systemctl restart fp-watch
journalctl -u fp-watch -f
```

## Vérifier que ça tourne

```bash
systemctl status fp-watch              # doit afficher "active (running)"
journalctl -u fp-watch -n 30           # les derniers passages
```

Tu dois voir une ligne `Veille demarree...` puis, à chaque cycle, rien du tout
tant qu'aucune annonce ne dépasse le seuil. C'est normal : le silence est le
comportement attendu.

## Bonnes pratiques

- **Intervalle minimum 120 s.** À 60 s tu doubles le trafic pour un gain de
  quelques secondes, et tu t'exposes à un blocage pour abus.
- **`.env` en `chmod 600`.** Il contient le token du bot Telegram.
- **Sauvegarde `data/pipeline.db`** de temps en temps : c'est ton historique de
  candidatures.
- **Mets à jour avec `git pull` puis `systemctl restart fp-watch`.**

## Arrêter et désinstaller

```bash
systemctl disable --now fp-watch
rm /etc/systemd/system/fp-watch.service
rm -rf /opt/freelance-pipeline
userdel fpwatch
```
