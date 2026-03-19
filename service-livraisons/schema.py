import strawberry
from typing import List, Optional
from datetime import datetime
from database import livraisons_collection, tracking_collection
from bson import ObjectId


# ============================================================
# TYPES GraphQL (ce que le client peut recevoir)
# ============================================================

@strawberry.type
class CoordonneeGPS:
    latitude: float
    longitude: float
    timestamp: str
    note: Optional[str] = None

@strawberry.type
class Livraison:
    id: str
    commande_id: int
    client: str
    adresse: str
    statut: str                          # en_preparation, en_transit, livre, echec
    livreur: Optional[str] = None
    historique_gps: List[CoordonneeGPS] = strawberry.field(default_factory=list)
    created_at: str


# ============================================================
# INPUTS GraphQL (ce que le client envoie dans les mutations)
# ============================================================

@strawberry.input
class MajStatutInput:
    livraison_id: str
    nouveau_statut: str
    livreur: Optional[str] = None

@strawberry.input
class AjoutGPSInput:
    livraison_id: str
    latitude: float
    longitude: float
    note: Optional[str] = None


# ============================================================
# HELPER : convertir un document MongoDB en type Livraison
# ============================================================

def doc_to_livraison(doc: dict) -> Livraison:
    gps_list = [
        CoordonneeGPS(
            latitude=g["latitude"],
            longitude=g["longitude"],
            timestamp=g["timestamp"],
            note=g.get("note")
        )
        for g in doc.get("historique_gps", [])
    ]
    return Livraison(
        id=str(doc["_id"]),
        commande_id=doc["commande_id"],
        client=doc["client"],
        adresse=doc["adresse"],
        statut=doc["statut"],
        livreur=doc.get("livreur"),
        historique_gps=gps_list,
        created_at=doc["created_at"]
    )


# ============================================================
# QUERIES (lecture)
# ============================================================

@strawberry.type
class Query:

    @strawberry.field(description="Retourne toutes les livraisons")
    def livraisons(self) -> List[Livraison]:
        docs = livraisons_collection.find()
        return [doc_to_livraison(d) for d in docs]

    @strawberry.field(description="Retourne une livraison par son ID")
    def livraison(self, id: str) -> Optional[Livraison]:
        doc = livraisons_collection.find_one({"_id": ObjectId(id)})
        if not doc:
            return None
        return doc_to_livraison(doc)

    @strawberry.field(description="Retourne la livraison liée à une commande")
    def livraison_par_commande(self, commande_id: int) -> Optional[Livraison]:
        doc = livraisons_collection.find_one({"commande_id": commande_id})
        if not doc:
            return None
        return doc_to_livraison(doc)

    @strawberry.field(description="Historique GPS d'une livraison")
    def historique_gps(self, livraison_id: str) -> List[CoordonneeGPS]:
        doc = livraisons_collection.find_one({"_id": ObjectId(livraison_id)})
        if not doc:
            return []
        return [
            CoordonneeGPS(
                latitude=g["latitude"],
                longitude=g["longitude"],
                timestamp=g["timestamp"],
                note=g.get("note")
            )
            for g in doc.get("historique_gps", [])
        ]


# ============================================================
# MUTATIONS (écriture)
# ============================================================

@strawberry.type
class Mutation:

    @strawberry.mutation(description="Met à jour le statut d'une livraison")
    def mettre_a_jour_statut(self, data: MajStatutInput) -> Livraison:
        statuts_valides = ["en_preparation", "en_transit", "livre", "echec"]
        if data.nouveau_statut not in statuts_valides:
            raise ValueError(f"Statut invalide. Valeurs possibles : {statuts_valides}")

        update_data = {"statut": data.nouveau_statut}
        if data.livreur:
            update_data["livreur"] = data.livreur

        result = livraisons_collection.find_one_and_update(
            {"_id": ObjectId(data.livraison_id)},
            {"$set": update_data},
            return_document=True
        )
        if not result:
            raise ValueError("Livraison introuvable")
        return doc_to_livraison(result)

    @strawberry.mutation(description="Ajoute une coordonnée GPS à l'historique de tracking")
    def ajouter_coordonnee_gps(self, data: AjoutGPSInput) -> Livraison:
        nouvelle_coord = {
            "latitude": data.latitude,
            "longitude": data.longitude,
            "timestamp": datetime.utcnow().isoformat(),
            "note": data.note
        }
        result = livraisons_collection.find_one_and_update(
            {"_id": ObjectId(data.livraison_id)},
            {"$push": {"historique_gps": nouvelle_coord}},
            return_document=True
        )
        if not result:
            raise ValueError("Livraison introuvable")
        return doc_to_livraison(result)


# Schéma GraphQL final
schema = strawberry.Schema(query=Query, mutation=Mutation)
