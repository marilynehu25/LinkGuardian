"""Configuration Celery pour LinkGuardian - VERSION CORRIGÉE"""

from celery import Celery

# Créer l'instance Celery
celery = Celery(
    "linkguardian",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

# Configuration avec rate limiting et retry
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Paris",
    enable_utc=True,
    # ⚙️ GESTION DES TÂCHES - CORRECTION DU PROBLÈME
    task_acks_late=False,  # ✅ Accuse réception AVANT exécution (plus de re-traitement au redémarrage)
    task_reject_on_worker_lost=True,  # ✅ Rejeter les tâches si le worker crash
    worker_prefetch_multiplier=1,  # Traite 1 tâche à la fois par worker
    # ⚙️ EXPIRATION DES TÂCHES
    result_expires=3600,  # ✅ Les résultats expirent après 1h (nettoie Redis)
    task_ignore_result=False,  # ✅ On garde les résultats pour le suivi
    # ⚙️ RETRY AUTOMATIQUE
    task_autoretry_for=(Exception,),  # Retry sur toutes les exceptions
    task_retry_backoff=True,  # Délai exponentiel entre retries
    task_retry_backoff_max=3600,  # Max 1h d'attente entre retries
    task_max_retries=3,  # ✅ Réduit à 3 tentatives (au lieu de 5)
    task_retry_jitter=True,  # Délai aléatoire pour éviter les "thundering herd"
    # ⚙️ RATE LIMITING
    task_default_rate_limit="10/m",  # 10 tâches par minute par défaut
    # ⚙️ TIMEOUT
    task_soft_time_limit=300,  # Timeout "soft" à 5 minutes
    task_time_limit=360,  # Timeout "hard" à 6 minutes
    # ⚙️ NETTOYAGE AUTOMATIQUE
    worker_disable_rate_limits=False,  # Respecter les rate limits
)
