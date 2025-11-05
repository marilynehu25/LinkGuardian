# routes/backlinks_routes.py

from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from models import Source, Tag, Website

backlinks_routes = Blueprint("backlinks_routes", __name__)


def get_filtered_query():
    """Construit la requête avec les filtres communs"""
    query = Website.query.filter_by(user_id=current_user.id)

    # Filtres
    q = request.args.get("q", "").strip()
    follow = request.args.get("follow", "all")
    indexed = request.args.get("indexed", "all")
    sort = request.args.get("sort", "created")
    order = request.args.get("order", "desc")

    # Recherche textuelle
    if q:
        query = query.filter(
            (Website.url.ilike(f"%{q}%")) | (Website.anchor_text.ilike(f"%{q}%"))
        )

    # Filtre follow/nofollow
    if follow == "true":
        query = query.filter(Website.link_follow_status == "follow")
    elif follow == "false":
        query = query.filter(Website.link_follow_status == "nofollow")

    # Filtre indexé
    if indexed == "true":
        query = query.filter(Website.google_index_status == "Indexé !")
    elif indexed == "false":
        query = query.filter(Website.google_index_status != "Indexé !")

    # Tri
    if sort == "page_value":
        query = query.order_by(
            Website.page_value.desc() if order == "desc" else Website.page_value.asc()
        )
    elif sort == "page_trust":
        query = query.order_by(
            Website.page_trust.desc() if order == "desc" else Website.page_trust.asc()
        )
    elif sort == "domain":
        query = query.order_by(
            Website.url.desc() if order == "desc" else Website.url.asc()
        )
    else:  # created (par défaut)
        query = query.order_by(
            Website.id.desc() if order == "desc" else Website.id.asc()
        )

    return query


@backlinks_routes.route("/backlinks")
@login_required
def backlinks_list():
    """Route principale - page complète"""

    # Requête filtrée
    query = get_filtered_query()

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 10
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # ✅ Calcul de la qualité pour chaque site
    for site in pagination.items:
        if site.page_trust and site.page_value:
            site.quality = round((site.page_trust * 0.6) + (site.page_value * 0.4), 1)
        else:
            site.quality = 0

    # Statistiques (sur TOUTE la base, pas juste la page actuelle)
    all_sites = Website.query.filter_by(user_id=current_user.id)
    total = all_sites.count()

    if total > 0:
        follow_count = all_sites.filter(Website.link_follow_status == "follow").count()
        indexed_count = all_sites.filter(
            Website.google_index_status == "Indexé !"
        ).count()
        avg_value = all_sites.with_entities(func.avg(Website.page_value)).scalar() or 0
        avg_trust = all_sites.with_entities(func.avg(Website.page_trust)).scalar() or 0
        avg_quality = round((avg_trust * 0.6) + (avg_value * 0.4), 1)
    else:
        follow_count = indexed_count = avg_value = avg_trust = avg_quality = 0

    stats = {
        "total": total,
        "follow": follow_count,
        "follow_percentage": f"{(follow_count / total * 100) if total > 0 else 0:.1f}",
        "indexed": indexed_count,
        "indexed_percentage": f"{(indexed_count / total * 100) if total > 0 else 0:.1f}",
        "avg_quality": f"{avg_quality:.1f}",
        "avg_value": f"{avg_value:.1f}",
        "avg_trust": f"{avg_trust:.1f}",
    }

    tags = Tag.query.all()
    sources = Source.query.all()

    filters = {
        "q": request.args.get("q", ""),
        "follow": request.args.get("follow", "all"),
        "indexed": request.args.get("indexed", "all"),
        "sort": request.args.get("sort", "created"),
        "order": request.args.get("order", "desc"),
    }

    return render_template(
        "backlinks/list.html",
        backlinks=pagination.items,
        current_page=pagination.page,
        total_pages=pagination.pages or 1,
        stats=stats,
        filters=filters,
        tags=tags,
        sources=sources,
    )

@backlinks_routes.route("/backlinks/partial/table")
@login_required
def backlinks_table_partial():
    """Partial HTMX - seulement le tableau"""

    # Requête filtrée (MÊME logique que la route principale)
    query = get_filtered_query()

    # Pagination
    page = request.args.get("page", 1, type=int)
    per_page = 10
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    return render_template(
        "backlinks/_table.html",
        backlinks=pagination.items,
        current_page=pagination.page,
        total_pages=pagination.pages or 1,
    )

