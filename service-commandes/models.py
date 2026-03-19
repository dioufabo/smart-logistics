from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class Produit(Base):
    """Catalogue des produits disponibles"""
    __tablename__ = "produits"

    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String(100), nullable=False)
    description = Column(String(500))
    prix = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relation : un produit peut apparaître dans plusieurs commandes
    lignes_commande = relationship("LigneCommande", back_populates="produit")


class Commande(Base):
    """Commandes passées par les clients"""
    __tablename__ = "commandes"

    id = Column(Integer, primary_key=True, index=True)
    client_nom = Column(String(100), nullable=False)
    client_email = Column(String(100), nullable=False)
    statut = Column(String(50), default="en_attente")  # en_attente, confirmee, expediee, livree
    adresse_livraison = Column(String(300), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relation : une commande contient plusieurs lignes
    lignes = relationship("LigneCommande", back_populates="commande", cascade="all, delete")


class LigneCommande(Base):
    """Détail des produits dans une commande"""
    __tablename__ = "lignes_commande"

    id = Column(Integer, primary_key=True, index=True)
    commande_id = Column(Integer, ForeignKey("commandes.id"), nullable=False)
    produit_id = Column(Integer, ForeignKey("produits.id"), nullable=False)
    quantite = Column(Integer, nullable=False, default=1)
    prix_unitaire = Column(Float, nullable=False)

    commande = relationship("Commande", back_populates="lignes")
    produit = relationship("Produit", back_populates="lignes_commande")
