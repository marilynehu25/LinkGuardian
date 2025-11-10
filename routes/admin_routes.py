from functools import wraps
from flask import Blueprint, render_template, abort
from flask_login import current_user, login_required

admin_routes = Blueprint("admin_routes", __name__)


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


@admin_routes.route("/admin")
@login_required
@admin_required
def admin():
    return render_template("admin/list.html")
