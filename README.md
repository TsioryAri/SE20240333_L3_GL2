# PharmaGest — application Django de gestion de pharmacie

PharmaGest est une application web de gestion de pharmacie développée avec Django. Cette version reprend le projet existant et étend ses fonctions : catalogue, achats multi-lignes, lots, inventaire, ventes, retours, utilisateurs par rôle et rapports.

> **État du livrable :** version de développement enrichie. Les fichiers Python ont été contrôlés syntaxiquement dans l'environnement de préparation, mais l'environnement de préparation ne dispose pas de Django et ne permet pas d'exécuter `manage.py check` ni les tests Django. Il faut donc effectuer la recette indiquée ci-dessous sur Debian avant toute utilisation réelle. Ce logiciel n'est pas un logiciel médical/pharmaceutique certifié.

## Fonctionnalités présentes

- Authentification Django et interface d'administration.
- Tableau de bord : ventes du jour, chiffre d'affaires, alertes de stock faible et péremptions.
- Gestion des catégories, médicaments, fournisseurs et clients : consultation, création et modification.
- Recherche de médicaments par nom ou code.
- Gestion des lots, dates de péremption et quantités.
- Réception d'achats avec plusieurs lignes et création/mise à jour des lots.
- Sortie de stock à la vente selon FEFO (lot dont la péremption est la plus proche en premier), sans utiliser les lots périmés.
- Vente multi-lignes, client facultatif, choix du mode de paiement et reçu PDF.
- Retours avec contrôle de la quantité retournée et réintégration facultative après contrôle physique.
- Ajustements d'inventaire avec journal des mouvements.
- Journal d'audit pour les opérations commerciales et les ajustements.
- Rôles : Administrateur, Pharmacien, Gestionnaire de stock et Caissier.
- Exports CSV des stocks et ventes.
- Tests automatisés des services de vente, achat, retour, FEFO et ajustement de stock.
- Configuration SQLite par défaut et option PostgreSQL via variables d'environnement.

## Prérequis Debian 13

- Python 3.13 recommandé.
- pip et `venv`.
- Accès Internet pour installer les dépendances.
- Pour PostgreSQL : serveur PostgreSQL et compte/base dédiés.

## Installation locale

Depuis le dossier extrait `PharmaGest` :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python manage.py makemigrations pharmacie
python manage.py migrate
python manage.py createsuperuser
python manage.py setup_roles
python manage.py test
python manage.py check
python manage.py runserver
```

Ouvrir ensuite : http://127.0.0.1:8000/

La commande `makemigrations pharmacie` génère la migration initiale correspondant aux modèles de cette archive. Conserver ensuite les migrations dans le dépôt ; ne pas les supprimer pour réinitialiser une base de données de production.

## Premier paramétrage

1. Se connecter avec le compte superutilisateur créé pendant l'installation.
2. La commande `python manage.py setup_roles` crée les groupes et permissions de base.
3. Dans **Utilisateurs**, créer les comptes de l'équipe et attribuer un rôle.
4. Créer les catégories, fournisseurs et médicaments.
5. Enregistrer les achats/réceptions ; chaque ligne doit avoir un numéro de lot et une date de péremption future.
6. Vérifier le stock et les dates de péremption avant les ventes.
7. Utiliser les ajustements uniquement après inventaire physique et en renseignant le motif.

## Rôles applicatifs

- **Administrateur** : accès complet aux écrans applicatifs et à l'administration Django.
- **Pharmacien** : catalogue, clients, fournisseurs, achats, stock, ventes, retours et rapports.
- **Gestionnaire de stock** : catalogue, fournisseurs, achats, stock et rapports.
- **Caissier** : tableau de bord, clients, ventes et retours.

Les contrôles applicatifs sont définis dans `pharmacie/permissions.py`. Les groupes Django et leurs permissions natives sont créés par `setup_roles`. Vérifier les rôles et adapter les autorisations au fonctionnement réel de l'établissement.

## Configuration PostgreSQL (facultatif)

Définir les variables d'environnement avant de lancer Django :

```bash
export DB_ENGINE=postgres
export DB_NAME=pharmagest
export DB_USER=pharmagest
export DB_PASSWORD='mot-de-passe-fort'
export DB_HOST=127.0.0.1
export DB_PORT=5432
```

Le paquet `psycopg` est inclus dans `requirements.txt`. Créer préalablement la base et le rôle PostgreSQL, puis exécuter `python manage.py migrate`.

## Paramètres de sécurité

Pour un déploiement réel, définir au minimum `DJANGO_SECRET_KEY` avec une valeur secrète aléatoire, `DJANGO_DEBUG=0` et `DJANGO_ALLOWED_HOSTS` avec les noms de domaine autorisés. Configurer HTTPS, les sauvegardes automatiques, la surveillance, les mises à jour de sécurité et les droits d'accès au serveur. Ne jamais publier le fichier `.env` ni les identifiants de base de données.

## Vérification avant utilisation réelle

- Exécuter `python manage.py check` et `python manage.py test`.
- Tester manuellement création/réception d'un achat multi-lignes, vente avec stock suffisant et insuffisant, lots périmés, retours partiels et ajustements.
- Tester chaque rôle avec un compte non-superutilisateur et vérifier les accès refusés.
- Tester la restauration d'une sauvegarde et les accès simultanés à la caisse.
- Vérifier les règles locales relatives aux pharmacies, à la délivrance, à la facturation, aux données personnelles et à la conservation des historiques avec les responsables compétents.

## Limites connues de cette version

- Les migrations ne sont pas pré-générées dans l'archive : elles sont créées à l'installation avec `makemigrations`.
- Les exports fournis sont CSV ; les états comptables avancés, tableaux de bord analytiques et exports Excel restent à développer selon les besoins.
- Le paiement est enregistré par mode, sans intégration à un opérateur Mobile Money ni rapprochement bancaire.
- Les retours sont suivis et peuvent réintégrer le stock, mais le workflow financier de remboursement/avoir doit être défini et validé avant exploitation.
- L'application nécessite une recette fonctionnelle, sécurité et métier avant une mise en production.
