# Architecture de la V1

Ce document explique les choix faits pour la V1, ce qu'ils permettent, et
leurs limites connues.

## 1. Vue d'ensemble

Une seule application Django (monolithe), une base PostgreSQL, aucune autre
brique obligatoire.

```
Navigateur ──HTTPS──> Django (gunicorn + WhiteNoise) ──> PostgreSQL
                         │
                         └─ cache mémoire (Redis plus tard si plusieurs instances)
```

- Les pages sont rendues par Django (templates), le jeu est piloté par un petit
  fichier JavaScript (`game.js`, sans framework ni étape de build) qui parle à
  une API JSON.
- Les fichiers statiques (CSS, JS, police, icônes) sont servis par WhiteNoise,
  avec des noms hachés et un cache navigateur long.
- Les images des rounds sont générées par Pillow une fois par édition et
  stockées en base (WebP 1440×960, 80 à 140 Ko chacune). Les bananes sont
  placées de façon totalement aléatoire : elles peuvent se chevaucher, voire
  se cacher, comme dans la version d'origine.
- Pendant les 5 secondes, l'image occupe toute la fenêtre. Sur un téléphone
  tenu droit, elle est tournée d'un quart de tour pour utiliser toute la
  hauteur : tous les joueurs voient exactement la même image.

Pourquoi ne pas changer de stack : Django fournit déjà l'authentification, les
sessions, l'admin, la protection CSRF, les migrations et l'i18n. Le jeu est
simple ; aucune contrainte ne justifiait une réécriture.

## 2. Déroulé d'une partie

Le serveur est la seule source de vérité. Le navigateur ne connaît jamais un
nombre de bananes avant d'avoir répondu, et n'envoie jamais de score.

```
POST /api/editions/<n>/start                → crée la partie (1 par joueur et par édition)
POST /api/editions/<n>/rounds/1/image       → renvoie l'image, note l'heure d'affichage
     (5 s d'affichage côté navigateur)
POST /api/editions/<n>/rounds/1/answer      → enregistre la réponse, révèle le vrai nombre
     … rounds 2 et 3 …
     au dernier round : score calculé, décision « classé / non classé »
GET  /api/editions/<n>/state                → état complet (reprise après rechargement)
```

Règles appliquées par le serveur :

- un round ne peut être affiché qu'une fois le précédent répondu ;
- l'image d'un round peut être re-téléchargée pendant 15 s (micro-coupure
  réseau), jamais ensuite ;
- une réponse est définitive ; la renvoyer ne change rien (pas de double
  soumission) ;
- les écritures se font dans une transaction avec verrouillage de la ligne ;
- une partie commencée juste avant midi peut être terminée pendant 15 min
  après la bascule.

## 3. Modèle de données

Trois tables métier, plus l'utilisateur.

| Table | Rôle | Champs clés |
|---|---|---|
| `accounts_user` | Compte joueur | `email` (unique, identifiant), mot de passe haché, `date_joined` |
| `find_bananas_edition` | Défi du jour | `date`, `market` (`global`), `theme` (`banana`), `number`, `starts_at`, `ends_at` — unique sur (`market`, `date`) |
| `find_bananas_editionround` | Une image d'une édition | `index`, `count`, `image` (WebP), dimensions |
| `find_bananas_play` | La partie d'un joueur | `user` (nullable), `guest_key`, `ip_hash`, `status`, `rounds` (JSON), `score`, `ranked`, dates |

Choix notables :

- **Les éditions sont conservées** (l'ancien code supprimait la précédente) :
  l'historique d'un joueur reste lié aux images et nombres réellement joués.
- **Les rounds d'une partie sont en JSON** (`guess`, `count`, heures
  d'affichage et de réponse). Ajouter une information par round ou changer le
  nombre de rounds ne demande pas de migration. Le score est tout de même
  stocké en colonne, indexé, pour le classement.
- **Contraintes d'unicité en base** : une partie par compte et par édition, une
  partie par invité et par édition. La base empêche les doublons même si deux
  requêtes arrivent en même temps.
- **Modèle utilisateur personnalisé dès le départ** (connexion par email). Le
  changer plus tard aurait été une migration lourde.

## 4. Invités et comptes

- Un visiteur reçoit une clé aléatoire (`guest_key`) stockée dans sa session
  serveur (cookie de session d'un an, `HttpOnly`, `SameSite=Lax`). C'est ce
  qui lui permet de reprendre sa partie et de voir son résultat s'il revient.
- À l'inscription ou à la connexion, les parties invitées de l'appareil sont
  rattachées au compte, sauf pour les éditions déjà jouées avec ce compte
  (le compte garde alors sa propre partie).
- Un joueur connecté retrouve « déjà joué aujourd'hui » sur tous ses appareils.
- Données collectées : email, mot de passe haché et pseudo. Rien d'autre.
- **Pseudo** : public, choisi à l'inscription, modifiable depuis « Mon profil ».
  3 à 20 caractères (lettres sans accents, chiffres, `_`, `-`), unique sans
  tenir compte des majuscules (contrainte en base). Les noms réservés et
  vulgaires sont refusés par `accounts/usernames.py` : une liste de mots
  refusés partout (mots longs sans ambiguïté) et une liste de mots refusés
  seulement comme mot entier (« con » bloque « Tom_con » mais pas
  « Constance »). Le filtre ne sera jamais parfait : un pseudo peut être
  renommé depuis `/admin/`. Un compte sans pseudo (créé avant cette règle,
  ou demain après une connexion Google) est redirigé vers la page de choix
  du pseudo, sans interrompre une partie en cours.
- Suppression de compte en libre-service ; elle efface aussi ses parties.

**Série de jours** (`streaks.py`) : nombre de défis consécutifs terminés, pour
un compte ou, sans compte, pour l'identifiant invité du navigateur. La série
en cours reste valable jusqu'à la fin du défi suivant (avoir joué hier suffit
tant qu'on n'a pas encore joué aujourd'hui). Les parties invitées étant
rattachées au compte à l'inscription, la série survit à la création du
compte. Affichée sur l'écran de résultat (dès 2 jours), dans le profil (en
cours et record) et dans le partage (« 🔥 5 »). Pour un invité avec une série,
l'invitation à créer un compte devient « Ne perds pas ta série de 5 jours ».
Calculée à la demande à partir des parties enregistrées (aucune colonne
dédiée) : à mettre en cache ou à stocker si les historiques deviennent longs.

## 5. Score et comparaison

**Score** : règle d'origine conservée, somme des écarts absolus des trois
rounds (0 = parfait, plus bas = mieux). Tous les joueurs d'une édition voient
les mêmes images, la comparaison des scores bruts au sein d'une édition est
donc équitable.

**Code couleur d'un round** (affichage et partage) : selon l'écart, comparé à
environ 10 %, 15 % et 20 % du nombre moyen de bananes du round. Les seuils sont
dans `ROUND_SPECS` (`editions.py`) et envoyés au navigateur avec la partie.

| Round | 🟢 vert | 🟡 jaune | 🟠 orange | 🔴 rouge |
|---|---|---|---|---|
| 1 (20 à 50) | ≤ 4 | ≤ 6 | ≤ 8 | au-delà |
| 2 (50 à 100) | ≤ 8 | ≤ 11 | ≤ 15 | au-delà |
| 3 (100 à 200) | ≤ 15 | ≤ 23 | ≤ 30 | au-delà |
| Total | ≤ 27 | ≤ 40 | ≤ 53 | au-delà |

Un compte exact (🎯) déclenche des confettis et un mot qui traverse l'écran.

Règle de couleur : le **jaune banane** est réservé à ce qui se clique
(boutons, logo). Les **couleurs de résultat** marquent ce qu'on a obtenu :
écart de chaque round, pastilles 1-2-3, tableau final et la grosse pastille du
score (couleur du total). Une pastille jaune signifie donc toujours « résultat
moyen ».

**Population de référence** : les parties *terminées* et *classées* de la même
édition. Les visiteurs qui n'ont pas fini ne comptent pas.

**Calcul** : `top X %` avec `X = arrondi supérieur de 100 × (joueurs strictement
meilleurs + 1) / nombre de joueurs`. Les ex aequo partagent la meilleure
position. Exemple : 10 joueurs, 1 meilleur que vous → top 20 %.

**Trop peu de joueurs** : en dessous de 20 parties classées
(`RANKING_MIN_PLAYERS`), aucun pourcentage n'est affiché, seulement le nombre
de joueurs du jour.

**Performance** : les scores sont de petits entiers. On maintient
l'histogramme `{score: nombre de joueurs}` de l'édition (une requête
`GROUP BY`, mise en cache 30 s). Le calcul d'un percentile est ensuite une
somme en mémoire, quel que soit le nombre de joueurs.

**Le classement évolue dans la journée** : le pourcentage affiché est celui du
moment ; l'historique recalcule la position avec tous les joueurs de
l'édition.

## 6. Sécurité et anti-triche

Corrigé par rapport au prototype :

| Faille | Traitement |
|---|---|
| Bonnes réponses dans le HTML | Le nombre n'est envoyé qu'après la réponse |
| Score calculé par le navigateur | Calculé et stocké par le serveur |
| Image consultable à volonté | Servie à la demande, re-téléchargeable 15 s seulement |
| Rejouer en vidant ses cookies | Au-delà de 5 parties classées par connexion et par édition, les suivantes ne comptent plus dans le classement |
| `SECRET_KEY` publique, `ALLOWED_HOSTS=*` | Variables d'environnement, refus de démarrer sans clé |
| Threads créés à chaque partie | Supprimés ; plus de planificateur dans le processus web |

Autres protections :

- réponses lentes (plus de 2 min après l'affichage) : la partie compte pour le
  joueur mais pas dans le classement (limite la capture d'écran puis comptage) ;
- limitation de débit par IP sur le démarrage de partie, les images, les
  réponses, l'inscription, la connexion et le mot de passe oublié ;
- l'IP brute n'est jamais stockée : seulement une empreinte salée, différente
  chaque jour ;
- CSRF sur toutes les requêtes d'écriture, cookies `Secure` et HSTS en
  production, `X-Frame-Options: DENY`, redirection post-connexion limitée au
  site ;
- historique accessible uniquement à son propriétaire.

**Ce qui reste possible** (assumé, proportionné à un jeu gratuit) : un joueur
déterminé peut faire une capture d'écran pendant les 5 secondes et compter
tranquillement en moins de 2 minutes, ou automatiser le comptage. Si les
classements prennent de la valeur (lots, marques), pistes : délai de réponse
plus court pour être classé, détection statistique des scores parfaits
répétés, classements réservés aux comptes vérifiés.

## 7. International

Préparé, sans être construit :

- **Un instant de bascule unique** (midi, heure de Paris) pour tout le monde ;
  les calculs gèrent le changement d'heure (une édition dure alors 23 h ou
  25 h).
- **Français et anglais dès la V1** : la langue du navigateur est détectée
  (navigateur en français → français, toute autre langue → anglais) ; un
  sélecteur en bas de page permet de changer, le choix est mémorisé dans un
  cookie. Le message partagé est dans la langue de celui qui partage.
- **Textes centralisés** : tous les textes visibles passent par le système de
  traduction de Django, y compris ceux du JavaScript (`strings.py`). Ajouter
  une langue = l'ajouter à `LANGUAGES` et créer son fichier `locale/<langue>`,
  sans toucher au code. Les fichiers compilés (`.mo`) sont versionnés.
- **Éditions par marché et par objet** : `Edition.market` et `Edition.theme`
  existent déjà (valeurs `global` et `banana`). Une édition « canettes pour
  l'Italie » sera une nouvelle ligne ; il restera à choisir le marché d'un
  visiteur (pays ou langue) et à fournir l'image de l'objet.

Décision à prendre plus tard : **comment déterminer le marché d'un joueur**
(langue du navigateur, pays de l'IP, choix explicite). Elle influence la
comparaison entre joueurs : un percentile n'a de sens qu'entre joueurs d'une
même édition.

## 8. Déploiement et coûts

Recommandation : **Render** (service web, région Francfort) + **Neon**
(PostgreSQL, offre gratuite, région UE).

| Poste | Coût mensuel |
|---|---|
| Render, service web 0,5 CPU / 512 Mo, toujours allumé | ~7 $ |
| Neon, offre gratuite (1 Go par projet, mise en veille après 5 min d'inactivité) | 0 $ |
| Email transactionnel (offre gratuite d'un fournisseur SMTP) | 0 € |
| Domaine find-bananas.com | déjà payé |
| **Total** | **~7 $ / mois** |

Variante tout-Render : PostgreSQL Render à ~6 $ / mois en plus (~13 $ au
total), une seule facture et une base toujours éveillée.

Pourquoi pas l'offre gratuite de Render pour le web : le service s'endort
après 15 min sans visite, et le premier visiteur attend de longues secondes.
Inacceptable pour un jeu de 30 secondes.

Volume en base : environ 330 Ko d'images par jour, soit ~120 Mo par an, et
~1 Ko par partie. L'offre gratuite de Neon tient plusieurs mois même avec du
trafic ; prévoir le passage en payant (facturation à l'usage) quand la base
approche 1 Go.

## 9. Limites et montée en charge

La V1 n'est **pas** dimensionnée pour des millions de joueurs simultanés. Ce
qu'elle supporte raisonnablement : une instance, quelques milliers de parties
par jour, avec un pic à midi.

Charge par partie : 1 page, 7 requêtes API, environ 7 écritures en base, 3
images (~330 Ko au total).

Quand le trafic augmente, dans l'ordre :

1. Plusieurs instances web + **Redis** (`CACHE_URL`) pour partager limites de
   débit et histogrammes. Aucun changement de code.
2. Base payante plus grosse, pool de connexions (PgBouncer / pooler Neon).
3. **Images sur un stockage objet + CDN** avec des URL signées à courte durée,
   au lieu de les servir depuis la base. C'est le premier vrai goulot : à midi,
   tous les joueurs demandent les mêmes 3 images.
4. Histogramme maintenu en continu (compteurs Redis) plutôt que recalculé.
5. Archivage des anciennes parties invitées.

Rien de cela n'exige de revoir le modèle de données.

## 10. Évolutions futures (non développées)

- Autres langues, choix du marché du joueur.
- Éditions sponsorisées : objet et marque par édition / marché, interface
  d'administration des campagnes.
- Image de partage générée (carte du score) pour les réseaux sociaux.
- Statistiques personnelles plus riches (courbe de progression, séries).
- Connexion sans mot de passe (lien magique) ou via Google / Apple.
- Classement entre amis.
- Notifications (« le défi du jour est en ligne »).
- Application mobile (PWA d'abord).
