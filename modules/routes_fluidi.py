"""
Routes for the Fluid List management module.
Provides CRUD operations on rules/fluid_list.json and a web UI.
"""

import json
import os

from flask import Blueprint, jsonify, render_template, request

fluidi_bp = Blueprint("fluidi", __name__)

_FLUID_LIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rules", "fluid_list.json")


def _read_fluid_data() -> dict:
    with open(_FLUID_LIST_PATH, encoding="utf-8") as f:
        return json.load(f)


def _write_fluid_data(data: dict) -> None:
    with open(_FLUID_LIST_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@fluidi_bp.route("/")
def list_fluidi():
    """GET /fluidi → JSON list of all fluids."""
    data = _read_fluid_data()
    return jsonify(data.get("fluidi", []))


@fluidi_bp.route("/categorie")
def list_categorie():
    """GET /fluidi/categorie → JSON list of unique categories."""
    data = _read_fluid_data()
    categorie = sorted({f["categoria"] for f in data.get("fluidi", [])})
    return jsonify(categorie)


@fluidi_bp.route("/custom", methods=["POST"])
def add_custom():
    """POST /fluidi/custom → add a custom fluid entry."""
    payload = request.get_json()
    required = ("codice", "descrizione", "categoria", "materiale", "rating")
    missing = [k for k in required if not payload.get(k)]
    if missing:
        return jsonify({"error": f"Campi obbligatori mancanti: {', '.join(missing)}"}), 400

    data = _read_fluid_data()
    existing_codes = {f["codice"] for f in data.get("fluidi", [])}
    if payload["codice"] in existing_codes:
        return jsonify({"error": f"Codice '{payload['codice']}' già esistente"}), 409

    new_fluid = {
        "codice": payload["codice"].strip().upper(),
        "descrizione": payload["descrizione"].strip(),
        "categoria": payload["categoria"].strip(),
        "materiale": payload["materiale"].strip(),
        "rating": payload["rating"].strip(),
        "coibentazione": payload.get("coibentazione", "").strip(),
        "standard": False,
        "custom": True,
    }
    nota = payload.get("nota", "").strip()
    if nota:
        new_fluid["nota"] = nota

    data.setdefault("fluidi", []).append(new_fluid)
    _write_fluid_data(data)
    return jsonify(new_fluid), 201


@fluidi_bp.route("/custom/<codice>", methods=["DELETE"])
def delete_custom(codice):
    """DELETE /fluidi/custom/<codice> → remove a custom fluid."""
    data = _read_fluid_data()
    fluidi = data.get("fluidi", [])
    target = [f for f in fluidi if f["codice"] == codice]

    if not target:
        return jsonify({"error": f"Fluido '{codice}' non trovato"}), 404
    if not target[0].get("custom", False):
        return jsonify({"error": "Solo i fluidi custom possono essere rimossi"}), 403

    data["fluidi"] = [f for f in fluidi if f["codice"] != codice]
    _write_fluid_data(data)
    return jsonify({"deleted": codice})


@fluidi_bp.route("/page")
def fluidi_page():
    """GET /fluidi/page → render the Fluid List HTML page."""
    return render_template("fluidi.html")
