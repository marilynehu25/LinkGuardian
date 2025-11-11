from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from database import db
from models import Configuration, User

config_bp = Blueprint("config_routes", __name__)


# ============================================================
# 🔧 DÉCORATEUR ADMIN
# ============================================================
def admin_required(f):
    """Décorateur pour vérifier que l'utilisateur est un administrateur"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)

    return decorated_function


# ============================================================
# 🧩 PAGE GÉNÉRALE DE CONFIGURATION
# ============================================================
@config_bp.route("/configuration", methods=["GET", "POST"])
@login_required
def configuration():
    """Page principale de configuration"""
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
        return redirect(url_for("config_routes.configuration"))

    # Récupérer les utilisateurs (pour l’onglet admin)
    users = User.query.all()
    total_users = len(users)
    total_admins = len([u for u in users if u.role == "admin"])
    config = Configuration.query.first()

    return render_template(
        "settings/index.html",
        config=config,
        total_users=total_users,
        total_admins=total_admins,
        users=users,
    )


# ============================================================
# 👑 ROUTE ADMIN /configuration/administrateur
# ============================================================
@config_bp.route("/configuration/administrateur?tab=admin")
@login_required
@admin_required
def admin():
    """Affiche la page de configuration avec l’onglet admin actif"""
    users = User.query.all()
    total_users = len(users)
    total_admins = len([u for u in users if u.role == "admin"])

    # On rend le même template que la page principale
    return render_template(
        "settings/_table_admin.html",
        users=users,
        total_users=total_users,
        total_admins=total_admins,
    )


@config_bp.route("/configuration/administrateur/user/<int:user_id>")
@login_required
@admin_required
def get_user(user_id):
    """API pour récupérer les données d'un utilisateur (pour le modal d'édition)"""
    user = User.query.get_or_404(user_id)

    return jsonify(
        {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.email,
            "email": user.email,
            "role": user.role,
        }
    )


@config_bp.route("/configuration/administrateur/user/add", methods=["POST"])
@login_required
@admin_required
def add_user():
    """Ajouter un nouvel utilisateur"""
    try:
        # Récupérer les données du formulaire
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        username = request.form.get("email")
        email = request.form.get("email")
        password = request.form.get("password")
        role = request.form.get("role", "user")

        # Vérifier si l'username existe déjà
        if User.query.filter_by(username=username).first():
            flash(f"Le nom d'utilisateur '{username}' existe déjà.", "error")
            return redirect(url_for("config_routes.admin"))

        # Vérifier si l'email existe déjà
        if User.query.filter_by(email=email).first():
            flash(f"L'adresse email '{email}' est déjà utilisée.", "error")
            return redirect(url_for("config_routes.admin"))

        # Créer le nouvel utilisateur
        new_user = User(
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email,
            role=role,
        )

        # Définir le mot de passe (sera hashé automatiquement)
        new_user.set_password(password)

        # Ajouter à la base de données
        db.session.add(new_user)
        db.session.commit()

        flash(
            f"L'utilisateur {first_name} {last_name} a été créé avec succès.", "success"
        )

    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la création de l'utilisateur : {str(e)}", "error")

    return redirect(url_for("config_routes.admin"))


@config_bp.route(
    "/configuration/administrateur/user/<int:user_id>/edit", methods=["POST"]
)
@login_required
@admin_required
def edit_user(user_id):
    """Modifier un utilisateur existant"""
    try:
        user = User.query.get_or_404(user_id)

        # Récupérer les données du formulaire
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        username = request.form.get("username")
        email = request.form.get("email")
        role = request.form.get("role")

        # Vérifier si l'username existe déjà (sauf pour l'utilisateur actuel)
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user_id:
            flash(f"Le nom d'utilisateur '{username}' existe déjà.", "error")
            return redirect(url_for("config_routes.admin"))

        # Vérifier si l'email existe déjà (sauf pour l'utilisateur actuel)
        existing_email = User.query.filter_by(email=email).first()
        if existing_email and existing_email.id != user_id:
            flash(f"L'adresse email '{email}' est déjà utilisée.", "error")
            return redirect(url_for("config_routes.admin"))

        # Empêcher un admin de se retirer ses propres droits admin
        if user_id == current_user.id and role != "admin":
            flash(
                "Vous ne pouvez pas retirer vos propres droits d'administrateur.",
                "error",
            )
            return redirect(url_for("config_routes.admin"))

        # Mettre à jour les données
        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        user.email = email
        user.role = role

        db.session.commit()

        flash(
            f"L'utilisateur {first_name} {last_name} a été modifié avec succès.",
            "success",
        )

    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la modification de l'utilisateur : {str(e)}", "error")

    return redirect(url_for("config_routes.admin"))


@config_bp.route(
    "/configuration/administrateur/user/<int:user_id>/change-password", methods=["POST"]
)
@login_required
@admin_required
def change_user_password(user_id):
    """Changer le mot de passe d'un utilisateur"""
    try:
        user = User.query.get_or_404(user_id)

        # Récupérer le nouveau mot de passe
        new_password = request.form.get("new_password")

        if not new_password or len(new_password) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "error")
            return redirect(url_for("config_routes.admin"))

        # Changer le mot de passe
        user.set_password(new_password)
        db.session.commit()

        flash(
            f"Le mot de passe de {user.first_name} {user.last_name} a été modifié avec succès.",
            "success",
        )

    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors du changement de mot de passe : {str(e)}", "error")

    return redirect(url_for("config_routes.admin"))


@config_bp.route(
    "/configuration/administrateur/user/<int:user_id>/delete", methods=["POST"]
)
@login_required
@admin_required
def delete_user(user_id):
    """Supprimer un utilisateur"""
    try:
        user = User.query.get_or_404(user_id)

        # Empêcher un admin de se supprimer lui-même
        if user_id == current_user.id:
            flash("Vous ne pouvez pas supprimer votre propre compte.", "error")
            return redirect(url_for("config_routes.admin"))

        # Stocker le nom pour le message
        user_name = f"{user.first_name} {user.last_name}"

        # Supprimer l'utilisateur (les sites associés seront supprimés en cascade si configuré)
        db.session.delete(user)
        db.session.commit()

        flash(f"L'utilisateur {user_name} a été supprimé avec succès.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors de la suppression de l'utilisateur : {str(e)}", "error")

    return redirect(url_for("config_routes.admin"))


# À ajouter dans config_routes.py


@config_bp.route("/configuration/change-password", methods=["POST"])
@login_required
def change_own_password():
    """Permet à l'utilisateur connecté de changer son propre mot de passe"""
    try:
        # Récupérer les données du formulaire
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        # Validation : vérifier que tous les champs sont remplis
        if not current_password or not new_password or not confirm_password:
            flash("Tous les champs sont requis.", "error")
            return redirect(url_for("config_routes.configuration"))

        # Validation : vérifier que le nouveau mot de passe a au moins 6 caractères
        if len(new_password) < 6:
            flash(
                "Le nouveau mot de passe doit contenir au moins 6 caractères.", "error"
            )
            return redirect(url_for("config_routes.configuration"))

        # Validation : vérifier que le nouveau mot de passe et la confirmation correspondent
        if new_password != confirm_password:
            flash(
                "Le nouveau mot de passe et la confirmation ne correspondent pas.",
                "error",
            )
            return redirect(url_for("config_routes.configuration"))

        # Vérifier que le mot de passe actuel est correct
        if not current_user.check_password(current_password):
            flash("Le mot de passe actuel est incorrect.", "error")
            return redirect(url_for("config_routes.configuration"))

        # Empêcher l'utilisateur de réutiliser le même mot de passe
        if current_user.check_password(new_password):
            flash("Le nouveau mot de passe doit être différent de l'ancien.", "error")
            return redirect(url_for("config_routes.configuration"))

        # Changer le mot de passe
        current_user.set_password(new_password)
        db.session.commit()

        flash("Votre mot de passe a été modifié avec succès.", "success")

    except Exception as e:
        db.session.rollback()
        flash(f"Erreur lors du changement de mot de passe : {str(e)}", "error")

    return redirect(url_for("config_routes.configuration"))
