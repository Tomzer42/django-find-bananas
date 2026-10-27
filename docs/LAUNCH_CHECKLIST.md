# Checklist de lancement

Cocher chaque point sur l'environnement de production.

## Configuration

- [ ] `DJANGO_DEBUG=0`
- [ ] `DJANGO_SECRET_KEY` neuve, longue, jamais publiée (l'ancienne est dans l'historique Git public)
- [ ] `DJANGO_ALLOWED_HOSTS` et `DJANGO_CSRF_TRUSTED_ORIGINS` contiennent le domaine final
- [ ] `SITE_URL=https://find-bananas.com` (utilisé dans le message de partage et les aperçus de lien)
- [ ] `DATABASE_URL` pointe sur PostgreSQL avec `sslmode=require`
- [ ] `DJANGO_TRUSTED_PROXY_COUNT=1` (sinon toutes les IP sont celles du proxy et les limites de débit bloquent tout le monde)
- [ ] SMTP configuré, email de test reçu (mot de passe oublié)
- [ ] `python manage.py check --deploy` sans avertissement bloquant

## Base de données

- [ ] `python manage.py migrate` exécuté
- [ ] `python manage.py generate_editions` exécuté : l'édition du jour et les 2 suivantes existent
- [ ] Compte administrateur créé (`createsuperuser`), `/admin/` accessible
- [ ] Sauvegardes de la base vérifiées (fenêtre de restauration de l'offre Neon choisie, ou export quotidien `pg_dump`)

## Parcours à tester à la main (téléphone + ordinateur)

- [ ] Visiteur : jouer les 3 rounds sans compte, voir le résultat
- [ ] Recharger la page pendant les 5 secondes : on arrive sur la saisie, l'image ne réapparaît pas
- [ ] Recharger après la partie : le résultat s'affiche, impossible de rejouer
- [ ] Partager : feuille de partage native sur téléphone, copie sur ordinateur ; le message contient le lien
- [ ] Ouvrir le lien partagé dans un autre navigateur : on arrive sur le jeu
- [ ] Créer un compte depuis l'écran de résultat : la partie apparaît dans « Mon profil » (moyennes générales et par round)
- [ ] Se déconnecter, se reconnecter : le résultat du jour est retrouvé
- [ ] Mot de passe oublié : email reçu, lien fonctionnel
- [ ] Supprimer un compte de test
- [ ] Couper le réseau pendant un round, le rétablir : le message d'erreur s'affiche, la partie continue
- [ ] Le lendemain à 12:00 (Paris) : une nouvelle édition apparaît, le compte à rebours était juste

## Navigateurs

- [ ] Safari iOS, Chrome Android
- [ ] Chrome, Firefox, Safari, Edge sur ordinateur

## Sécurité et confidentialité

- [ ] HTTPS forcé (redirection http → https)
- [ ] Clé secrète de l'ancien dépôt considérée comme compromise (ne plus l'utiliser nulle part)
- [ ] Page « Privacy » relue (adresse de contact à ajouter)
- [ ] Si Google Analytics est activé : la bannière de consentement apparaît et rien n'est chargé avant acceptation
- [ ] Après quelques jours stables en HTTPS : `DJANGO_HSTS_SECONDS=31536000`

## Partage et référencement

- [ ] Aperçu du lien correct (Open Graph) dans WhatsApp / Messenger / X — l'image actuelle est une capture de l'ancien site, à remplacer
- [ ] Favicon et icône d'écran d'accueil iOS visibles

## Exploitation

- [ ] Alerte si le site ne répond plus (le health check Render suffit au début, ou un service de monitoring gratuit)
- [ ] Logs consultables dans le tableau de bord de l'hébergeur
- [ ] Tâche planifiée quotidienne `generate_editions` (optionnelle : l'édition est créée à la volée si elle manque)
