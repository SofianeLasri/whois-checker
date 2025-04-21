FROM python:3.9-slim

# Créer un utilisateur non-root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances et installer les packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Créer le répertoire de données et définir les permissions
RUN mkdir -p /app/data && chown -R appuser:appuser /app

# Copier le code source
COPY domain_monitor.py notifications.py test_notifications.py ./
RUN chmod +x test_notifications.py

# Script de démarrage conditionnel
COPY start.sh .
RUN chmod +x start.sh

# Définir l'utilisateur non-root
USER appuser

# Créer un volume pour la persistance des données
VOLUME /app/data

# Exécuter le script approprié selon le mode
CMD ["./start.sh"]
