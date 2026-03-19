# Image de base légère Python
FROM python:3.11-slim

# Répertoire de travail dans le container
WORKDIR /app

# Dépendances en premier (cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code source
COPY . .

# Port exposé
EXPOSE 8001

# Démarrage sur le port 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
