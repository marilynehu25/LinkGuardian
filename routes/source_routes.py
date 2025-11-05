from flask import Blueprint, jsonify, request

from models import Source, db

source_rout = Blueprint("source_routes", __name__)


# Route pour ajouter une source dans la liste des sources
@source_rout.route("/add_source", methods=["POST"])
def add_source():
    data = request.get_json()
    new_source = Source(nom=data["nom"])
    db.session.add(new_source)
    db.session.commit()
    return jsonify({"success": True})


# Route pour supprimer une source
@source_rout.route("/delete_source", methods=["POST"])
def delete_source():
    data = request.get_json()
    source_name = data["nom"]
    source = Source.query.filter_by(nom=source_name).first()

    if source:
        db.session.delete(source)
        db.session.commit()
        return jsonify({"success": True})

    return jsonify({"success": False, "error": "Source introuvable"}), 404


# Route pour récupérer toutes les sources
@source_rout.route("/get_sources", methods=["GET"])
def get_sources():
    sources = Source.query.all()
    return jsonify([{"nom": s.nom} for s in sources])
