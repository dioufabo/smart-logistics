from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from strawberry.fastapi import GraphQLRouter
from schema import schema
from database import livraisons_collection
from datetime import datetime

# Application FastAPI qui héberge GraphQL
app = FastAPI(
    title="Smart-Logistics - Service Livraisons",
    description="Suivi en temps réel des livraisons (GraphQL + MongoDB)",
    version="1.0.0"
)

# Montage de l'interface GraphQL sur /graphql
graphql_app = GraphQLRouter(schema)
app.include_router(graphql_app, prefix="/graphql")


# ============================================================
# ENDPOINT REST interne : appelé par le service Commandes
# quand une nouvelle commande est créée
# ============================================================

@app.post("/init-livraison", tags=["Interne"])
async def init_livraison(request: Request):
    """
    Crée automatiquement une entrée de livraison
    lorsque le service Commandes crée une commande.
    """
    data = await request.json()
    commande_id = data.get("commande_id")
    adresse     = data.get("adresse", "")
    client      = data.get("client", "")

    # Vérifier si une livraison existe déjà pour cette commande
    existante = livraisons_collection.find_one({"commande_id": commande_id})
    if existante:
        return JSONResponse({"message": "Livraison déjà existante"}, status_code=200)

    # Créer la livraison avec statut initial
    nouvelle = {
        "commande_id": commande_id,
        "client": client,
        "adresse": adresse,
        "statut": "en_preparation",
        "livreur": None,
        "historique_gps": [],
        "created_at": datetime.utcnow().isoformat()
    }
    livraisons_collection.insert_one(nouvelle)
    return JSONResponse({"message": "Livraison initialisée", "commande_id": commande_id}, status_code=201)


@app.get("/health", tags=["Santé"])
def health_check():
    """Endpoint de santé pour Docker Swarm"""
    return {"status": "ok", "service": "livraisons"}
