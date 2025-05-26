# backend/routes/parts.py
from flask import Blueprint, request, jsonify, make_response, current_app
from flask_cors import cross_origin
from flask_mail import Message
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import re
import os

parts_bp = Blueprint("parts", __name__)

"""
# Configuración de MongoDB…
client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=5000)
client.admin.command('ping')
db = client["TechMaintain"]
parts_collection = db["parts"]
requests_collection = db["requests"]
"""

# Configuración de MongoDB…
MONGO_URI = os.getenv("MONGO_URI",
    "mongodb+srv://clostr1010:clostr123@techmaintain.gb8mby5.mongodb.net/?retryWrites=true&w=majority&appName=TechMaintain")

client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

db = client["TechMaintain"]
parts_collection = db["parts"]
requests_collection = db["requests"]


def format_document(doc):
    d = doc.copy()
    if '_id' in d:
        d['id'] = str(d.pop('_id'))
    for k,v in d.items():
        if isinstance(v, ObjectId):
            d[k] = str(v)
        elif isinstance(v, datetime):
            d[k] = v.isoformat()
    return d

def validate_email(email):
    return re.match(r"^[^@]+@[^@]+\.[^@]+$", email)

# Endpoints para Partes
@parts_bp.route("/parts", methods=["OPTIONS","GET","POST"])
@cross_origin(origins="http://localhost:3000", supports_credentials=True)
def handle_parts():
    if request.method == "OPTIONS":
        return make_response("", 200)
    if request.method == "GET":
        try:
            parts = list(parts_collection.find({}))
            return jsonify([format_document(p) for p in parts]), 200
        except Exception as e:
            current_app.logger.error(f"Error GET /parts: {e}")
            return jsonify({"error": "Error al obtener partes"}), 500

    # POST: crear nueva parte
    if request.method == "POST":
        try:
            data = request.get_json()
            data["createdAt"] = datetime.utcnow()
            result = parts_collection.insert_one(data)
            return jsonify({"id": str(result.inserted_id)}), 201
        except Exception as e:
            current_app.logger.error(f"Error POST /parts: {e}")
            return jsonify({"error": "Error al crear parte"}), 500


@parts_bp.route("/parts/<id>", methods=["OPTIONS","GET","PUT","DELETE"])
@cross_origin(origins="http://localhost:3000", supports_credentials=True)
def handle_single_part(id):
    if request.method == "OPTIONS":
        return make_response("", 200)
    try:
        obj_id = ObjectId(id)
    except:
        return jsonify({"error": "ID inválido"}), 400
    if request.method == "GET":
        part = parts_collection.find_one({"_id": obj_id})
        if not part:
            return jsonify({"error": "Parte no encontrada"}), 404
        return jsonify(format_document(part)), 200
    if request.method == "PUT":
        data = request.get_json()
        result = parts_collection.update_one({"_id": obj_id}, {"$set": data})
        if result.matched_count == 0:
            return jsonify({"error": "Parte no encontrada"}), 404
        return jsonify({"message": "Parte actualizada"}), 200
    if request.method == "DELETE":
        result = parts_collection.delete_one({"_id": obj_id})
        if result.deleted_count == 0:
            return jsonify({"error": "Parte no encontrada"}), 404
        return jsonify({"message": "Parte eliminada"}), 200

# Endpoints para Solicitudes
@parts_bp.route("/requests", methods=["OPTIONS","GET","POST"])
@cross_origin(origins="http://localhost:3000", supports_credentials=True)
def handle_requests():
    if request.method == "OPTIONS":
        return make_response("", 200)
    if request.method == "GET":
        try:
            reqs = list(requests_collection.find({}).sort("request_date", -1))
            return jsonify([format_document(r) for r in reqs]), 200
        except Exception as e:
            current_app.logger.error(f"Error GET /requests: {e}")
            return jsonify({"error": "Error al obtener solicitudes"}), 500

    # POST: crear nueva solicitud
    data = request.get_json()
    # Validaciones básicas
    required = ["partId","quantity","requiredDate","priority","reason","responsible_email"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Faltan campos: {', '.join(missing)}"}), 400
    if not validate_email(data["responsible_email"]):
        return jsonify({"error": "Email inválido"}), 400
    try:
        part_id = ObjectId(data["partId"])
    except:
        return jsonify({"error": "ID de pieza inválido"}), 400
    part = parts_collection.find_one({"_id": part_id})
    if not part:
        return jsonify({"error": "Pieza no encontrada"}), 404
    try:
        qty = int(data["quantity"])
        if qty <= 0:
            raise ValueError
    except:
        return jsonify({"error": "Cantidad debe ser positiva"}), 400
    if part.get("quantity",0) < qty:
        return jsonify({"error": "Cantidad insuficiente","available": part.get("quantity")} ), 400

    new_req = {
        "part_id": part_id,
        "quantity": qty,
        "request_date": datetime.utcnow(),
        "required_date": datetime.fromisoformat(data["requiredDate"]),
        "priority": data["priority"],
        "reason": data["reason"],
        "status": "Pendiente",
        "requester": data.get("requester","Anónimo"),
        "responsible_email": data["responsible_email"]
    }
    try:
        res = requests_collection.insert_one(new_req)
        parts_collection.update_one({"_id": part_id}, {"$inc": {"quantity": -qty}})
        new_req["_id"] = res.inserted_id
        # Enviar notificación
        send_request_notification(format_document(new_req), format_document(part))
        return jsonify(format_document(new_req)), 201
    except Exception as e:
        current_app.logger.error(f"Error POST /requests: {e}")
        return jsonify({"error": "Error procesando solicitud"}), 500

@parts_bp.route("/requests/<id>/status", methods=["OPTIONS","PATCH"])
@cross_origin(origins="http://localhost:3000", supports_credentials=True)
def update_request_status(id):
    if request.method == "OPTIONS":
        return make_response("", 200)
    data = request.get_json()
    status = data.get("status")
    if not status:
        return jsonify({"error": "Estado no proporcionado"}), 400
    try:
        res = requests_collection.update_one({"_id": ObjectId(id)}, {"$set": {"status": status}})
        if res.matched_count == 0:
            return jsonify({"error": "Solicitud no encontrada"}), 404
        return jsonify({"message": "Estado actualizado"}), 200
    except Exception as e:
        current_app.logger.error(f"Error PATCH status: {e}")
        return jsonify({"error": "Error interno"}), 500

# Función de envío de correo
def send_request_notification(request_data: dict, part_data: dict):
    # Formatea fechas
    try:
        rd = datetime.fromisoformat(request_data['required_date']).strftime("%d/%m/%Y")
    except:
        rd = request_data.get('required_date')
    try:
        rq = datetime.fromisoformat(request_data['request_date']).strftime("%d/%m/%Y %H:%M")
    except:
        rq = request_data.get('request_date')

    subject = f"[TECHTEAM] Solicitud {part_data.get('serialNumber','pieza')} – {request_data['priority'].upper()}"
    body = f"""
NUEVA SOLICITUD DE PIEZA – TECHTEAM

Código: {part_data.get('serialNumber','N/A')}
Módulo: {part_data.get('module','N/A')}
Cantidad: {request_data['quantity']}
Prioridad: {request_data['priority'].capitalize()}
Fecha requerida: {rd}
Fecha solicitud: {rq}
Solicitante: {request_data.get('requester','Anónimo')}

Motivo:
{request_data.get('reason','')}
"""
    try:
        # Obtén mail desde current_app
        mail = current_app.extensions.get('mail')
        if not mail:
            current_app.logger.error("❌ Flask-Mail no inicializado.")
            return
        msg = Message(subject=subject,
                      recipients=[request_data['responsible_email']],
                      body=body)
        mail.send(msg)
        current_app.logger.info(f"📧 Correo enviado a {request_data['responsible_email']}")
    except Exception as e:
        current_app.logger.error(f"❌ Error enviando notificación: {e}")

# ----------------------
# Endpoint de prueba SMTP
# ----------------------
@parts_bp.route("/test-email", methods=["GET"])
def test_email():
    mail = current_app.extensions.get('mail')
    if not mail:
        return "Flask-Mail no inicializado", 500
    msg = Message(
        subject="[TEST] SMTP Flask-Mail funcionando?",
        recipients=["tu_correo@dominio.com"],
        body="Si recibes esto, SMTP OK."
    )
    mail.send(msg)
    return "Correo de prueba enviado", 200