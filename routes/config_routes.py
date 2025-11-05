from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from models import Configuration, db

config_bp = Blueprint("config_routes", __name__)

# configuration de la page Configuration
# Route pour afficher la page de configuration
# afficher et mettre à jour les configurations de l'application. Si la méthode est GET, elle affiche simplement la page de configuration avec les valeurs actuelles.
# Si la méthode est POST, elle traite les données du formulaire, met à jour la configuration dans la base de données, et redirige l'utilisateur vers la page de configuration
# avec un message de confirmation.
@config_bp.route("/configuration", methods=["GET", "POST"])
@login_required
def configuration():
    """
    Affiche et met à jour la configuration de l’application.
    GET → affiche la page
    POST → met à jour la base de données
    """
    if request.method == "POST":
        sms_enabled = request.form.get("sms_enabled") == "on"
        phone_number = request.form.get("phone_number")

        config = Configuration.query.first()
        if not config:
            config = Configuration()
            db.session.add(config)

        config.sms_enabled = sms_enabled
        config.phone_number = phone_number

        db.session.commit()
        flash("Configuration sauvegardée avec succès.")
        return redirect(
            url_for("config_routes.configuration")
        )  # <-- note le nom 'config.' ici

    else:
        config = Configuration.query.first()
        return render_template("settings/index.html", config=config)


# Redirige le lien "/settings" du layout vers la page de configuration existante
@config_bp.route("/settings", methods=["GET"])
@login_required
def settings_redirect():
    return redirect(url_for("config_routes.configuration"))
