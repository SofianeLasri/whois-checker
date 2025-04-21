import whois
import time
import os
import json
import logging
from datetime import datetime
from notifications import NotificationManager

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('domain_monitor')


# Lecture de la configuration
def get_config():
    config = {
        'domain': os.environ.get('DOMAIN', ''),
        'check_interval': int(os.environ.get('CHECK_INTERVAL', 3600)),  # Default: 1 heure
        'history_file': os.environ.get('HISTORY_FILE', '/app/data/domain_history.json'),

        # Email config
        'email_enabled': os.environ.get('EMAIL_ENABLED', 'false'),
        'email_from': os.environ.get('EMAIL_FROM', ''),
        'email_to': os.environ.get('EMAIL_TO', ''),
        'smtp_server': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
        'smtp_port': os.environ.get('SMTP_PORT', '587'),
        'smtp_username': os.environ.get('SMTP_USERNAME', ''),
        'smtp_password': os.environ.get('SMTP_PASSWORD', ''),

        # Pushover config
        'pushover_enabled': os.environ.get('PUSHOVER_ENABLED', 'false'),
        'pushover_app_token': os.environ.get('PUSHOVER_APP_TOKEN', ''),
        'pushover_user_key': os.environ.get('PUSHOVER_USER_KEY', ''),

        # Telegram config
        'telegram_enabled': os.environ.get('TELEGRAM_ENABLED', 'false'),
        'telegram_bot_token': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
        'telegram_chat_id': os.environ.get('TELEGRAM_CHAT_ID', ''),

        # Discord config
        'discord_enabled': os.environ.get('DISCORD_ENABLED', 'false'),
        'discord_webhook_url': os.environ.get('DISCORD_WEBHOOK_URL', ''),

        # Ntfy config
        'ntfy_enabled': os.environ.get('NTFY_ENABLED', 'false'),
        'ntfy_topic': os.environ.get('NTFY_TOPIC', '')
    }

    # Vérification des paramètres requis
    if not config['domain']:
        raise ValueError("Le domaine à surveiller n'est pas configuré")

    return config


# [Le reste du code pour check_domain_status, detect_changes, save_history, et load_history reste inchangé]

# Fonction pour préparer le message de notification
def prepare_notification_message(domain, changes, current_status):
    subject = f"Changement détecté pour le domaine {domain}"

    # Corps du message
    body = f"Changements détectés pour {domain} le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}:\n\n"

    for key, change in changes.items():
        body += f"{key}:\n"
        body += f"  - Avant: {change['from']}\n"
        body += f"  - Après: {change['to']}\n\n"

    body += "\nStatut actuel du domaine:\n"

    # Afficher d'abord les champs les plus importants
    important_fields = ['registered', 'domain_name', 'registrar', 'expiration_date', 'status']
    for key in important_fields:
        if key in current_status:
            body += f"{key}: {current_status[key]}\n"

    return subject, body


# Fonction principale
def main():
    try:
        config = get_config()
        logger.info(f"Démarrage de la surveillance du domaine {config['domain']}")

        # Initialiser le gestionnaire de notifications
        notification_manager = NotificationManager(config)

        while True:
            logger.info(f"Vérification du statut de {config['domain']}")

            # Charger l'historique
            previous_status = load_history(config)

            # Vérifier le statut actuel
            current_status = check_domain_status(config['domain'])

            # Détecter les changements
            changes = detect_changes(previous_status, current_status)

            # Si des changements sont détectés, envoyer une notification
            if changes and len(changes) > 0 and not (len(changes) == 1 and "message" in changes):
                logger.info(f"Changements détectés: {json.dumps(changes, indent=2)}")

                # Préparer le message de notification
                subject, message = prepare_notification_message(config['domain'], changes, current_status)

                # Envoyer les notifications via tous les canaux configurés
                results = notification_manager.send_notification(subject, message, changes, current_status)

                # Afficher les résultats
                for service, success in results:
                    status = "succès" if success else "échec"
                    logger.info(f"Notification via {service}: {status}")
            else:
                logger.info("Aucun changement détecté")

            # Sauvegarder l'historique
            save_history(config, current_status)

            # Attendre avant la prochaine vérification
            next_check = datetime.now().timestamp() + config['check_interval']
            next_check_time = datetime.fromtimestamp(next_check).strftime('%Y-%m-%d %H:%M:%S')
            logger.info(f"Prochaine vérification prévue à {next_check_time}")

            time.sleep(config['check_interval'])

    except KeyboardInterrupt:
        logger.info("Interruption manuelle, arrêt du bot")
    except Exception as e:
        logger.error(f"Erreur dans la fonction principale: {e}")
        raise


if __name__ == "__main__":
    main()
