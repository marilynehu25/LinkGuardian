# librairie Flask
from asyncio import Semaphore

from aiohttp import ClientTimeout
from celery.schedules import crontab
from flask import Flask
from flask_executor import Executor
from flask_login import current_user
from flask_migrate import Migrate

# Importer Celery depuis le fichier dédié
from celery_app import celery

# librairie SQLAlchemy
from database import db
from routes.anchors_routes import anchors_routes
from routes.auth_routes import authentification
from routes.backlinks_routes import backlinks_routes
from routes.config_routes import config_bp
from routes.domains_routes import domains_routes
from routes.login_manager import login_manager
from routes.main_routes import main_routes
from routes.progress_routes import progress_routes
from routes.site_routes import sites_routes
from routes.source_routes import source_rout
from routes.static_routes import static_bp
from services.tag_services import tag_serv
from services.utils_service import tag_color

SECONDS_BETWEEN_REQUESTS = 150
SEMAPHORE_BABBAR = Semaphore(10)
MAX_CONCURRENT_REQUESTS = 10
SEMAPHORE_YOURTEXTGURU = Semaphore(2)
request_counter = 0
AIOHTTP_TIMEOUT = ClientTimeout(total=30)

# Création de l'application Flask
app = Flask(__name__)
app.secret_key = "dfsdfsdfdfsdfsdfsdfsdfsdfsdfsdffsd"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"

# Initialisation de la base de données
db.init_app(app)
migrate = Migrate(app, db)
login_manager.init_app(app)
executor = Executor(app)


# ✅ Configuration du user_loader pour Flask-Login
@login_manager.user_loader
def load_user(user_id):
    from models import User

    return User.query.get(int(user_id))


# Configuration du contexte Flask pour Celery
class ContextTask(celery.Task):
    def __call__(self, *args, **kwargs):
        with app.app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask

# Configuration des tâches périodiques
celery.conf.beat_schedule = {
    "check-all-sites-weekly": {
        "task": "tasks.check_all_sites_weekly",
        "schedule": crontab(day_of_week="monday", hour=2, minute=0),
    },
}

# Filtres de template
app.add_template_filter(tag_color, "tag_color")

# Enregistrement des Blueprints
app.register_blueprint(authentification)
app.register_blueprint(config_bp)
app.register_blueprint(main_routes)
app.register_blueprint(sites_routes)
app.register_blueprint(source_rout)
app.register_blueprint(static_bp)
app.register_blueprint(backlinks_routes)
app.register_blueprint(progress_routes)
app.register_blueprint(anchors_routes)
app.register_blueprint(domains_routes)
app.register_blueprint(tag_serv)
# app.register_blueprint(dashboard_routes)


@app.context_processor
def inject_global_stats():
    """Injecte des statistiques globales dans tous les templates"""
    if current_user.is_authenticated:
        from urllib.parse import urlparse

        from sqlalchemy import func

        from models import Website

        # Nombre total de backlinks
        total_backlinks = Website.query.filter_by(user_id=current_user.id).count()

        # Nombre d'ancres uniques
        total_unique_anchors = (
            db.session.query(func.count(func.distinct(Website.anchor_text)))
            .filter(
                Website.user_id == current_user.id,
                Website.anchor_text.isnot(None),
                Website.anchor_text != "",
            )
            .scalar()
            or 0
        )

        # Nombre de domaines uniques
        sites = (
            Website.query.filter_by(user_id=current_user.id)
            .with_entities(Website.url)
            .all()
        )
        unique_domains = len(
            set(
                urlparse(site.url).netloc.replace("www.", "")
                for site in sites
                if site.url
            )
        )

        return dict(
            total_backlinks=total_backlinks,
            total_unique_anchors=total_unique_anchors,
            total_unique_domains=unique_domains,
        )

    return dict(total_backlinks=0, total_unique_anchors=0, total_unique_domains=0)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
