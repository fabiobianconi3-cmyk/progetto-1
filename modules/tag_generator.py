"""
Module 1 - SOP Tag Generator
Generates tags following Lundbeck SOP naming conventions:
  Equipment: AAA-YYBBBB-XX
  Lines:     AAAA-BB-C-DDDDDD-EEE-FF
  Instruments: AAA-BBBBBB-XX
"""

import json
import os
import re
from flask import Blueprint, render_template, request, jsonify

tag_bp = Blueprint("tags", __name__)

# --- Equipment tag: AAA-YYBBBB-XX ---
EQUIPMENT_TYPES = {
    "PMP": "Pompa",
    "TK": "Serbatoio",
    "HX": "Scambiatore di calore",
    "AGT": "Agitatore",
    "FLT": "Filtro",
    "VLV": "Valvola",
    "CMP": "Compressore",
    "DRY": "Essiccatore",
    "REA": "Reattore",
    "COL": "Colonna",
}

# --- Instrument types ---
INSTRUMENT_TYPES = {
    "PI": "Indicatore di pressione",
    "TI": "Indicatore di temperatura",
    "FI": "Indicatore di flusso",
    "LI": "Indicatore di livello",
    "LT": "Trasmettitore di livello",
    "PT": "Trasmettitore di pressione",
    "TT": "Trasmettitore di temperatura",
    "FT": "Trasmettitore di flusso",
    "PIC": "Controllore di pressione",
    "TIC": "Controllore di temperatura",
    "FIC": "Controllore di flusso",
    "LIC": "Controllore di livello",
    "PSV": "Valvola di sicurezza pressione",
    "XV": "Valvola on/off",
    "CV": "Valvola di controllo",
}

LINE_SPEC_CLASSES = {
    "A": "AISI 316L",
    "B": "AISI 304",
    "C": "PP",
    "D": "PVDF",
    "E": "PE-HD",
    "F": "Vetro",
}

_FLUID_LIST_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "rules", "fluid_list.json")

_FALLBACK_FLUID_SERVICES = {
    "WFI": "Acqua per iniettabili",
    "PW": "Acqua purificata circuito secondario",
    "CIPS": "Cleaning in place (mandata)",
    "CIPR": "Cleaning in place (ritorno)",
    "N": "Azoto",
    "CA": "Aria compressa",
    "P": "Linea di processo generica",
}


def load_fluid_services() -> dict:
    """Load fluid services from rules/fluid_list.json, returning {codice: descrizione}."""
    try:
        with open(_FLUID_LIST_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return {fluid["codice"]: fluid["descrizione"] for fluid in data.get("fluidi", [])}
    except (FileNotFoundError, json.JSONDecodeError, KeyError):
        return dict(_FALLBACK_FLUID_SERVICES)


def validate_equipment_tag(tag: str) -> dict:
    """Validate equipment tag format AAA-YYBBBB-XX."""
    pattern = r"^([A-Z]{2,3})-(\d{2}[A-Z]{0,2}\d{2,4})-(\d{2})$"
    m = re.match(pattern, tag)
    if not m:
        return {"valid": False, "error": "Formato non valido. Atteso: AAA-YYBBBB-XX"}
    return {"valid": True, "type": m.group(1), "number": m.group(2), "suffix": m.group(3)}


def validate_line_tag(tag: str) -> dict:
    """Validate line tag format AAAA-BB-C-DDDDDD-EEE-FF."""
    pattern = r"^(\d{4})-(\d{2})-([A-F])-([A-Z0-9\-]{2,10})-([A-Z]{2,3})-(\d{2})$"
    m = re.match(pattern, tag)
    if not m:
        return {"valid": False, "error": "Formato non valido. Atteso: AAAA-BB-C-DDDDDD-EEE-FF"}
    return {
        "valid": True,
        "area": m.group(1),
        "diameter": m.group(2),
        "spec_class": m.group(3),
        "service": m.group(4),
        "insulation": m.group(5),
        "sequence": m.group(6),
    }


def validate_instrument_tag(tag: str) -> dict:
    """Validate instrument tag format AAA-BBBBBB-XX."""
    pattern = r"^([A-Z]{2,3})-(\d{4,6})-(\d{2})$"
    m = re.match(pattern, tag)
    if not m:
        return {"valid": False, "error": "Formato non valido. Atteso: AAA-BBBBBB-XX"}
    return {"valid": True, "function": m.group(1), "loop": m.group(2), "suffix": m.group(3)}


def generate_equipment_tag(eq_type: str, area_year: str, seq_number: str, suffix: str) -> str:
    return f"{eq_type}-{area_year}{seq_number}-{suffix}"


def generate_line_tag(area: str, diameter: str, spec_class: str, service: str, insulation: str, sequence: str) -> str:
    return f"{area}-{diameter}-{spec_class}-{service}-{insulation}-{sequence}"


def generate_instrument_tag(inst_type: str, loop_number: str, suffix: str) -> str:
    return f"{inst_type}-{loop_number}-{suffix}"


@tag_bp.route("/")
def tag_page():
    return render_template(
        "tags.html",
        equipment_types=EQUIPMENT_TYPES,
        instrument_types=INSTRUMENT_TYPES,
        spec_classes=LINE_SPEC_CLASSES,
        fluid_services=load_fluid_services(),
    )


@tag_bp.route("/generate", methods=["POST"])
def generate():
    data = request.get_json()
    tag_category = data.get("category", "")

    if tag_category == "equipment":
        tag = generate_equipment_tag(
            data.get("eq_type", ""),
            data.get("area_year", ""),
            data.get("seq_number", ""),
            data.get("suffix", "01"),
        )
        validation = validate_equipment_tag(tag)
    elif tag_category == "line":
        tag = generate_line_tag(
            data.get("area", ""),
            data.get("diameter", ""),
            data.get("spec_class", ""),
            data.get("service", ""),
            data.get("insulation", ""),
            data.get("sequence", ""),
        )
        validation = validate_line_tag(tag)
    elif tag_category == "instrument":
        tag = generate_instrument_tag(
            data.get("inst_type", ""),
            data.get("loop_number", ""),
            data.get("suffix", "01"),
        )
        validation = validate_instrument_tag(tag)
    else:
        return jsonify({"error": "Categoria non valida"}), 400

    return jsonify({"tag": tag, "validation": validation})


@tag_bp.route("/validate", methods=["POST"])
def validate():
    data = request.get_json()
    tag = data.get("tag", "").strip().upper()
    category = data.get("category", "")

    if category == "equipment":
        result = validate_equipment_tag(tag)
    elif category == "line":
        result = validate_line_tag(tag)
    elif category == "instrument":
        result = validate_instrument_tag(tag)
    else:
        return jsonify({"error": "Categoria non valida"}), 400

    result["tag"] = tag
    return jsonify(result)
