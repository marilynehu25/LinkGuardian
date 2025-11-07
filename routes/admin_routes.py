from flask import Blueprint, redirect, render_template, url_for, flash
from flask_login import login_required, current_user

admin_routes = Blueprint("admin_routes", __name__)

@admin_routes.route("/admin")
@login_required
def admin():
    # Vérifie si l'utilisateur est admin
    if current_user.role != "admin":
        flash("Accès refusé : vous n'êtes pas administrateur.", "danger")
        return redirect(url_for("main_routes.index"))
    
    # Si l'utilisateur est admin, on affiche la page admin
    return render_template("admin/master.html")