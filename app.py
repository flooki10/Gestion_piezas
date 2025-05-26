# backend/app.py
from flask import Flask
from flask_cors import CORS
from flask_mail import Mail

from routes.parts import parts_bp
from routes.auth import auth_bp  # si lo usas

mail = Mail()

def create_app():
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})
    app.config.update(
        MAIL_SERVER='smtp.gmail.com',
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME='walidsabhi99@gmail.com',        # Cambia por tu email
        MAIL_PASSWORD='dpwu jbux pkvy nrlr',           # App Password de Gmail
        MAIL_DEFAULT_SENDER=('TechMaintain','noreply@techmaintain.com'),
        MAIL_DEBUG=True
    )
    mail.init_app(app)
    app.register_blueprint(parts_bp, url_prefix="/api")
    app.register_blueprint(auth_bp, url_prefix="/api")
    app.logger.setLevel('DEBUG')
    return app

if __name__=="__main__":
    app = create_app()
    app.run(debug=True, port=5000)
