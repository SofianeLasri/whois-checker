#!/bin/bash

# Vérifier si le mode test est activé
if [ "$TEST_MODE" = "true" ]; then
    echo "Démarrage en mode TEST..."

    # Si un service spécifique est demandé pour le test
    if [ -n "$TEST_SERVICE" ]; then
        echo "Test du service: $TEST_SERVICE"
        python test_notifications.py --service "$TEST_SERVICE"
    else
        echo "Test de tous les services configurés"
        python test_notifications.py
    fi
else
    echo "Démarrage du moniteur de domaine en mode normal..."
    python domain_monitor.py
fi
