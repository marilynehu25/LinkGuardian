# librairie Flask

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)

# librairie SQLAlchemy
# à partir du fichier python database.py
from database import db
from models import User

authentification = Blueprint("auth_routes", __name__)


# gère l'inscription des utilisateurs en vérifiant si l'utilisateur est déjà connecté, en traitant les soumissions de formulaires pour créer de nouveaux utilisateurs,
# et en affichant le formulaire d'inscription dans le cas d'une requête GET. Elle utilise Flask-Login pour vérifier l'état de connexion de l'utilisateur actuel,
# SQLAlchemy pour interagir avec la base de données, et des messages flash pour informer l'utilisateur sur le succès ou l'échec de l'inscription.


@authentification.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("main_routes.index"))

    if request.method == "POST":
        username = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")

        if password != confirm_password:
            flash("Les mots de passe ne correspondent pas.")
            return redirect(url_for("auth_routes.signup"))

        # Vérifier si nom d’utilisateur ou email déjà utilisés
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()
        if existing_user:
            flash("Ce nom d’utilisateur ou email existe déjà.")
            return redirect(url_for("auth_routes.signup"))

        new_user = User(
            username=username, first_name=first_name, last_name=last_name, email=email
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        flash("Inscription réussie.")
        return redirect(url_for("auth_routes.login"))

    return render_template("access_account/signup.html")


# gère l'authentification des utilisateurs en vérifiant si un utilisateur est déjà connecté, en traitant les soumissions de formulaires pour vérifier les informations d'identification,
# et en affichant le formulaire de connexion dans le cas d'une requête GET. Elle utilise Flask-Login pour gérer l'état de connexion de l'utilisateur,
# SQLAlchemy pour interagir avec la base de données, et des messages flash pour informer l'utilisateur sur le succès ou l'échec de l'authentification.
@authentification.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main_routes.index"))

    if request.method == "POST":
        username = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            next_page = request.args.get("next")
            return (
                redirect(next_page)
                if next_page
                else redirect(url_for("main_routes.index"))
            )

        flash("Nom d’utilisateur ou mot de passe incorrect.")

    return render_template("access_account/login.html")


# cette fonction est utilisée pour déconnecter l'utilisateur et le rediriger vers la page de connexion de l'application Flask.
@authentification.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("auth_routes.login"))

