from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import models
import database
import httpx
import os

# Création de l'application FastAPI
app = FastAPI(
    title="Smart-Logistics - Service Commandes",
    description="Gestion des produits et des commandes clients",
    version="1.0.0"
)

# URL du service livraisons (communication inter-services)
LIVRAISONS_URL = os.getenv("LIVRAISONS_URL", "http://service-livraisons:8001")

# --- Création des tables au démarrage ---
@app.on_event("startup")
def startup():
    models.Base.metadata.create_all(bind=database.engine)


# ============================================================
# SCHEMAS Pydantic (validation des données entrantes/sortantes)
# ============================================================

class LigneCommandeIn(BaseModel):
    produit_id: int
    quantite: int

class CommandeCreate(BaseModel):
    client_nom: str
    client_email: str
    adresse_livraison: str
    lignes: List[LigneCommandeIn]

class LigneCommandeOut(BaseModel):
    id: int
    produit_id: int
    quantite: int
    prix_unitaire: float
    class Config:
        from_attributes = True

class CommandeOut(BaseModel):
    id: int
    client_nom: str
    client_email: str
    statut: str
    adresse_livraison: str
    lignes: List[LigneCommandeOut]
    class Config:
        from_attributes = True

class ProduitCreate(BaseModel):
    nom: str
    description: Optional[str] = ""
    prix: float
    stock: int

class ProduitOut(BaseModel):
    id: int
    nom: str
    description: Optional[str]
    prix: float
    stock: int
    class Config:
        from_attributes = True


# ============================================================
# ENDPOINTS PRODUITS
# ============================================================

@app.get("/produits", response_model=List[ProduitOut], tags=["Produits"])
def lister_produits(db: Session = Depends(database.get_db)):
    """Retourne la liste de tous les produits du catalogue"""
    return db.query(models.Produit).all()

@app.post("/produits", response_model=ProduitOut, status_code=201, tags=["Produits"])
def creer_produit(produit: ProduitCreate, db: Session = Depends(database.get_db)):
    """Ajoute un nouveau produit au catalogue"""
    nouveau = models.Produit(**produit.dict())
    db.add(nouveau)
    db.commit()
    db.refresh(nouveau)
    return nouveau


# ============================================================
# ENDPOINTS COMMANDES (GET / POST / DELETE)
# ============================================================

@app.get("/orders", response_model=List[CommandeOut], tags=["Commandes"])
def lister_commandes(db: Session = Depends(database.get_db)):
    """Retourne toutes les commandes"""
    return db.query(models.Commande).all()

@app.get("/orders/{order_id}", response_model=CommandeOut, tags=["Commandes"])
def obtenir_commande(order_id: int, db: Session = Depends(database.get_db)):
    """Retourne une commande spécifique par son ID"""
    commande = db.query(models.Commande).filter(models.Commande.id == order_id).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return commande

@app.post("/orders", response_model=CommandeOut, status_code=201, tags=["Commandes"])
def creer_commande(commande_data: CommandeCreate, db: Session = Depends(database.get_db)):
    """
    Crée une nouvelle commande.
    Vérifie le stock des produits, crée la commande,
    puis notifie le service Livraisons pour créer un suivi.
    """
    lignes_a_ajouter = []

    # Vérification du stock pour chaque produit
    for ligne in commande_data.lignes:
        produit = db.query(models.Produit).filter(models.Produit.id == ligne.produit_id).first()
        if not produit:
            raise HTTPException(status_code=404, detail=f"Produit {ligne.produit_id} introuvable")
        if produit.stock < ligne.quantite:
            raise HTTPException(status_code=400, detail=f"Stock insuffisant pour {produit.nom}")
        lignes_a_ajouter.append((produit, ligne.quantite))

    # Création de la commande
    nouvelle_commande = models.Commande(
        client_nom=commande_data.client_nom,
        client_email=commande_data.client_email,
        adresse_livraison=commande_data.adresse_livraison,
    )
    db.add(nouvelle_commande)
    db.flush()  # pour obtenir l'ID avant le commit

    # Ajout des lignes et déduction du stock
    for produit, quantite in lignes_a_ajouter:
        ligne = models.LigneCommande(
            commande_id=nouvelle_commande.id,
            produit_id=produit.id,
            quantite=quantite,
            prix_unitaire=produit.prix
        )
        db.add(ligne)
        produit.stock -= quantite  # mise à jour du stock

    db.commit()
    db.refresh(nouvelle_commande)

    # Notification asynchrone au service Livraisons
    try:
        with httpx.Client(timeout=3.0) as client:
            client.post(f"{LIVRAISONS_URL}/init-livraison", json={
                "commande_id": nouvelle_commande.id,
                "adresse": commande_data.adresse_livraison,
                "client": commande_data.client_nom
            })
    except Exception:
        # On ne bloque pas la commande si le service livraisons est indisponible
        pass

    return nouvelle_commande

@app.delete("/orders/{order_id}", status_code=204, tags=["Commandes"])
def supprimer_commande(order_id: int, db: Session = Depends(database.get_db)):
    """Supprime une commande (et ses lignes en cascade)"""
    commande = db.query(models.Commande).filter(models.Commande.id == order_id).first()
    if not commande:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    db.delete(commande)
    db.commit()
    return None

@app.get("/health", tags=["Santé"])
def health_check():
    """Endpoint de santé pour Docker Swarm"""
    return {"status": "ok", "service": "commandes"}
