# Smart-Logistics 

Plateforme distribuée de gestion de livraisons composée de deux micro-services Python communiquant via Docker Swarm.

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                  Réseau Overlay Docker Swarm                      │
│                      (logistics-net)                              │
│                                                                   │
│  ┌─────────────────────────┐   HTTP    ┌──────────────────────┐  │
│  │   Service Commandes      │ ────────▶ │  Service Livraisons   │  │
│  │   FastAPI + PostgreSQL   │           │  GraphQL + MongoDB    │  │
│  │   Port 8000  (3 replicas)│           │  Port 8001 (3 replicas│  │
│  └────────────┬────────────┘           └──────────┬───────────┘  │
│               │                                    │              │
│               ▼                                    ▼              │
│         PostgreSQL 15                          MongoDB 7          │
│           Port 5432                            Port 27017         │
│                                                                   │
│                     Portainer  :9000                              │
└──────────────────────────────────────────────────────────────────┘
```

## Structure du projet

```
smart-logistics/
├── service-commandes/          # API REST FastAPI
│   ├── main.py                 # Endpoints GET/POST/DELETE /orders
│   ├── models.py               # Tables SQLAlchemy (Produit, Commande, Ligne)
│   ├── database.py             # Connexion PostgreSQL avec retry automatique
│   ├── entrypoint.sh           # Script de démarrage
│   ├── requirements.txt
│   └── Dockerfile
├── service-livraisons/         # API GraphQL Strawberry
│   ├── main.py                 # Serveur FastAPI + endpoint /init-livraison
│   ├── schema.py               # Queries et Mutations GraphQL
│   ├── database.py             # Connexion MongoDB
│   ├── requirements.txt
│   └── Dockerfile
├── docker-stack.yml            # Stack Swarm (replicas, réseau, volumes)
└── README.md
```

---

## Prérequis

- **Docker Desktop** installé et lancé (Windows/Mac) ou **Docker Engine** (Linux)
- **Git** installé
- Espace disque : minimum **4 GB libres** pour Docker
  > Sur Docker Desktop : Settings → Resources → Advanced → Virtual disk limit → mettre **60 GB minimum**

---

## Déploiement pas à pas

### Étape 1 — Cloner le projet

```bash
git clone <url-du-repo>
cd smart-logistics
```

### Étape 2 — Construire les images Docker

> Cette étape télécharge Python et installe les dépendances (~2-5 min par image)

```bash
# Image du service commandes
docker build -t smart-logistics/service-commandes:latest ./service-commandes

# Image du service livraisons
docker build -t smart-logistics/service-livraisons:latest ./service-livraisons
```

Vérifier que les images sont bien créées :
```bash
docker images | grep smart-logistics
```
Résultat attendu :
```
smart-logistics/service-commandes    latest    abc123...   2 min ago   ~250MB
smart-logistics/service-livraisons   latest    def456...   1 min ago   ~230MB
```

### Étape 3 — Initialiser Docker Swarm

```bash
docker swarm init
```

> Si tu vois `This node is already part of a swarm` → le Swarm est déjà actif, passe à l'étape suivante.

Résultat attendu :
```
Swarm initialized: current node (xxx) is now a manager.
```

### Étape 4 — Déployer la stack

```bash
docker stack deploy -c docker-stack.yml smart-logistics
```

Résultat attendu :
```
Creating network smart-logistics_logistics-net
Creating service smart-logistics_postgres-commandes
Creating service smart-logistics_mongo-livraisons
Creating service smart-logistics_service-commandes
Creating service smart-logistics_service-livraisons
Creating service smart-logistics_portainer
```

### Étape 5 — Vérifier le déploiement

```bash
docker stack services smart-logistics
```

Résultat attendu (tous les services doivent être UP) :
```
NAME                                 REPLICAS   IMAGE
smart-logistics_mongo-livraisons     1/1        mongo:7
smart-logistics_portainer            1/1        portainer/portainer-ce:latest
smart-logistics_postgres-commandes   1/1        postgres:15-alpine
smart-logistics_service-commandes    3/3        smart-logistics/service-commandes:latest
smart-logistics_service-livraisons   3/3        smart-logistics/service-livraisons:latest
```

> Si un service affiche `0/3` ou `0/1`, voir la section **Dépannage** ci-dessous.

---

## Accéder aux services

| Service            | URL                           | Description                    |
|--------------------|-------------------------------|--------------------------------|
| API Commandes      | http://localhost:8000/docs    | Interface Swagger interactive  |
| API Livraisons     | http://localhost:8001/graphql | Playground GraphQL             |
| Portainer          | http://localhost:9000         | Monitoring Docker Swarm        |

> **Portainer** : au premier accès, créer un compte admin (password ≥ 12 caractères).

Username : admin
Password : admin1234567 (minimum 12 caractères)
> Si Portainer affiche "session expirée" : `docker service update --force smart-logistics_portainer`

---

## Tester les APIs

### Créer un produit
```bash
curl -X POST http://localhost:8000/produits \
  -H "Content-Type: application/json" \
  -d '{"nom": "Laptop Dell", "description": "PC portable", "prix": 999.99, "stock": 10}'
```

### Créer une commande
> Remplacer `produit_id` par l'`id` retourné ci-dessus

```bash
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "client_nom": "Alice Dupont",
    "client_email": "alice@example.com",
    "adresse_livraison": "12 Rue de Dakar, Sénégal",
    "lignes": [{"produit_id": 1, "quantite": 2}]
  }'
```

> La commande notifie automatiquement le Service Livraisons via `POST /init-livraison`

### Lister les commandes
```bash
curl http://localhost:8000/orders
```

### Supprimer une commande
```bash
curl -X DELETE http://localhost:8000/orders/1
```

### Query GraphQL — Lister les livraisons
Dans le navigateur sur http://localhost:8001/graphql :
```graphql
query {
  livraisons {
    id
    commandeId
    client
    statut
    adresse
    historiqueGps {
      latitude
      longitude
      timestamp
    }
  }
}
```

### Mutation GraphQL — Mettre à jour le statut
```graphql
mutation {
  mettreAJourStatut(data: {
    livraisonId: "VOTRE_ID_ICI",
    nouveauStatut: "en_transit",
    livreur: "Bob Martin"
  }) {
    id
    statut
    livreur
  }
}
```

### Mutation GraphQL — Ajouter une coordonnée GPS
```graphql
mutation {
  ajouterCoordonneeGps(data: {
    livraisonId: "VOTRE_ID_ICI",
    latitude: 14.6937,
    longitude: -17.4441,
    note: "Arrivée à Dakar"
  }) {
    id
    historiqueGps {
      latitude
      longitude
      timestamp
    }
  }
}
```

---

## Test de résilience

Docker Swarm recrée automatiquement un container tué :

```bash
# 1. Récupérer l'ID d'un container service-commandes
docker ps | grep service-commandes

# 2. Tuer manuellement un container (remplacer CONTAINER_ID)
docker kill CONTAINER_ID

# 3. Vérifier que Swarm maintient 3/3 replicas (attendre ~10s)
sleep 12 && docker stack services smart-logistics
```

Le service reste à **3/3** — c'est la preuve de la haute disponibilité.

---

## Mettre à jour un service (zero downtime)

```bash
# Rebuild l'image
docker build -t smart-logistics/service-commandes:latest ./service-commandes

# Déployer la mise à jour (1 replica à la fois, délai 10s)
docker service update --force smart-logistics_service-commandes
```

---

## Surveiller les logs

```bash
# Logs du service commandes (en direct)
docker service logs -f smart-logistics_service-commandes

# Logs du service livraisons
docker service logs -f smart-logistics_service-livraisons

# Logs de tous les containers d'un service
docker service ps smart-logistics_service-commandes
```

---

## Arrêter et nettoyer

```bash
# Arrêter la stack (garde les volumes)
docker stack rm smart-logistics

# Quitter le Swarm
docker swarm leave --force

# Supprimer les volumes (efface toutes les données)
docker volume rm smart-logistics_postgres_data smart-logistics_mongo_data

# Nettoyage complet Docker (images, cache, volumes inutilisés)
docker system prune -a --volumes -f
```

---# smart-logistics
