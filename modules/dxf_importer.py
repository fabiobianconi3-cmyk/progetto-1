"""
Module 4 - Excel to DXF Tag Importer
Reads updated tags from an Excel file and applies them to a DXF file.
The Excel must have columns: blocco, attributo_tag, vecchio_valore, nuovo_valore
"""

import os
import io
import ezdxf
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename

importer_bp = Blueprint("importer", __name__)

ALLOWED_DXF = {"dxf"}
ALLOWED_EXCEL = {"xlsx", "xls"}


def allowed_dxf(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_DXF


def allowed_excel(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXCEL


def read_update_map(excel_path):
    """Read the Excel update mapping.
    Expected columns: blocco, attributo_tag, vecchio_valore, nuovo_valore
    """
    df = pd.read_excel(excel_path)
    required_cols = {"blocco", "attributo_tag", "nuovo_valore"}
    actual_cols = {c.lower().strip() for c in df.columns}

    if not required_cols.issubset(actual_cols):
        missing = required_cols - actual_cols
        raise ValueError(f"Colonne mancanti nel file Excel: {', '.join(missing)}")

    df.columns = [c.lower().strip() for c in df.columns]
    return df


def apply_updates(doc, updates_df):
    """Apply tag updates from DataFrame to DXF document."""
    msp = doc.modelspace()
    results = []

    for _, row in updates_df.iterrows():
        target_block = str(row["blocco"]).strip()
        target_attr = str(row["attributo_tag"]).strip().upper()
        new_value = str(row["nuovo_valore"]).strip()
        old_value = str(row.get("vecchio_valore", "")).strip() if "vecchio_valore" in row.index else None

        found = False
        for entity in msp:
            if entity.dxftype() != "INSERT":
                continue
            if entity.dxf.name != target_block:
                continue

            for attrib in entity.attribs:
                if attrib.dxf.tag.upper() != target_attr:
                    continue

                current_value = attrib.dxf.text
                # If old_value specified, only update matching attributes
                if old_value and old_value != current_value:
                    continue

                attrib.dxf.text = new_value
                results.append({
                    "blocco": target_block,
                    "attributo": target_attr,
                    "vecchio_valore": current_value,
                    "nuovo_valore": new_value,
                    "stato": "Aggiornato",
                })
                found = True

        if not found:
            results.append({
                "blocco": target_block,
                "attributo": target_attr,
                "vecchio_valore": old_value or "N/A",
                "nuovo_valore": new_value,
                "stato": "Non trovato",
            })

    return results


@importer_bp.route("/")
def import_page():
    return render_template("import.html")


@importer_bp.route("/update", methods=["POST"])
def update_dxf():
    if "dxf_file" not in request.files or "excel_file" not in request.files:
        return jsonify({"error": "Caricare sia il file DXF che il file Excel"}), 400

    dxf_file = request.files["dxf_file"]
    excel_file = request.files["excel_file"]

    if not allowed_dxf(dxf_file.filename):
        return jsonify({"error": "File DXF non valido"}), 400
    if not allowed_excel(excel_file.filename):
        return jsonify({"error": "File Excel non valido"}), 400

    dxf_filename = secure_filename(dxf_file.filename)
    excel_filename = secure_filename(excel_file.filename)
    dxf_path = os.path.join(current_app.config["UPLOAD_FOLDER"], dxf_filename)
    excel_path = os.path.join(current_app.config["UPLOAD_FOLDER"], excel_filename)

    dxf_file.save(dxf_path)
    excel_file.save(excel_path)

    try:
        doc = ezdxf.readfile(dxf_path)
    except Exception as e:
        if os.path.exists(excel_path):
            os.remove(excel_path)
        return jsonify({"error": f"Errore lettura DXF: {str(e)}"}), 400

    try:
        updates_df = read_update_map(excel_path)
    except ValueError as e:
        if os.path.exists(dxf_path):
            os.remove(dxf_path)
        if os.path.exists(excel_path):
            os.remove(excel_path)
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        if os.path.exists(dxf_path):
            os.remove(dxf_path)
        if os.path.exists(excel_path):
            os.remove(excel_path)
        return jsonify({"error": f"Errore lettura Excel: {str(e)}"}), 400
    finally:
        if os.path.exists(excel_path):
            os.remove(excel_path)

    results = apply_updates(doc, updates_df)

    # Save updated DXF
    output_name = f"updated_{dxf_filename}"
    output_path = os.path.join(current_app.config["UPLOAD_FOLDER"], output_name)
    doc.saveas(output_path)

    if os.path.exists(dxf_path):
        os.remove(dxf_path)

    updated_count = sum(1 for r in results if r["stato"] == "Aggiornato")
    not_found_count = sum(1 for r in results if r["stato"] == "Non trovato")

    return jsonify({
        "results": results,
        "summary": {
            "total": len(results),
            "updated": updated_count,
            "not_found": not_found_count,
        },
        "download_filename": output_name,
    })


@importer_bp.route("/download/<filename>")
def download_updated(filename):
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], secure_filename(filename))
    if not os.path.exists(filepath):
        return jsonify({"error": "File non trovato"}), 404

    return send_file(
        filepath,
        mimetype="application/octet-stream",
        as_attachment=True,
        download_name=filename,
    )
