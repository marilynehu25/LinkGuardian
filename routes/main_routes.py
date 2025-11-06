from datetime import datetime, timedelta
from urllib.parse import urlparse

# routes/dashboard_routes.py
from flask import Blueprint, render_template, request
from flask_login import current_user, login_required
from sqlalchemy import func

from models import Website, WebsiteStats

# Création du Blueprint
main_routes = Blueprint("main_routes", __name__)


def get_date_range(range_param="30d"):
    """Calcule la plage de dates selon le paramètre (7d, 30d, 90d)"""
    now = datetime.now()

    if range_param == "7d":
        days = 7
        label = "7 derniers jours"
    elif range_param == "90d":
        days = 90
        label = "90 derniers jours"
    else:  # Par défaut 30d
        days = 30
        label = "30 derniers jours"

    start_date = now - timedelta(days=days)
    return start_date, now, days, label


def calculate_total_backlinks(user_id):
    """Calcule le nombre total de backlinks actuels"""
    return Website.query.filter_by(user_id=user_id).count()


def calculate_backlinks_added(user_id, start_date):
    """Calcule le nombre de backlinks ajoutés dans la période"""
    return Website.query.filter(
        Website.user_id == user_id, Website.first_checked >= start_date
    ).count()


def calculate_total_domains(user_id):
    """Compte le nombre de domaines uniques."""
    count = (
        Website.query.filter(Website.user_id == user_id)
        .with_entities(Website.domains)
        .distinct()
        .count()
    )
    return count or 0


def calculate_domains_added(user_id, start_date):
    return len(
        {
            d
            for (d,) in Website.query.with_entities(Website.domains)
            .filter(Website.user_id == user_id, Website.first_checked >= start_date)
            .all()
            if d
        }
    )


def calculate_total_urls(user_id):
    """Calcule le nombre total d'URLs principales uniques (link_to_check) actuelles"""
    unique_urls = (
        Website.query.filter_by(user_id=user_id)
        .with_entities(Website.link_to_check)
        .distinct()
        .count()
    )

    return unique_urls


def calculate_urls_added(user_id, start_date):
    """Calcule le nombre d'URLs principales uniques ajoutées dans la période"""
    unique_urls = (
        Website.query.filter(
            Website.user_id == user_id, Website.first_checked >= start_date
        )
        .with_entities(Website.link_to_check)
        .distinct()
        .count()
    )

    return unique_urls


def calculate_follow_percentage(user_id):
    """Calcule le pourcentage actuel de liens follow"""
    total = Website.query.filter_by(user_id=user_id).count()

    if total == 0:
        return 0.0

    follow_count = Website.query.filter_by(
        user_id=user_id, link_follow_status="follow"
    ).count()

    return round((follow_count / total) * 100, 1)


def calculate_follow_percentage_change(user_id, start_date):
    """Calcule le changement du pourcentage de liens follow dans la période"""
    # Pourcentage actuel
    current_percentage = calculate_follow_percentage(user_id)

    # Pourcentage avant la période (tous les sites ajoutés avant start_date)
    total_before = Website.query.filter(
        Website.user_id == user_id, Website.first_checked < start_date
    ).count()

    if total_before == 0:
        return 0.0

    follow_before = Website.query.filter(
        Website.user_id == user_id,
        Website.first_checked < start_date,
        Website.link_follow_status == "follow",
    ).count()

    percentage_before = round((follow_before / total_before) * 100, 1)

    # Différence
    change = round(current_percentage - percentage_before, 1)
    return change


def calculate_average_quality(user_id):
    """Calcule la qualité moyenne actuelle (PageTrust * 0.6 + PageValue * 0.4)"""
    sites = Website.query.filter(
        Website.user_id == user_id,
        Website.page_trust.isnot(None),
        Website.page_value.isnot(None),
    ).all()

    if not sites:
        return 0.0

    total_quality = 0
    for site in sites:
        quality = (site.page_trust * 0.6) + (site.page_value * 0.4)
        total_quality += quality

    avg_quality = total_quality / len(sites)
    return round(avg_quality, 1)


def calculate_quality_change(user_id, start_date):
    """Calcule le changement de qualité moyenne dans la période"""
    # Qualité actuelle
    current_quality = calculate_average_quality(user_id)

    # Qualité avant la période
    sites_before = Website.query.filter(
        Website.user_id == user_id,
        Website.first_checked < start_date,
        Website.page_trust.isnot(None),
        Website.page_value.isnot(None),
    ).all()

    if not sites_before:
        return 0.0

    total_quality_before = 0
    for site in sites_before:
        quality = (site.page_trust * 0.6) + (site.page_value * 0.4)
        total_quality_before += quality

    avg_quality_before = total_quality_before / len(sites_before)

    # Différence
    change = round(current_quality - avg_quality_before, 1)
    return change


def get_evolution_data(user_id, start_date, days):
    """Génère les données d'évolution des backlinks et domaines sur la période"""
    intervals = []
    backlinks_counts = []
    domains_counts = []
    interval_days = days / 10

    for i in range(11):
        date = start_date + timedelta(days=interval_days * i)
        intervals.append(date.strftime("%Y-%m-%d"))

        # ✅ Compter seulement dans la période sélectionnée
        count = Website.query.filter(
            Website.user_id == user_id,
            Website.first_checked >= start_date,  # ← LIGNE AJOUTÉE
            Website.first_checked <= date,
        ).count()
        backlinks_counts.append(count)

        sites = (
            Website.query.filter(
                Website.user_id == user_id,
                Website.first_checked >= start_date,  # ← LIGNE AJOUTÉE
                Website.first_checked <= date,
            )
            .with_entities(Website.url)
            .all()
        )

        unique_domains = set()
        for site in sites:
            if site.url:
                parsed = urlparse(site.url)
                domain = parsed.netloc.replace("www.", "")
                if domain:
                    unique_domains.add(domain)

        domains_counts.append(len(unique_domains))

    return [
        {"name": "Backlinks", "x": intervals, "y": backlinks_counts},
        {"name": "Domaines", "x": intervals, "y": domains_counts},
    ]


def get_follow_distribution(user_id):
    """Génère les données de répartition Follow/NoFollow"""

    # Total
    total_count = Website.query.filter_by(user_id=user_id).count()

    # Follow
    follow_count = Website.query.filter_by(
        user_id=user_id, link_follow_status="follow"
    ).count()

    # Tout le reste (nofollow + NULL + autres)
    nofollow_count = total_count - follow_count

    return {
        "labels": ["Follow", "NoFollow"],
        "values": [follow_count, nofollow_count],
        "colors": ["#22c55e", "#f59e0b"],
    }


def get_http_status_distribution(user_id):
    """Génère les données de répartition des statuts HTTP"""
    status_counts = {}

    sites = Website.query.filter_by(user_id=user_id).all()

    for site in sites:
        status = site.status_code or "Inconnu"
        status_str = str(status)

        # Regrouper les codes similaires
        if status_str.startswith("2"):
            key = "200"
        elif status_str.startswith("301"):
            key = "301"
        elif status_str.startswith("302"):
            key = "302"
        elif status_str.startswith("4"):
            key = "404"
        elif status_str.startswith("5"):
            key = "500"
        else:
            key = "Autres"

        status_counts[key] = status_counts.get(key, 0) + 1

    labels = ["200", "301", "302", "404", "500", "Autres"]
    values = [status_counts.get(label, 0) for label in labels]
    colors = ["#22c55e", "#f59e0b", "#f59e0b", "#ef4444", "#ef4444", "#6b7280"]

    return {"labels": labels, "values": values, "colors": colors}


def get_top_anchors(user_id, limit=10):
    """Génère le top des ancres les plus utilisées avec retour à la ligne si nécessaire"""
    anchors = (
        Website.query.filter(
            Website.user_id == user_id,
            Website.anchor_text.isnot(None),
            Website.anchor_text != "",
        )
        .with_entities(
            Website.anchor_text, func.count(Website.anchor_text).label("count")
        )
        .group_by(Website.anchor_text)
        .order_by(func.count(Website.anchor_text).desc())
        .limit(limit)
        .all()
    )

    def wrap_text(text, max_length=35):
        if not text:
            return text
        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) <= max_length:
                current_line.append(word)
                current_length += len(word) + 1  # +1 pour l'espace
            else:
                lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        if current_line:
            lines.append(" ".join(current_line))

        return "<br>".join(lines)

    labels = [wrap_text(a.anchor_text) for a in anchors]
    values = [a.count for a in anchors]
    colors = [
        "#38bdf8", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6",
        "#06b6d4", "#84cc16", "#f97316", "#ec4899", "#64748b"
    ]
    return {"labels": labels, "values": values, "colors": colors[:len(labels)]}



def get_pv_pt_scatter(user_id, start_date, end_date, limit=50):
    """Génère les données scatter Page Value vs Page Trust"""
    sites = (
        Website.query.filter(
            Website.user_id == user_id,
            Website.page_value.isnot(None),
            Website.page_trust.isnot(None),
            Website.last_checked >= start_date,
            Website.last_checked <= end_date,
        )
        .order_by((Website.page_value + Website.page_trust).desc())
        .all()
    )

    x_values = [site.page_value for site in sites]
    y_values = [site.page_trust for site in sites]
    labels = [urlparse(site.url).netloc for site in sites]
    sizes = [int(site.backlinks_external or 5) for site in sites]

    return {"x": x_values, "y": y_values, "labels": labels, "sizes": sizes}


def calculate_links_diff_period(user_id, period="30d"):
    """
    Calcule le nombre de liens gagnés et perdus sur une période (7d, 30d, 90d)
    en comparant les snapshots WebsiteStats.
    """
    # Déterminer la durée en jours
    if period == "7d":
        days = 7
    elif period == "90d":
        days = 90
    else:
        days = 30  # par défaut

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Snapshot le plus récent AVANT la date de fin (aujourd'hui)
    latest = (
        WebsiteStats.query.filter(
            WebsiteStats.user_id == user_id, WebsiteStats.date <= end_date
        )
        .order_by(WebsiteStats.date.desc())
        .first()
    )

    # Snapshot le plus proche AVANT la date de début
    previous = (
        WebsiteStats.query.filter(
            WebsiteStats.user_id == user_id, WebsiteStats.date <= start_date
        )
        .order_by(WebsiteStats.date.desc())
        .first()
    )

    # Si pas de snapshot suffisant, on ne calcule rien
    if not latest or not previous:
        return {
            "period": period,
            "lost": 0,
            "gained": 0,
            "previous_total": previous.total_backlinks if previous else 0,
            "current_total": latest.total_backlinks if latest else 0,
        }

    diff = latest.total_backlinks - previous.total_backlinks
    lost = abs(diff) if diff < 0 else 0
    gained = diff if diff > 0 else 0

    return {
        "period": period,
        "lost": lost,
        "gained": gained,
        "previous_total": previous.total_backlinks,
        "current_total": latest.total_backlinks,
        "date_start": previous.date.strftime("%Y-%m-%d"),
        "date_end": latest.date.strftime("%Y-%m-%d"),
    }


@main_routes.route("/")
@login_required
def index():
    """Route principale du dashboard"""

    # Récupérer la plage de dates
    range_param = request.args.get("range", "30d")
    start_date, end_date, days, range_label = get_date_range(range_param)

    # === KPIs ===

    # 1. Backlinks totaux
    total_backlinks = calculate_total_backlinks(current_user.id)
    backlinks_added = calculate_backlinks_added(current_user.id, start_date)
    backlinks_change = (
        f"+{backlinks_added}" if backlinks_added > 0 else str(backlinks_added)
    )
    backlinks_change_type = "positive" if backlinks_added >= 0 else "negative"

    # 2. Domaines référents
    total_domains = calculate_total_domains(current_user.id)
    domains_added = calculate_domains_added(current_user.id, start_date)
    domains_change = f"+{domains_added}" if domains_added > 0 else str(domains_added)
    domains_change_type = "positive" if domains_added >= 0 else "negative"

    links_diff = calculate_links_diff_period(current_user.id, period=range_param)
    links_lost = links_diff["lost"]
    links_gained = links_diff["gained"]

    # 5. % Follow
    follow_percentage = calculate_follow_percentage(current_user.id)
    follow_change = calculate_follow_percentage_change(current_user.id, start_date)
    follow_change_str = (
        f"+{follow_change}%" if follow_change >= 0 else f"{follow_change}%"
    )
    follow_change_type = "positive" if follow_change >= 0 else "negative"

    # 6. Qualité moyenne
    avg_quality = calculate_average_quality(current_user.id)
    quality_change = calculate_quality_change(current_user.id, start_date)
    quality_change_str = (
        f"+{quality_change}" if quality_change >= 0 else str(quality_change)
    )
    quality_change_type = "positive" if quality_change >= 0 else "negative"

    # Grouper les KPIs
    kpis = {
        "total_backlinks": total_backlinks,
        "backlinks_change": backlinks_change,
        "backlinks_change_type": backlinks_change_type,
        "total_domains": total_domains,
        "domains_change": domains_change,
        "domains_change_type": domains_change_type,
        "links_gained": links_gained,
        "links_lost": links_lost,
        "follow_percentage": follow_percentage,
        "follow_change": follow_change_str,
        "follow_change_type": follow_change_type,
        "avg_quality": avg_quality,
        "quality_change": quality_change_str,
        "quality_change_type": quality_change_type,
    }

    # === GRAPHIQUES ===

    charts_data = {
        "evolution": get_evolution_data(current_user.id, start_date, days),
        "follow_distribution": get_follow_distribution(current_user.id),
        "http_status": get_http_status_distribution(current_user.id),
        "top_anchors": get_top_anchors(current_user.id, limit=10),
        "pv_pt_scatter": get_pv_pt_scatter(
            current_user.id, start_date, end_date, limit=50
        ),
    }

    # Timestamp pour éviter le cache des graphiques
    timestamp = int(datetime.now().timestamp())

    print(f"DEBUG - kpis: {kpis}")
    print(f"DEBUG - type de kpis: {type(kpis)}")
    print(f"DEBUG - kpis est None?: {kpis is None}")

    return render_template(
        "dashboard/index.html",
        kpis=kpis,
        charts_data=charts_data,
        range_label=range_label,
        range_param=range_param,
        timestamp=timestamp,
    )


@main_routes.route("/dashboard/content")
@login_required
def dashboard_content():
    """Route partielle HTMX pour recharger uniquement le contenu du dashboard"""

    # Récupérer la plage de dates
    range_param = request.args.get("range", "30d")
    start_date, end_date, days, range_label = get_date_range(range_param)

    # === KPIs ===
    total_backlinks = calculate_total_backlinks(current_user.id)
    backlinks_added = calculate_backlinks_added(current_user.id, start_date)
    backlinks_change = (
        f"+{backlinks_added}" if backlinks_added > 0 else str(backlinks_added)
    )
    backlinks_change_type = "positive" if backlinks_added >= 0 else "negative"

    total_domains = calculate_total_domains(current_user.id)
    domains_added = calculate_domains_added(current_user.id, start_date)
    domains_change = f"+{domains_added}" if domains_added > 0 else str(domains_added)
    domains_change_type = "positive" if domains_added >= 0 else "negative"

    links_diff = calculate_links_diff_period(current_user.id, period=range_param)
    links_lost = links_diff["lost"]
    links_gained = links_diff["gained"]

    follow_percentage = calculate_follow_percentage(current_user.id)
    follow_change = calculate_follow_percentage_change(current_user.id, start_date)
    follow_change_str = (
        f"+{follow_change}%" if follow_change >= 0 else f"{follow_change}%"
    )
    follow_change_type = "positive" if follow_change >= 0 else "negative"

    avg_quality = calculate_average_quality(current_user.id)
    quality_change = calculate_quality_change(current_user.id, start_date)
    quality_change_str = (
        f"+{quality_change}" if quality_change >= 0 else str(quality_change)
    )
    quality_change_type = "positive" if quality_change >= 0 else "negative"

    kpis = {
        "total_backlinks": total_backlinks,
        "backlinks_change": backlinks_change,
        "backlinks_change_type": backlinks_change_type,
        "total_domains": total_domains,
        "domains_change": domains_change,
        "domains_change_type": domains_change_type,
        "links_gained": links_gained,
        "links_lost": links_lost,
        "follow_percentage": follow_percentage,
        "follow_change": follow_change_str,
        "follow_change_type": follow_change_type,
        "avg_quality": avg_quality,
        "quality_change": quality_change_str,
        "quality_change_type": quality_change_type,
    }

    # === GRAPHIQUES ===
    charts_data = {
        "evolution": get_evolution_data(current_user.id, start_date, days),
        "follow_distribution": get_follow_distribution(current_user.id),
        "http_status": get_http_status_distribution(current_user.id),
        "top_anchors": get_top_anchors(current_user.id, limit=10),
        "pv_pt_scatter": get_pv_pt_scatter(
            current_user.id, start_date, end_date, limit=50
        ),
    }

    timestamp = int(datetime.now().timestamp())

    # ✅ Renvoie SEULEMENT le template partiel, pas la page complète
    return render_template(
        "dashboard/_dashboard_content.html",
        kpis=kpis,
        charts_data=charts_data,
        range_label=range_label,
        timestamp=timestamp,
        range_param=range_param,
    )
