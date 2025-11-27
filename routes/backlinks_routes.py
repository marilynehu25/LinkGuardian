# routes/backlinks_routes.py

from flask import Blueprint, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import func

from models import Source, Tag, User, Website

backlinks_routes = Blueprint("backlinks_routes", __name__)


def get_filtered_query():
    """Construit la requête filtrée backlinks/dashboard"""

    # Récupération brute des filtres
    filter_user_ids = request.args.getlist("user_id")  # toujours strings
    filter_tags = request.args.getlist("tag")
    filter_sources = request.args.getlist("source")

    # --------------------------------------------
    # 🔹 1. Sélection des utilisateurs
    # --------------------------------------------
    if current_user.role == "main_admin":
        # Filtrage uniquement sur les valeurs numériques
        valid_user_ids = [int(uid) for uid in filter_user_ids if uid.isdigit()]

        if valid_user_ids:
            # → cas 1 : un ou plusieurs utilisateurs sélectionnés
            query = Website.query.filter(Website.user_id.in_(valid_user_ids))
        else:
            # → cas 2 : rien sélectionné → MES données uniquement
            query = Website.query.filter(Website.user_id == current_user.id)

    else:
        # → utilisateur simple
        query = Website.query.filter(Website.user_id == current_user.id)

    # --------------------------------------------
    # 🔹 2. Filtres TAGS
    # --------------------------------------------
    if filter_tags:
        normalized = [t.lower().strip() for t in filter_tags]
        query = query.filter(func.lower(Website.tag).in_(normalized))

    # --------------------------------------------
    # 🔹 3. Filtres SOURCES
    # --------------------------------------------
    if filter_sources:
        normalized = [s.lower().strip() for s in filter_sources]
        query = query.filter(func.lower(Website.source_plateforme).in_(normalized))

    # --------------------------------------------
    # 🔹 4. Search textuelle
    # --------------------------------------------
    q = request.args.get("q", "").strip()
    if q:
        query = query.filter(
            Website.url.ilike(f"%{q}%") | Website.anchor_text.ilike(f"%{q}%")
        )

    # --------------------------------------------
    # 🔹 5. Follow / Nofollow
    # --------------------------------------------
    follow = request.args.get("follow", "all")
    if follow == "true":
        query = query.filter(Website.link_follow_status == "follow")
    elif follow == "false":
        query = query.filter(Website.link_follow_status == "nofollow")

    # --------------------------------------------
    # 🔹 6. Indexation
    # --------------------------------------------
    indexed = request.args.get("indexed", "all")
    if indexed == "true":
        query = query.filter(Website.google_index_status == "Indexé !")
    elif indexed == "false":
        query = query.filter(Website.google_index_status != "Indexé !")

    # --------------------------------------------
    # 🔹 7. Tri
    # --------------------------------------------
    sort = request.args.get("sort", "created")
    order = request.args.get("order", "desc")

    columns = {
        "page_value": Website.page_value,
        "page_trust": Website.page_trust,
        "domain": Website.url,
        "created": Website.id,
    }
    col = columns.get(sort, Website.id)
    query = query.order_by(col.desc() if order == "desc" else col.asc())

    return query


@backlinks_routes.route("/backlinks")
@login_required
def backlinks_list():
    """Route principale - page complète"""

    # ---------------------------------------
    # 🔹 1) Récupération query filtrée
    # ---------------------------------------
    query = get_filtered_query()

    # ---------------------------------------
    # 🔹 2) Pagination
    # ---------------------------------------
    page = request.args.get("page", 1, type=int)
    per_page = 10
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # ---------------------------------------
    # 🔹 3) Calcul qualité
    # ---------------------------------------
    for site in pagination.items:
        if site.page_trust and site.page_value:
            site.quality = round((site.page_trust * 0.6) + (site.page_value * 0.4), 1)
        else:
            site.quality = 0

    # ---------------------------------------
    # 🔹 4) Statistiques filtrées
    # ---------------------------------------
    stats_query = get_filtered_query().order_by(None)
    total = stats_query.count()

    if total > 0:
        follow_count = stats_query.filter(
            Website.link_follow_status == "follow"
        ).count()
        indexed_count = stats_query.filter(
            Website.google_index_status == "Indexé !"
        ).count()
        avg_value = (
            stats_query.with_entities(func.avg(Website.page_value)).scalar() or 0
        )
        avg_trust = (
            stats_query.with_entities(func.avg(Website.page_trust)).scalar() or 0
        )
        avg_quality = round((float(avg_trust) * 0.6) + (float(avg_value) * 0.4), 1)
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

    # ---------------------------------------
    # 🔹 6) Filtres envoyés au template
    # ---------------------------------------
    filters = {
        "q": request.args.get("q", ""),
        "follow": request.args.get("follow", "all"),
        "indexed": request.args.get("indexed", "all"),
        "sort": request.args.get("sort", "created"),
        "order": request.args.get("order", "desc"),
        # multi-tags
        "tag": request.args.getlist("tag"),
        # multi-source
        "source": request.args.getlist("source"),
        # multi-users
        "user_id": request.args.getlist("user_id"),
    }

    # ---------------------------------------
    # 🔹 7) URL pagination (garde tous les filtres)
    # ---------------------------------------
    pagination_base_url = url_for(
        "backlinks_routes.backlinks_table_partial",
        q=request.args.get("q", ""),
        # multi-valued filters
        tag=request.args.getlist("tag"),
        source=request.args.getlist("source"),
        user_id=request.args.getlist("user_id"),
        follow=request.args.get("follow", "all"),
        indexed=request.args.get("indexed", "all"),
        sort=request.args.get("sort", "created"),
        order=request.args.get("order", "desc"),
    )

    # ---------------------------------------
    # 🔹 8) Render template final
    # ---------------------------------------
    return render_template(
        "backlinks/list.html",
        backlinks=pagination.items,
        current_page=pagination.page,
        total_pages=pagination.pages or 1,
        stats=stats,
        filters=filters,
        tags=Tag.query.all(),
        sources=Source.query.all(),
        users=User.query.all(),
        pagination_base_url=pagination_base_url,
    )


@backlinks_routes.route("/backlinks/partial/table")
@login_required
def backlinks_table_partial():
    """Partial HTMX - seulement le tableau"""

    # ---------------------------------------
    # 🔹 Redirection si pas HTMX
    # ---------------------------------------
    if not request.headers.get("HX-Request"):
        page = request.args.get("page", 1, type=int)
        return redirect(url_for("backlinks_routes.backlinks_list", page=page))

    # ---------------------------------------
    # 🔹 Query filtrée (tout est dans get_filtered_query)
    # ---------------------------------------
    query = get_filtered_query()

    # ---------------------------------------
    # 🔹 Pagination
    # ---------------------------------------
    page = request.args.get("page", 1, type=int)
    per_page = 10
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    # ---------------------------------------
    # 🔹 Calcul qualité
    # ---------------------------------------
    for site in pagination.items:
        if site.page_trust and site.page_value:
            site.quality = round((site.page_trust * 0.6) + (site.page_value * 0.4), 1)
        else:
            site.quality = 0

    # ---------------------------------------
    # 🔹 Reconstruction de l'URL de pagination
    #     → conserve TOUS les filtres multi-values
    # ---------------------------------------
    base_url = url_for(
        "backlinks_routes.backlinks_table_partial",
        q=request.args.get("q", ""),
        # MULTI-TAGS
        tag=request.args.getlist("tag"),
        # MULTI-SOURCES
        source=request.args.getlist("source"),
        # MULTI-USERS
        user_id=request.args.getlist("user_id"),
        follow=request.args.get("follow", "all"),
        indexed=request.args.get("indexed", "all"),
        sort=request.args.get("sort", "created"),
        order=request.args.get("order", "desc"),
    )

    # ---------------------------------------
    # 🔹 Render partial HTMX
    # ---------------------------------------
    return render_template(
        "backlinks/_table.html",
        backlinks=pagination.items,
        current_page=pagination.page,
        total_pages=pagination.pages or 1,
        pagination_base_url=base_url,
    )
