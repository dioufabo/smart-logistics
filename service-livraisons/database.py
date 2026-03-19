from pymongo import MongoClient
import os

# URL de connexion MongoDB (via variable d'environnement)
MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo-livraisons:27017")
MONGO_DB  = os.getenv("MONGO_DB", "livraisons_db")

# Client MongoDB partagé
client = MongoClient(MONGO_URL)
db = client[MONGO_DB]

# Collections (équivalent des tables en SQL)
livraisons_collection = db["livraisons"]
tracking_collection   = db["tracking"]   # historique des coordonnées GPS
