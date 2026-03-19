#!/bin/bash
echo "🚀 Démarrage du service commandes..."
exec uvicorn main:app --host 0.0.0.0 --port 8000
