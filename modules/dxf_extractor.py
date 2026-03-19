"""
Module 3 - DXF Text & Attribute Extraction
Extracts all texts (TEXT, MTEXT) and block attributes from DXF files.
Exports results as downloadable Excel file.
"""

import io
import os
import ezdxf
import pandas as pd
from flask import Blueprint, render_template, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename

extractor_bp = Blueprint("extractor", __name__)

ALLOWED_EXTENSIONS = {"dxf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def extract_texts(doc):
    """Extract TEXT and MTEXT entities."""
    texts = []
    msp = doc.modelspace()

    for entity in msp:
        if entity.dxftype() == "TEXT":
            texts.append({
                "tipo": "TEXT",
                "testo": entity.dxf.text,
                "layer": entity.dxf.layer,
                "posizione_x": round(entity.dxf.insert.x, 2),
                "posizione_y": round(entity.dxf.insert.y, 2),
                "altezza": round(entity.dxf.height, 2),
                "rotazione": round(getattr(entity.dxf, "rotation", 0), 2),
            })
        elif entity.dxftype() == "MTEXT":
            texts.append({
                "tipo": "MTEXT",
                "testo": entity.text,
                "layer": entity.dxf.layer,
                "posizione_x": round(entity.dxf.insert.x, 2),
                "posizione_y": round(entity.dxf.insert.y, 2),
                "altezza": round(entity.dxf.char_height, 2),
                "rotazione": round(getattr(entity.dxf, "rotation", 0), 2),
            })

    return texts


def extract_attributes(doc):
    """Extract block INSERT entities with their attributes."""
    attributes = []
    msp = doc.modelspace()

    for entity in msp:
        if entity.dxftype() == "INSERT":
            block_name = entity.dxf.name
            layer = entity.dxf.layer
            pos_x = round(entity.dxf.insert.x, 2)
            pos_y = round(entity.dxf.insert.y, 2)

            if entity.attribs:
                for attrib in entity.attribs:
                    attributes.append({
                        "blocco": block_name,
                        "layer": layer,
                        "posizione_x": pos_x,
                        "posizione_y": pos_y,
                        "attributo_tag": attrib.dxf.tag,
                        "attributo_valore": attrib.dxf.text,
                    })
            else:
                attributes.append({
                    "blocco": block_name,
                    "layer": layer,
                    "posizione_x": pos_x,
                    "posizione_y": pos_y,
                    "attributo_tag": "",
                    "attributo_valore": "",
                })

    return attributes


@extractor_bp.route("/")
def extract_page():
    return render_template("extract.html")


@extractor_bp.route("/analyze", methods=["POST"])
def analyze_dxf():
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

    texts = extract_texts(doc)
    attributes = extract_attributes(doc)

    return jsonify({
        "filename": filename,
        "texts": texts,
        "attributes": attributes,
        "summary": {
            "total_texts": len(texts),
            "total_attributes": len(attributes),
            "layers": list(set(t["layer"] for t in texts + attributes)),
        },
    })


@extractor_bp.route("/export", methods=["POST"])
def export_excel():
    """Export extracted data to Excel."""
    data = request.get_json()
    texts = data.get("texts", [])
    attributes = data.get("attributes", [])

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if texts:
            df_texts = pd.DataFrame(texts)
            df_texts.to_excel(writer, sheet_name="Testi", index=False)
        if attributes:
            df_attrs = pd.DataFrame(attributes)
            df_attrs.to_excel(writer, sheet_name="Attributi", index=False)

    output.seek(0)
    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="dxf_extraction.xlsx",
    )
