# Image de base : python:3.12-alpine
# Justification : Alpine (~50 Mo) est bien plus légère que l'image complète
# (~1 Go). Nos dépendances (flask, redis-py, gunicorn) sont du Python pur :
# pas de compilation, donc pas de problème de compatibilité musl.
FROM python:3.12-alpine

# Pas de .pyc inutiles, logs affichés immédiatement
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# 1) On copie d'abord SEULEMENT requirements.txt :
#    tant que les dépendances ne changent pas, cette couche (et le pip install)
#    reste en cache Docker, même si app.py change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Puis le code source (couche qui change souvent, donc en dernier)
COPY app.py .

# Utilisateur non-root : limite l'impact d'une compromission
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
USER appuser

EXPOSE 5000

# CMD : commande exécutée au démarrage du conteneur (forme exec, sans shell)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]