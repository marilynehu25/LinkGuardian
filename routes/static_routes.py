# routes/static_routes.py
from flask import Blueprint, current_app

# Création du Blueprint
static_bp = Blueprint("static", __name__)


# Ajout de page
# permet à un utilisateur ou à un robot d'accéder au fichier "robots.txt" en visitant l'URL "/robots.txt" de l'application Flask. Le fichier "robots.txt" est généralement utilisé
# pour fournir des directives aux robots d'exploration web sur la manière dont ils devraient accéder et explorer le site.
@static_bp.route("/robots.txt")
def robots_txt():
    return current_app.send_static_file("robots.txt")


#  permet à un utilisateur ou à un robot d'accéder au fichier "sitemap.xml" en visitant l'URL '/sitemap.xml' de l'application Flask. Le fichier "sitemap.xml" est généralement utilisé
# pour fournir des informations structurées sur la structure du site aux moteurs de recherche.
@static_bp.route("/sitemap.xml")
def sitemap_xml():
    return current_app.send_static_file("sitemap.xml")


#  permet à un utilisateur ou à un robot d'accéder au fichier "sitemap_index.xml" en visitant l'URL '/sitemap_index.xml' de l'application Flask. Le fichier "sitemap_index.xml" est
# généralement utilisé pour référencer plusieurs fichiers de sitemap et indiquer aux moteurs de recherche où trouver des informations détaillées sur la structure du site.
@static_bp.route("/sitemap_index.xml")
def sitemap_index_xml():
    return current_app.send_static_file("sitemap_index.xml")
