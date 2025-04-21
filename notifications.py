import requests
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger('domain_monitor')


class NotificationManager:
    def __init__(self, config):
        self.config = config
        self.notification_services = []

        # Configurer les services activés
        if config.get('email_enabled', 'false').lower() == 'true':
            self.notification_services.append(EmailNotifier(config))

        if config.get('pushover_enabled', 'false').lower() == 'true':
            self.notification_services.append(PushoverNotifier(config))

        if config.get('telegram_enabled', 'false').lower() == 'true':
            self.notification_services.append(TelegramNotifier(config))

        if config.get('discord_enabled', 'false').lower() == 'true':
            self.notification_services.append(DiscordNotifier(config))

        if config.get('ntfy_enabled', 'false').lower() == 'true':
            self.notification_services.append(NtfyNotifier(config))

        if not self.notification_services:
            logger.warning("Aucun service de notification n'est activé!")

    def send_notification(self, subject, message, changes, current_status):
        """Envoie une notification à tous les services configurés"""
        results = []

        for service in self.notification_services:
            try:
                success = service.send(subject, message, changes, current_status)
                results.append((service.__class__.__name__, success))
                if success:
                    logger.info(f"Notification envoyée via {service.__class__.__name__}")
                else:
                    logger.warning(f"Échec de l'envoi via {service.__class__.__name__}")
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi via {service.__class__.__name__}: {e}")
                results.append((service.__class__.__name__, False))

        return results


class EmailNotifier:
    """Service de notification par email"""

    def __init__(self, config):
        self.config = config

        # Validation des paramètres requis
        required = ['email_from', 'email_to', 'smtp_server', 'smtp_port', 'smtp_username', 'smtp_password']
        for param in required:
            if not config.get(param):
                logger.warning(f"EmailNotifier: Paramètre manquant: {param}")

    def send(self, subject, message, changes, current_status):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config['email_from']
            msg['To'] = self.config['email_to']
            msg['Subject'] = subject

            msg.attach(MIMEText(message, 'plain'))

            server = smtplib.SMTP(self.config['smtp_server'], int(self.config['smtp_port']))
            server.starttls()
            server.login(self.config['smtp_username'], self.config['smtp_password'])
            server.send_message(msg)
            server.quit()

            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de l'email: {e}")
            return False


class PushoverNotifier:
    """Service de notification via Pushover"""

    def __init__(self, config):
        self.config = config
        self.api_url = "https://api.pushover.net/1/messages.json"

        # Validation des paramètres requis
        if not config.get('pushover_app_token') or not config.get('pushover_user_key'):
            logger.warning("PushoverNotifier: Token d'application ou clé utilisateur manquant")

    def send(self, subject, message, changes, current_status):
        try:
            payload = {
                "token": self.config['pushover_app_token'],
                "user": self.config['pushover_user_key'],
                "title": subject,
                "message": message[:1024],  # Limité à 1024 caractères
                "priority": 1  # 1 = Haute priorité
            }

            response = requests.post(self.api_url, data=payload)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Erreur Pushover: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi Pushover: {e}")
            return False


class TelegramNotifier:
    """Service de notification via Telegram"""

    def __init__(self, config):
        self.config = config
        self.bot_token = config.get('telegram_bot_token', '')
        self.chat_id = config.get('telegram_chat_id', '')
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        # Validation des paramètres requis
        if not self.bot_token or not self.chat_id:
            logger.warning("TelegramNotifier: Token de bot ou ID de chat manquant")

    def send(self, subject, message, changes, current_status):
        try:
            # Formatage du message pour Telegram (supporte Markdown)
            text = f"*{subject}*\n\n{message}"

            payload = {
                "chat_id": self.chat_id,
                "text": text[:4096],  # Limité à 4096 caractères
                "parse_mode": "Markdown"
            }

            response = requests.post(self.api_url, data=payload)
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Erreur Telegram: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi Telegram: {e}")
            return False


class DiscordNotifier:
    """Service de notification via Discord webhook"""

    def __init__(self, config):
        self.config = config
        self.webhook_url = config.get('discord_webhook_url', '')

        # Validation des paramètres requis
        if not self.webhook_url:
            logger.warning("DiscordNotifier: URL de webhook manquante")

    def send(self, subject, message, changes, current_status):
        try:
            # Formater le message pour Discord (limité à 2000 caractères)
            embed = {
                "title": subject,
                "description": message[:2000],
                "color": 16711680  # Rouge (pour attirer l'attention)
            }

            payload = {
                "embeds": [embed],
                "username": "Domain Monitor Bot"
            }

            response = requests.post(self.webhook_url, json=payload)
            if response.status_code == 204:  # Discord renvoie 204 pour succès
                return True
            else:
                logger.error(f"Erreur Discord: {response.status_code}, {response.text}")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi Discord: {e}")
            return False


class NtfyNotifier:
    """Service de notification via ntfy.sh"""

    def __init__(self, config):
        self.config = config
        self.topic = config.get('ntfy_topic', '')
        self.api_url = f"https://ntfy.sh/{self.topic}"

        # Validation des paramètres requis
        if not self.topic:
            logger.warning("NtfyNotifier: Topic manquant")

    def send(self, subject, message, changes, current_status):
        try:
            headers = {
                "Title": subject,
                "Priority": "urgent",
                "Tags": "warning,domain"
            }

            response = requests.post(
                self.api_url,
                data=message[:4096],  # Limité à 4096 caractères
                headers=headers
            )

            if response.status_code == 200:
                return True
            else:
                logger.error(f"Erreur ntfy: {response.status_code}, {response.text}")
                return False
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi ntfy: {e}")
            return False
