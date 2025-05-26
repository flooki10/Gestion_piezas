from flask import Blueprint, request, jsonify, make_response
from werkzeug.security import check_password_hash, generate_password_hash
import smtplib
from email.mime.text import MIMEText

auth_bp = Blueprint("auth", __name__)

# 👉 Usuario “admin” con contraseña hasheada en memoria
USERS = {
    "admin": generate_password_hash("admin")
}

@auth_bp.route("/login", methods=["POST", "OPTIONS"])
def login():
    # Soporta preflight CORS
    if request.method == "OPTIONS":
        return _build_cors_preflight_response()

    data = request.get_json() or {}
    user = data.get("username")
    pwd  = data.get("password")

    if not user or not pwd:
        return jsonify({"success": False, "message": "Usuario y contraseña requeridos"}), 400

    stored = USERS.get(user)
    if not stored or not check_password_hash(stored, pwd):
        return jsonify({"success": False, "message": "Credenciales inválidas"}), 401

    # Envío de token simulado (podrías usar JWT aquí)
    token = "jwt_token_de_ejemplo"
    resp = make_response(jsonify({"success": True, "token": token}))
    # Si quieres usar cookie en lugar de localStorage:
    # resp.set_cookie("session", token, httponly=True, samesite="None", secure=False, domain="localhost")
    return resp

def _build_cors_preflight_response():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "http://localhost:3000")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type")
    response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response



@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    email = request.json.get('email')

    if not email:
        return jsonify({"message": "Correo electrónico es requerido"}), 400

    if '@' not in email or '.' not in email:
        return jsonify({"message": "Correo electrónico inválido"}), 400

    try:
        send_recovery_email(email)
        return jsonify({"message": "Correo de recuperación enviado correctamente."}), 200
    except Exception as e:
        return jsonify({"message": str(e)}), 500


def send_recovery_email(email):
    try:
        smtp_server = "smtp.tucorreo.com"
        smtp_port = 587
        smtp_user = "tucorreo@dominio.com"
        smtp_password = "tu_password"

        msg = MIMEText("Haz clic aquí para restablecer tu contraseña: http://tuapp.com/reset-password")
        msg["From"] = smtp_user
        msg["To"] = email
        msg["Subject"] = "Recuperación de Contraseña"

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

    except Exception as e:
        raise Exception(f"Error al enviar correo: {e}")
