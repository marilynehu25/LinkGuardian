from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from database import db
from models import Website

anchors_routes = Blueprint("anchors_routes", __name__)


def get_filtered_anchors_query():
    """Construit la requête avec les filtres communs pour les ancres"""
    # Requête de base : grouper par anchor_text
    query = (
        db.session.query(
            Website.anchor_text,
            func.count(Website.anchor_text).label("count"),
        )
        .filter(
            Website.user_id == current_user.id,
            Website.anchor_text.isnot(None),
            Website.anchor_text != "",
        )
        .group_by(Website.anchor_text)
    )

    # Filtres
    q = request.args.get("q", "").strip()
    anchor_type = request.args.get("type", "all")
    sort = request.args.get("sort", "count")
    order = request.args.get("order", "desc")

    # 🔍 Recherche textuelle
    if q:
        query = query.filter(Website.anchor_text.ilike(f"%{q}%"))

    return query, anchor_type, sort, order


def classify_anchor_type(text):
    """Classifie le type d'ancre"""
    text_lower = text.lower()

    if "http" in text_lower:
        return "naked_url"
    elif any(k in text_lower for k in ["marque", "officiel", "nom"]):
        return "branded"
    elif any(k in text_lower for k in ["ici", "plus", "page", "voir", "cliquez"]):
        return "generic"
    elif len(text_lower.split()) == 1:
        return "exact_match"
    else:
        return "partial_match"


def process_anchors(anchors_query, total_count, anchor_type_filter):
    """Traite les ancres et applique les filtres de type"""
    anchors = []

    for a in anchors_query:
        text = a.anchor_text.strip()
        count = a.count
        ratio = round((count / total_count) * 100, 1) if total_count > 0 else 0

        anchor_type = classify_anchor_type(text)

        # Filtre par type
        if anchor_type_filter != "all" and anchor_type != anchor_type_filter:
            continue

        anchors.append(
            {
                "text": text,
                "count": count,
                "ratio": ratio,
                "length": len(text),
                "trend": 0,
                "type": anchor_type,
                "over_optimized": ratio > 15,
            }
        )

    return anchors


@anchors_routes.route("/anchors")
@login_required
def anchors_list():
    """Route principale - page complète avec pagination"""

    # Requête filtrée
    query, anchor_type_filter, sort, order = get_filtered_anchors_query()

    # Exécuter la requête pour obtenir toutes les ancres filtrées
    anchors_query = query.all()

    if not anchors_query:
        return render_template(
            "anchors/list.html",
            anchors=[],
            current_page=1,
            total_pages=1,
            stats={
                "total_anchors": 0,
                "branded_percentage": 0,
                "exact_match_percentage": 0,
                "generic_percentage": 0,
                "over_optimized_count": 0,
            },
            over_optimized_anchors=[],
            pie_data={},
            top_data={},
            filters={
                "q": "",
                "type": "all",
                "sort": "count",
                "order": "desc",
            },
        )

    # Calculer le total pour les ratios
    total_count = sum(a.count for a in anchors_query)

    # Traiter les ancres
    anchors = process_anchors(anchors_query, total_count, anchor_type_filter)

    # 📊 Tri
    if sort == "count":
        anchors.sort(key=lambda a: a["count"], reverse=(order == "desc"))
    elif sort == "ratio":
        anchors.sort(key=lambda a: a["ratio"], reverse=(order == "desc"))
    elif sort == "length":
        anchors.sort(key=lambda a: a["length"], reverse=(order == "desc"))
    elif sort == "text":
        anchors.sort(key=lambda a: a["text"].lower(), reverse=(order == "desc"))

    # 📄 PAGINATION (comme backlinks)
    page = request.args.get("page", 1, type=int)
    per_page = 10
    total_anchors = len(anchors)
    total_pages = (total_anchors + per_page - 1) // per_page  # Arrondi supérieur

    # Extraire la page actuelle
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_anchors = anchors[start_idx:end_idx]

    # 📊 Statistiques (sur TOUTES les ancres, pas juste la page)
    if anchors:
        stats = {
            "total_anchors": len(anchors),
            "total_occurrences": sum(a["count"] for a in anchors),
            "branded_percentage": round(
                sum(1 for a in anchors if a["type"] == "branded") / len(anchors) * 100,
                1,
            ),
            "exact_match_percentage": round(
                sum(1 for a in anchors if a["type"] == "exact_match")
                / len(anchors)
                * 100,
                1,
            ),
            "generic_percentage": round(
                sum(1 for a in anchors if a["type"] == "generic") / len(anchors) * 100,
                1,
            ),
            "over_optimized_count": sum(1 for a in anchors if a["over_optimized"]),
        }
    else:
        stats = {
            "total_anchors": 0,
            "total_occurrences": 0,
            "branded_percentage": 0,
            "exact_match_percentage": 0,
            "generic_percentage": 0,
            "over_optimized_count": 0,
        }

    # 📊 Graphiques (basés sur TOUTES les ancres)
    pie_data = {
        "labels": ["Marque", "Exacte", "Partielle", "Génériques", "URLs nues"],
        "values": [
            sum(1 for a in anchors if a["type"] == "branded"),
            sum(1 for a in anchors if a["type"] == "exact_match"),
            sum(1 for a in anchors if a["type"] == "partial_match"),
            sum(1 for a in anchors if a["type"] == "generic"),
            sum(1 for a in anchors if a["type"] == "naked_url"),
        ],
        "colors": ["#22c55e", "#38bdf8", "#f59e0b", "#8b5cf6", "#6b7280"],
    }

    # Top 15 ancres (basé sur le tri actuel)
    top_sorted = anchors[:15]
    top_data = {
        "labels": [a["text"] for a in top_sorted],
        "values": [a["count"] for a in top_sorted],
        "colors": ["#3b82f6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6"] * 3,
    }

    # Ancres sur-optimisées
    over_optimized_anchors = [a for a in anchors if a["over_optimized"]]

    # Filtres actuels
    filters = {
        "q": request.args.get("q", ""),
        "type": request.args.get("type", "all"),
        "sort": request.args.get("sort", "count"),
        "order": request.args.get("order", "desc"),
    }

    return render_template(
        "anchors/list.html",
        anchors=paginated_anchors,  # ✅ Seulement la page actuelle
        current_page=page,
        total_pages=total_pages or 1,
        stats=stats,
        over_optimized_anchors=over_optimized_anchors,
        pie_data=pie_data,
        top_data=top_data,
        filters=filters,
    )


@anchors_routes.route("/anchors/partial/table")
@login_required
def anchors_table_partial():
    """Partial HTMX - seulement le tableau (pour HTMX)"""

    # Requête filtrée (MÊME logique que la route principale)
    query, anchor_type_filter, sort, order = get_filtered_anchors_query()

    # Exécuter la requête
    anchors_query = query.all()

    if not anchors_query:
        return render_template(
            "anchors/_table.html",
            anchors=[],
            current_page=1,
            total_pages=1,
        )

    # Calculer le total pour les ratios
    total_count = sum(a.count for a in anchors_query)

    # Traiter les ancres
    anchors = process_anchors(anchors_query, total_count, anchor_type_filter)

    # Tri
    if sort == "count":
        anchors.sort(key=lambda a: a["count"], reverse=(order == "desc"))
    elif sort == "ratio":
        anchors.sort(key=lambda a: a["ratio"], reverse=(order == "desc"))
    elif sort == "length":
        anchors.sort(key=lambda a: a["length"], reverse=(order == "desc"))
    elif sort == "text":
        anchors.sort(key=lambda a: a["text"].lower(), reverse=(order == "desc"))

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 10
    total_anchors = len(anchors)
    total_pages = (total_anchors + per_page - 1) // per_page

    # Extraire la page actuelle
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_anchors = anchors[start_idx:end_idx]

    return render_template(
        "anchors/_anchors_table.html",
        anchors=paginated_anchors,
        current_page=page,
        total_pages=total_pages or 1,
    )
