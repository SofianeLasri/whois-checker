#!/usr/bin/env python3
import os
import json
import logging
import argparse
from datetime import datetime
from notifications import NotificationManager
from domain_monitor import get_config

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('notification_test')


def create_test_data():
    """Crée des données de test simulant un changement de statut de domaine"""
    current_time = datetime.now().isoformat()

    previous_status = {
        "registered": True,
        "domain_name": "example.com",
        "registrar": "Old Registrar Inc.",
        "status": ["clientTransferProhibited"],
        "name_servers": ["ns1.oldhost.com", "ns2.oldhost.com"],
        "creation_date": "2020-01-01 00:00:00",
        "expiration_date": "2023-01-01 00:00:00",
        "updated_date": "2022-06-01 00:00:00",
        "dnssec": "unsigned",
        "check_time": current_time
    }

    current_status = {
        "registered": True,
        "domain_name": "example.com",
        "registrar": "New Registrar LLC",  # Changé
        "status": ["pendingDelete", "redemptionPeriod"],  # Changé
        "name_servers": ["ns1.newhost.com", "ns2.newhost.com"],  # Changé
        "creation_date": "2020-01-01 00:00:00",
        "expiration_date": "2023-01-01 00:00:00",  # Inchangé
        "updated_date": "2023-04-21 12:30:00",  # Changé
        "dnssec": "unsigned",
        "check_time": current_time
    }

    # Générer les changements détectés
    changes = {
        "registrar": {
            "from": "Old Registrar Inc.",
            "to": "New Registrar LLC"
        },
        "status": {
            "from": ["clientTransferProhibited"],
            "to": ["pendingDelete", "redemptionPeriod"]
        },
        "name_servers": {
            "from": ["ns1.oldhost.com", "ns2.oldhost.com"],
            "to": ["ns1.newhost.com", "ns2.newhost.com"]
        },
        "updated_date": {
            "from": "2022-06-01 00:00:00",
            "to": "2023-04-21 12:30:00"
        }
    }

    return previous_status, current_status, changes


def run_notification_test(services=None):
    """Exécute un test de tous les services de notification configurés"""
    try:
        logger.info("Démarrage du test de notification...")

        # Charger la configuration
        config = get_config()
        domain = config.get('domain', 'example.com')

        # Si des services spécifiques sont demandés, les activer temporairement
        if services:
            for service in services:
                config[f"{service}_enabled"] = "true"
                logger.info(f"Service {service} activé pour ce test")

        # Initialiser le gestionnaire de notifications
        notification_manager = NotificationManager(config)

        if not notification_manager.notification_services:
            logger.error("❌ ERREUR: Aucun service de notification n'est activé!")
            logger.info(
                "Veuillez activer au moins un service dans le fichier .env ou préciser un service avec l'option --service")
            return False

        # Créer des données de test
        previous_status, current_status, changes = create_test_data()

        # Préparer le sujet et le message
        subject = f"TEST - Changement détecté pour {domain}"
        message = f"""Ceci est un TEST de notification du moniteur de domaine.
Si vous recevez ce message, votre service de notification fonctionne correctement!

Simulation de changements pour {domain}:

📅 Date du test: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ CHANGEMENTS SIMULÉS:
- Registrar: Old Registrar Inc. → New Registrar LLC
- Statut: clientTransferProhibited → pendingDelete, redemptionPeriod
- Serveurs de noms: ns1.oldhost.com, ns2.oldhost.com → ns1.newhost.com, ns2.newhost.com
- Date de mise à jour: 2022-06-01 → 2023-04-21

Ce message est uniquement un TEST. Aucun changement réel n'a été détecté sur votre domaine.
"""

        # Envoyer les notifications de test
        results = notification_manager.send_notification(subject, message, changes, current_status)

        # Afficher les résultats
        success_count = 0
        for service, success in results:
            status = "✅ SUCCÈS" if success else "❌ ÉCHEC"
            logger.info(f"{status} - Notification via {service}")
            if success:
                success_count += 1

        if success_count > 0:
            logger.info(f"✅ Test réussi! {success_count}/{len(results)} notifications envoyées avec succès.")
            return True
        else:
            logger.error("❌ Test échoué! Aucune notification n'a pu être envoyée.")
            return False

    except Exception as e:
        logger.error(f"❌ Erreur lors du test: {e}")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test des services de notification')
    parser.add_argument('--service', '-s', action='append',
                        choices=['email', 'pushover', 'telegram', 'discord', 'ntfy'],
                        help='Service(s) spécifique(s) à tester (par défaut: tous les services configurés)')
    args = parser.parse_args()

    success = run_notification_test(args.service)
    exit(0 if success else 1)
