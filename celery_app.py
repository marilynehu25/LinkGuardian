"""Configuration Celery pour LinkGuardian - version Flask + RabbitMQ + Beat"""

import os

from celery import Celery
from celery.schedules import crontab

broker_user = os.getenv("RABBITMQ_DEFAULT_USER")
broker_pass = os.getenv("RABBITMQ_DEFAULT_PASS")

# ✅ Créer l'instance Celery STANDALONE (sans Flask au départ)
celery = Celery(
    "linkguardian",
    broker=f"amqp://{broker_user}:{broker_pass}@rabbitmq:5672//",
    backend="rpc://",
)

# Configuration commune
celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Europe/Paris",
    enable_utc=True,
    imports=("tasks",),
    task_acks_late=True,
    task_reject_on_worker_lost=False,
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_ignore_result=False,
    task_autoretry_for=(Exception,),
    task_retry_backoff=True,
    task_retry_backoff_max=3600,
    task_max_retries=3,
    task_retry_jitter=True,
    task_default_rate_limit="10/m",
    worker_disable_rate_limits=False,
    task_soft_time_limit=300,
    task_time_limit=360,
    broker_transport_options={
        "visibility_timeout": 3600,
        "confirm_publish": True,
    },
)

# ✅ Planificateur de tâches (beat)
celery.conf.beat_schedule = {
    "check-all-sites-weekly": {
        "task": "tasks.check_all_sites_weekly",
        "schedule": crontab(day_of_week="monday", hour=2, minute=0),
    },
}


def get_flask_app():
    """
    Crée et retourne l'instance Flask avec toute sa configuration.
    Cette fonction est appelée par les workers Celery.
    """
    from flask import Flask
    from flask_migrate import Migrate

    from database import db
    from routes.login_manager import login_manager
    
    app = Flask(__name__)
    app.secret_key = os.getenv("SECRET_KEY", "dfsdfsdfdfsdfsdfsdfsdfsdfsdfsdffsd")
    
    db_user = os.getenv("POSTGRES_USER", "postgres")
    db_pass = os.getenv("POSTGRES_PASSWORD", "25082001Ma#")
    db_host = os.getenv("DB_HOST", "postgres")
    db_port = os.getenv("DB_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "site")
    
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    )
    
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager.init_app(app)
    
    return app


def init_celery(app):
    """
    Initialise Celery avec le contexte Flask après la création de l'app.
    À appeler depuis app.py après la création de l'instance Flask.
    """
    class ContextTask(celery.Task):
        """Exécute chaque tâche dans un contexte Flask"""
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


# 🔥 IMPORTANT : Créer flask_app pour les workers
flask_app = get_flask_app()
init_celery(flask_app)

#print("ℹ️ Celery initialisé avec contexte Flask pour les workers")