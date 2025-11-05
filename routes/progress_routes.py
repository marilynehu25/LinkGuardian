# routes/progress_routes.py

from datetime import datetime, timedelta

from flask import Blueprint, jsonify
from flask_login import current_user, login_required

from models import Website

progress_routes = Blueprint("progress_routes", __name__)

# Dictionnaire pour stocker les vérifications en cours (en mémoire)
# Format: {user_id: {'checking': [site_ids], 'last_update': datetime}}
verification_status = {}


@progress_routes.route("/api/verification-status")
@login_required
def get_verification_status():
    """
    Retourne le statut des vérifications en cours pour l'utilisateur connecté.
    On considère qu'un site est "en vérification" si last_checked a été mis à jour
    dans les 15 dernières secondes.
    """
    user_id = current_user.id

    # Récupérer les sites vérifiés dans les 15 dernières secondes
    recent_threshold = datetime.now() - timedelta(seconds=15)

    # Sites en cours de vérification (last_checked très récent)
    checking_sites = Website.query.filter(
        Website.user_id == user_id, Website.last_checked >= recent_threshold
    ).count()

    # Total de sites
    total_sites = Website.query.filter_by(user_id=user_id).count()

    print(f"🔍 Vérification status API: {checking_sites} sites en cours")

    return jsonify(
        {
            "is_checking": checking_sites > 0,
            "sites_checking": checking_sites,
            "total_sites": total_sites,
        }
    )


@progress_routes.route("/api/start-verification/<int:site_id>", methods=["POST"])
@login_required
def start_verification(site_id):
    """
    Marque le début d'une vérification pour un site.
    """
    user_id = current_user.id

    if user_id not in verification_status:
        verification_status[user_id] = {
            "checking": set(),
            "last_update": datetime.now(),
        }

    verification_status[user_id]["checking"].add(site_id)
    verification_status[user_id]["last_update"] = datetime.now()

    return jsonify({"success": True})


@progress_routes.route("/api/end-verification/<int:site_id>", methods=["POST"])
@login_required
def end_verification(site_id):
    """
    Marque la fin d'une vérification pour un site.
    """
    user_id = current_user.id

    if (
        user_id in verification_status
        and site_id in verification_status[user_id]["checking"]
    ):
        verification_status[user_id]["checking"].remove(site_id)
        verification_status[user_id]["last_update"] = datetime.now()

    return jsonify({"success": True})
