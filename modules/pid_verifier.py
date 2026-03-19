"""
Module 2 - P&ID Completeness Verification
Rules:
  - Every pump (PMP) must have suction line, discharge line, and PI with SCALA attribute
  - Every tank (TK) must have at least one LT (level transmitter)
  - Pressure indicator (PI) blocks must contain SCALA attribute
"""

import os
import ezdxf
from flask import Blueprint, render_template, request, jsonify, current_app
from werkzeug.utils import secure_filename

verifier_bp = Blueprint("verifier", __name__)

ALLOWED_EXTENSIONS = {"dxf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_blocks_and_tags(doc):
    """Extract all block references with their attributes from the DXF document."""
    blocks = []
    msp = doc.modelspace()

    for entity in msp:
        if entity.dxftype() == "INSERT":
            block_info = {
                "name": entity.dxf.name,
                "position": (round(entity.dxf.insert.x, 2), round(entity.dxf.insert.y, 2)),
                "attributes": {},
                "layer": entity.dxf.layer,
            }
            for attrib in entity.attribs:
                block_info["attributes"][attrib.dxf.tag.upper()] = attrib.dxf.text
            blocks.append(block_info)

    return blocks


def find_equipment(blocks, prefix):
    """Find blocks whose TAG attribute or block name starts with prefix."""
    results = []
    for b in blocks:
        tag_value = b["attributes"].get("TAG", b["attributes"].get("TAGNAME", ""))
        if tag_value.upper().startswith(prefix):
            results.append(b)
        elif b["name"].upper().startswith(prefix):
            results.append(b)
    return results


def find_instruments(blocks, inst_type):
    """Find instrument blocks by type prefix (e.g., PI, LT)."""
    results = []
    for b in blocks:
        tag_value = b["attributes"].get("TAG", b["attributes"].get("TAGNAME", ""))
        if tag_value.upper().startswith(inst_type):
            results.append(b)
        elif b["name"].upper().startswith(inst_type):
            results.append(b)
    return results


def find_lines(blocks):
    """Find line/pipe entities."""
    results = []
    for b in blocks:
        tag_value = b["attributes"].get("TAG", b["attributes"].get("TAGNAME", ""))
        # Lines typically have numeric area codes or LINE in the name
        if b["name"].upper().startswith("LINE") or "-" in tag_value and any(
            c.isdigit() for c in tag_value[:4]
        ):
            results.append(b)
    return results


def verify_pumps(blocks):
    """Verify each pump has suction, discharge, and PI with SCALA."""
    pumps = find_equipment(blocks, "PMP")
    pi_instruments = find_instruments(blocks, "PI")
    issues = []

    for pump in pumps:
        pump_tag = pump["attributes"].get("TAG", pump["attributes"].get("TAGNAME", pump["name"]))
        pump_issues = []

        # Check for associated PI instruments
        associated_pis = []
        for pi in pi_instruments:
            pi_tag = pi["attributes"].get("TAG", pi["attributes"].get("TAGNAME", ""))
            # Check proximity or same loop number
            if pump_tag[:3] in pi_tag or abs(pi["position"][0] - pump["position"][0]) < 500:
                associated_pis.append(pi)

        if not associated_pis:
            pump_issues.append("Manca indicatore di pressione (PI) associato")
        else:
            for pi in associated_pis:
                if "SCALA" not in pi["attributes"] and "SCALE" not in pi["attributes"]:
                    pi_tag = pi["attributes"].get("TAG", pi["attributes"].get("TAGNAME", pi["name"]))
                    pump_issues.append(f"PI '{pi_tag}' manca attributo SCALA nel blocco")

        # Check for suction and discharge lines (simplified proximity check)
        nearby_lines = []
        for b in blocks:
            if b["name"].upper().startswith("LINE") or b.get("layer", "").upper() in (
                "PIPE",
                "LINES",
                "PIPING",
            ):
                dist = (
                    (b["position"][0] - pump["position"][0]) ** 2
                    + (b["position"][1] - pump["position"][1]) ** 2
                ) ** 0.5
                if dist < 500:
                    nearby_lines.append(b)

        if len(nearby_lines) < 2:
            pump_issues.append(
                f"Connessioni linea insufficienti (trovate {len(nearby_lines)}, "
                f"richieste almeno 2: aspirazione + mandata)"
            )

        if pump_issues:
            issues.append({"equipment": pump_tag, "type": "Pompa", "issues": pump_issues})

    return pumps, issues


def verify_tanks(blocks):
    """Verify each tank has at least one LT."""
    tanks = find_equipment(blocks, "TK")
    lt_instruments = find_instruments(blocks, "LT")
    issues = []

    for tank in tanks:
        tank_tag = tank["attributes"].get("TAG", tank["attributes"].get("TAGNAME", tank["name"]))
        tank_issues = []

        associated_lts = []
        for lt in lt_instruments:
            lt_tag = lt["attributes"].get("TAG", lt["attributes"].get("TAGNAME", ""))
            if tank_tag[:3] in lt_tag or abs(lt["position"][0] - tank["position"][0]) < 500:
                associated_lts.append(lt)

        if not associated_lts:
            tank_issues.append("Manca trasmettitore di livello (LT) associato")

        if tank_issues:
            issues.append({"equipment": tank_tag, "type": "Serbatoio", "issues": tank_issues})

    return tanks, issues


def verify_pi_scala(blocks):
    """Verify all PI instruments have SCALA attribute."""
    pi_instruments = find_instruments(blocks, "PI")
    issues = []

    for pi in pi_instruments:
        pi_tag = pi["attributes"].get("TAG", pi["attributes"].get("TAGNAME", pi["name"]))
        if "SCALA" not in pi["attributes"] and "SCALE" not in pi["attributes"]:
            issues.append({
                "equipment": pi_tag,
                "type": "Manometro (PI)",
                "issues": ["Attributo SCALA mancante nel blocco"],
            })

    return pi_instruments, issues


@verifier_bp.route("/")
def verify_page():
    return render_template("verify.html")


@verifier_bp.route("/check", methods=["POST"])
def check_pid():
    if "dxf_file" not in request.files:
        return jsonify({"error": "Nessun file DXF caricato"}), 400

    file = request.files["dxf_file"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "File non valido. Caricare un file .dxf"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    try:
        doc = ezdxf.readfile(filepath)
    except Exception as e:
        return jsonify({"error": f"Errore lettura DXF: {str(e)}"}), 400
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)

    blocks = extract_blocks_and_tags(doc)

    pumps, pump_issues = verify_pumps(blocks)
    tanks, tank_issues = verify_tanks(blocks)
    pi_list, pi_issues = verify_pi_scala(blocks)

    all_issues = pump_issues + tank_issues + pi_issues
    total_blocks = len(blocks)

    summary = {
        "total_blocks": total_blocks,
        "pumps_found": len(pumps),
        "tanks_found": len(tanks),
        "pi_found": len(pi_list),
        "total_issues": len(all_issues),
        "status": "OK" if len(all_issues) == 0 else "PROBLEMI RILEVATI",
    }

    return jsonify({"summary": summary, "issues": all_issues, "filename": filename})
