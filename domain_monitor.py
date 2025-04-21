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


def normalize_whois_value(value):
    if value is None:
        return None

    # Traitement des listes
    if isinstance(value, list):
        # Tri des listes pour une comparaison cohérente
        if all(isinstance(x, str) for x in value):
            return sorted([str(x).lower() for x in value])
        return value

    # Traitement des dates
    if hasattr(value, 'strftime'):
        return value.strftime('%Y-%m-%d %H:%M:%S')

    # Autres types
    return str(value)

# Fonction pour vérifier le statut du domaine
def check_domain_status(domain):
    try:
        w = whois.whois(domain)

        # Extraire les informations importantes
        status = {}

        # Vérifier si le domaine existe
        if w.domain_name is None:
            status['registered'] = False
            status['availability'] = "Le domaine semble être disponible"
        else:
            status['registered'] = True

            # Récupérer les informations importantes
            important_fields = [
                'domain_name', 'registrar', 'whois_server', 'status',
                'name_servers', 'creation_date', 'expiration_date',
                'updated_date', 'dnssec'
            ]

            for field in important_fields:
                if hasattr(w, field):
                    status[field] = normalize_whois_value(getattr(w, field))

        status['raw_text'] = w.text if hasattr(w, 'text') else "Pas de texte brut disponible"
        status['check_time'] = datetime.now().isoformat()

        return status
    except Exception as e:
        logger.error(f"Erreur lors de la vérification du domaine {domain}: {e}")
        return {
            'error': str(e),
            'check_time': datetime.now().isoformat()
        }


# Fonction pour comparer les statuts et détecter les changements
def detect_changes(previous_status, current_status):
    changes = {}

    if 'error' in current_status:
        return {"error": current_status['error']}

    if not previous_status:
        return {"message": "Premier contrôle, pas d'historique disponible"}

    # Ignorer certains champs dans la comparaison
    skip_fields = ['check_time', 'raw_text']

    for key in current_status:
        if key in skip_fields:
            continue

        if key not in previous_status:
            changes[key] = {
                'from': None,
                'to': current_status[key]
            }
        elif previous_status[key] != current_status[key]:
            changes[key] = {
                'from': previous_status[key],
                'to': current_status[key]
            }

    # Vérifier les champs disparus
    for key in previous_status:
        if key in skip_fields:
            continue

        if key not in current_status:
            changes[key] = {
                'from': previous_status[key],
                'to': None
            }

    return changes

# Fonction pour sauvegarder l'historique
def save_history(config, status):
    try:
        # Créer le répertoire de données si nécessaire
        os.makedirs(os.path.dirname(config['history_file']), exist_ok=True)

        with open(config['history_file'], 'w') as f:
            json.dump(status, f, indent=2)
        logger.info(f"Historique sauvegardé dans {config['history_file']}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la sauvegarde de l'historique: {e}")
        return False


# Fonction pour charger l'historique
def load_history(config):
    try:
        if os.path.exists(config['history_file']):
            with open(config['history_file'], 'r') as f:
                return json.load(f)
        return None
    except Exception as e:
        logger.error(f"Erreur lors du chargement de l'historique: {e}")
        return None

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
