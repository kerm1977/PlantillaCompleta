# models.py
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from datetime import datetime, date, time
import json
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, Date, Time, UniqueConstraint
from sqlalchemy.orm import relationship
import sqlalchemy as sa

db = SQLAlchemy()
bcrypt = Bcrypt()
migrate = Migrate()

# --- MODELOS DE LA APLICACIÓN ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password = db.Column(db.String(200), nullable=True) 
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)
    avatar_url = db.Column(db.String(200), nullable=True, default='uploads/avatars/default.png')
    segundo_apellido = db.Column(db.String(100), nullable=True)
    telefono_emergencia = db.Column(db.String(20), nullable=True)
    nombre_emergencia = db.Column(db.String(100), nullable=True)
    empresa = db.Column(db.String(100), nullable=True)
    cedula = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)
    actividad = db.Column(db.String(100), nullable=True)
    capacidad = db.Column(db.String(50), nullable=True)
    participacion = db.Column(db.String(100), nullable=True)
    fecha_cumpleanos = db.Column(db.Date, nullable=True)
    tipo_sangre = db.Column(db.String(5), nullable=True)
    poliza = db.Column(db.String(100), nullable=True)
    aseguradora = db.Column(db.String(100), nullable=True)
    alergias = db.Column(db.Text, nullable=True)
    enfermedades_cronicas = db.Column(db.Text, nullable=True)
    role = db.Column(db.String(50), nullable=False, default='Usuario Regular')
    last_login_at = db.Column(db.DateTime, nullable=True)
    
    auto_logout_minutes = db.Column(db.Integer, default=0, nullable=False, server_default='0')
    auto_logout_enabled = db.Column(db.Boolean, default=False, nullable=False, server_default='0')

    # AÑADIDO: Campo para el tema preferido del usuario
    theme = db.Column(db.String(10), nullable=False, default='light', server_default='light')

    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, server_default=sa.func.now())
    fecha_actualizacion = db.Column(db.DateTime, onupdate=datetime.utcnow)

    oauth_logins = db.relationship('OAuthSignIn', backref='user', lazy=True, cascade="all, delete-orphan")
    __table_args__ = (
        UniqueConstraint('username', name='uq_user_username'),
        UniqueConstraint('email', name='uq_user_email'),
    )

    def get_reset_token(self, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({'user_id': self.id})

    @staticmethod
    def verify_reset_token(token, expires_sec=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=expires_sec)['user_id']
        except:
            return None
        return User.query.get(user_id)

    def __repr__(self):
        return f'<User {self.username}>'

class OAuthSignIn(db.Model):
    __tablename__ = 'oauth_signin'
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    provider_user_id = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), nullable=False)
    __table_args__ = (
        UniqueConstraint('provider', 'provider_user_id', name='uq_oauth_signin_provider_user_id'),
    )

    def __repr__(self):
        return f'<OAuthSignIn {self.provider} para {self.user.username}>'

class AboutUs(db.Model):
    __tablename__ = 'about_us'
    id = db.Column(db.Integer, primary_key=True)
    logo_filename = db.Column(db.String(255), nullable=False)
    logo_info = db.Column(db.Text, nullable=True)
    title = db.Column(db.String(255), nullable=False)
    detail = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<AboutUs {self.title}>"

class PushSubscription(db.Model):
    __tablename__ = 'push_subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(120), nullable=True) 
    endpoint = db.Column(db.String(500), unique=True, nullable=False)
    p256dh_key = db.Column(db.String(255), nullable=False)
    auth_key = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f"<PushSubscription {self.endpoint}>"

    def to_dict(self):
        return {
            "endpoint": self.endpoint,
            "keys": {
                "p256dh": self.p256dh_key,
                "auth": self.auth_key
            }
        }


