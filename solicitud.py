import re
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from models import db, User 
from datetime import datetime, date, timedelta
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, Date, ForeignKey
import uuid
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
import qrcode
import base64
import os
from flask import current_app
from werkzeug.utils import secure_filename
import json

# Blueprint para el sistema de solicitudes
solicitud_bp = Blueprint('solicitud', __name__, template_folder='templates', static_folder='static')

# Definición del modelo de Solicitud (sin tocar models.py)
class Solicitud(db.Model):
    __tablename__ = 'solicitudes'
    id = db.Column(db.Integer, primary_key=True)
    numero_solicitud = db.Column(db.String(255), unique=True, nullable=False)
    tipo_servicio = db.Column(db.String(50), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    nombre = db.Column(db.String(255), nullable=True)
    primer_apellido = db.Column(db.String(255), nullable=True)
    segundo_apellido = db.Column(db.String(255), nullable=True)
    telefono = db.Column(db.String(20), nullable=True)

    nombre_empresa = db.Column(db.String(255), nullable=True)
    nombre_contacto = db.Column(db.String(255), nullable=True)
    telefono_empresa = db.Column(db.String(20), nullable=True)
    extension = db.Column(db.String(10), nullable=True)
    whatsapp = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(255), nullable=True)
    horario_atencion = db.Column(db.String(255), nullable=True)
    nota = db.Column(db.Text, nullable=True)

    destino = db.Column(db.String(255), nullable=True)
    cantidad_personas = db.Column(db.Integer, nullable=True)
    actividad = db.Column(db.String(255), nullable=True)
    lugar_salida = db.Column(db.String(255), nullable=True)
    lugar_destino = db.Column(db.String(255), nullable=True)
    puntos_encuentro = db.Column(db.Text, nullable=True)
    hora_salida = db.Column(db.String(10), nullable=True)
    hora_retorno = db.Column(db.String(10), nullable=True)
    fecha_viaje = db.Column(db.Date, nullable=True)
    enlace_mapa = db.Column(db.Text, nullable=True)
    mapa_adjunto = db.Column(db.String(255), nullable=True)

    motivo_cancelacion = db.Column(db.Text, nullable=True)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_cancelacion = db.Column(db.DateTime, nullable=True)

# Nuevo modelo para registrar a los usuarios creados por el formulario de solicitud
class SolicitudUsuario(db.Model):
    __tablename__ = 'solicitud_usuarios'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey('user.id'), unique=True, nullable=False)
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

# Rutas del Blueprint de Solicitud
@solicitud_bp.route('/crear_solicitud', methods=['GET'])
def crear_solicitud():
    tipo_servicio_opciones = ["Particular", "Empresarial"]
    actividad_opciones = ["Senderismo", "Comparsa", "Disciplina Deportiva", "Turismo", "Paseo"]
    return render_template(
        'crear_solicitud.html',
        tipo_servicio_opciones=tipo_servicio_opciones,
        actividad_opciones=actividad_opciones
    )

@solicitud_bp.route('/get_all_users')
def get_all_users():
    users = User.query.all()
    users_data = [{
        'id': user.id,
        'nombre': f"{user.nombre} {user.primer_apellido}",
        'telefono': user.telefono,
        'email': user.email or 'N/A'
    } for user in users]
    return jsonify(users_data)


@solicitud_bp.route('/check_user', methods=['POST'])
def check_user():
    numero_usuario = request.form.get('numero_usuario')
    user = User.query.filter_by(telefono=numero_usuario).first()
    if user:
        viajes = [{
            'id': 1,
            'destino': 'Volcán Irazú',
            'fecha_viaje': '2025-05-20',
            'cancelable': (datetime.strptime('2025-05-20', '%Y-%m-%d').date() - date.today()).days > 5
        }]
        return jsonify({
            'success': True,
            'nombre': f"{user.nombre} {user.primer_apellido}",
            'telefono': user.telefono,
            'es_empresarial': False, 
            'viajes': viajes,
            'message': 'Usuario encontrado.'
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Número de usuario no encontrado. Continúe para crear uno nuevo.'
        })

@solicitud_bp.route('/guardar_solicitud', methods=['POST'])
def guardar_solicitud():
    data = request.json
    user_has_account = data.get('userHasAccount')
    
    tipo_servicio = None
    numero_solicitud_generado = None
    nueva_solicitud = None
    user_id = None

    if user_has_account:
        tipo_servicio = "Particular"
        numero_usuario = data.get('numero_usuario')
        user = User.query.filter_by(telefono=numero_usuario).first()
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado.'})
        
        user_id = user.id
        
        numero_solicitud_generado = f"{user.nombre[0]}{user.primer_apellido[0]}-{str(uuid.uuid4())[:8]}".upper()
        
        destino = data.get('a_donde_va')
        cantidad_personas = data.get('cantidad_personas')
        actividad = data.get('actividad_select')
        lugar_salida = data.get('lugar_salida')
        lugar_destino = data.get('lugar_destino')
        puntos_encuentro = data.get('puntos_encuentro')
        hora_salida = data.get('hora_salida')
        hora_retorno = data.get('hora_retorno')
        fecha_viaje = data.get('fecha')
        enlace_mapa = data.get('enlace_mapa')
        
        nueva_solicitud = Solicitud(
            numero_solicitud=numero_solicitud_generado,
            tipo_servicio=tipo_servicio,
            user_id=user_id,
            nombre=user.nombre,
            primer_apellido=user.primer_apellido,
            segundo_apellido=user.segundo_apellido,
            telefono=user.telefono,
            destino=destino,
            cantidad_personas=cantidad_personas,
            actividad=actividad,
            lugar_salida=lugar_salida,
            lugar_destino=lugar_destino,
            puntos_encuentro=puntos_encuentro,
            hora_salida=hora_salida,
            hora_retorno=hora_retorno,
            fecha_viaje=datetime.strptime(fecha_viaje, '%Y-%m-%d').date() if fecha_viaje else None,
            enlace_mapa=enlace_mapa
        )
    else: # Nuevo usuario ('no')
        tipo_servicio = data.get('tipo_servicio_nuevo')
        if not tipo_servicio:
            return jsonify({'success': False, 'message': 'El tipo de servicio es obligatorio.'})

        if tipo_servicio == "Particular":
            nombre = data.get('nombre_personal')
            primer_apellido = data.get('primer_apellido_personal')
            segundo_apellido = data.get('segundo_apellido_personal')
            telefono = data.get('telefono_personal')
            
            user = User.query.filter_by(telefono=telefono).first()
            if not user:
                nuevo_usuario = User(
                    nombre=nombre,
                    primer_apellido=primer_apellido,
                    segundo_apellido=segundo_apellido,
                    telefono=telefono,
                )
                db.session.add(nuevo_usuario)
                db.session.commit()
                user_id = nuevo_usuario.id
                
                # Crear una entrada en la nueva tabla para registrarlo como usuario de solicitud
                nueva_solicitud_usuario = SolicitudUsuario(user_id=user_id)
                db.session.add(nueva_solicitud_usuario)
                db.session.commit()
            else:
                user_id = user.id
            
            iniciales = (nombre[0] if nombre else '') + \
                        (primer_apellido[0] if primer_apellido else '') + \
                        (segundo_apellido[0] if segundo_apellido else '')
            numero_solicitud_unico = f"{iniciales.upper()}{telefono}-{str(uuid.uuid4())[:8]}"
            numero_solicitud_simple = f"{iniciales.upper()}{telefono}"
            
            destino = data.get('a_donde_va')
            cantidad_personas = data.get('cantidad_personas')
            actividad = data.get('actividad_select')
            lugar_salida = data.get('lugar_salida')
            lugar_destino = data.get('lugar_destino')
            puntos_encuentro = data.get('puntos_encuentro')
            hora_salida = data.get('hora_salida')
            hora_retorno = data.get('hora_retorno')
            fecha_viaje = data.get('fecha')
            enlace_mapa = data.get('enlace_mapa')

            nueva_solicitud = Solicitud(
                numero_solicitud=numero_solicitud_unico,
                tipo_servicio=tipo_servicio,
                user_id=user_id,
                nombre=nombre,
                primer_apellido=primer_apellido,
                segundo_apellido=segundo_apellido,
                telefono=telefono,
                destino=destino,
                cantidad_personas=cantidad_personas,
                actividad=actividad if actividad != 'Otro' else data.get('otra_actividad'),
                lugar_salida=lugar_salida,
                lugar_destino=lugar_destino,
                puntos_encuentro=puntos_encuentro,
                hora_salida=hora_salida,
                hora_retorno=hora_retorno,
                fecha_viaje=datetime.strptime(fecha_viaje, '%Y-%m-%d').date() if fecha_viaje else None,
                enlace_mapa=enlace_mapa
            )

        elif tipo_servicio == "Empresarial":
            nombre_empresa = data.get('nombre_empresa')
            nombre_contacto = data.get('nombre_contacto')
            telefono_empresa = data.get('telefono_empresa')
            extension = data.get('extension')
            whatsapp = data.get('whatsapp_empresa')
            email = data.get('email_empresa')
            horario_atencion = data.get('horario_atencion')
            nota = data.get('nota_empresa')
            
            iniciales = (nombre_contacto[0] if nombre_contacto else '')
            numero_solicitud_unico = f"{iniciales.upper()}{telefono_empresa}-{str(uuid.uuid4())[:8]}"
            numero_solicitud_simple = f"{iniciales.upper()}{telefono_empresa}"

            nueva_solicitud = Solicitud(
                numero_solicitud=numero_solicitud_unico,
                tipo_servicio=tipo_servicio,
                nombre_empresa=nombre_empresa,
                nombre_contacto=nombre_contacto,
                telefono_empresa=telefono_empresa,
                extension=extension,
                whatsapp=whatsapp,
                email=email,
                horario_atencion=horario_atencion,
                nota=nota
            )
        else:
            return jsonify({'success': False, 'message': 'Tipo de servicio no válido.'})

    try:
        db.session.add(nueva_solicitud)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '¡Su solicitud ha sido guardada!',
            'numero_solicitud': numero_solicitud_simple,
            'solicitud_id': nueva_solicitud.id
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error al guardar la solicitud: {e}")
        return jsonify({'success': False, 'message': f'Error al guardar la solicitud: {e}'})

@solicitud_bp.route('/get_solicitud/<int:solicitud_id>')
def get_solicitud(solicitud_id):
    solicitud = Solicitud.query.get(solicitud_id)
    if not solicitud:
        return jsonify({'success': False, 'message': 'Solicitud no encontrada.'})
    
    solicitud_data = {
        'id': solicitud.id,
        'numero_solicitud': solicitud.numero_solicitud,
        'telefono': solicitud.telefono, 
        'whatsapp': solicitud.whatsapp, 
        'telefono_empresa': solicitud.telefono_empresa, 
        'tipo_servicio': solicitud.tipo_servicio, 
        'nombre_empresa': solicitud.nombre_empresa,
        'nombre_contacto': solicitud.nombre_contacto
    }
    return jsonify({'success': True, 'solicitud': solicitud_data})


@solicitud_bp.route('/exportar/<int:solicitud_id>/<string:formato>')
def exportar_solicitud(solicitud_id, formato):
    solicitud = Solicitud.query.get_or_404(solicitud_id)
    
    datos = {
        'Número de Solicitud': solicitud.numero_solicitud,
        'Tipo de Servicio': solicitud.tipo_servicio,
        'Fecha de Solicitud': solicitud.fecha_solicitud.strftime('%Y-%m-%d %H:%M:%S') if solicitud.fecha_solicitud else None,
        'Nombre': solicitud.nombre,
        'Primer Apellido': solicitud.primer_apellido,
        'Segundo Apellido': solicitud.segundo_apellido,
        'Teléfono': solicitud.telefono,
        'Nombre de Empresa': solicitud.nombre_empresa,
        'Nombre de Contacto': solicitud.nombre_contacto,
        'Teléfono de Empresa': solicitud.telefono_empresa,
        'Extensión': solicitud.extension,
        'Whatsapp': solicitud.whatsapp,
        'Email': solicitud.email,
        'Horario de Atención': solicitud.horario_atencion,
        'Nota': solicitud.nota,
        'Destino': solicitud.destino,
        'Cantidad de Personas': solicitud.cantidad_personas,
        'Actividad': solicitud.actividad,
        'Lugar de Salida': solicitud.lugar_salida,
        'Lugar de Destino': solicitud.lugar_destino,
        'Puntos de Encuentro': solicitud.puntos_encuentro,
        'Hora de Salida': solicitud.hora_salida,
        'Hora de Retorno': solicitud.hora_retorno,
        'Fecha del Viaje': solicitud.fecha_viaje.strftime('%Y-%m-%d') if solicitud.fecha_viaje else None,
        'Enlace del Mapa': solicitud.enlace_mapa,
    }
    
    datos_filtrados = {k: v for k, v in datos.items() if v is not None and v != '' and v != 0 and v != 'N/A'}

    if formato == 'txt':
        output = BytesIO()
        for key, value in datos_filtrados.items():
            output.write(f"{key}: {value}\n".encode('utf-8'))
        
        output.seek(0)
        return current_app.send_file(
            output,
            mimetype='text/plain',
            as_attachment=True,
            download_name=f'solicitud_{solicitud.numero_solicitud}.txt'
        )

    elif formato == 'pdf' or formato == 'jpg':
        buffer = BytesIO()
        pdf_c = canvas.Canvas(buffer, pagesize=letter)
        pdf_c.setTitle(f"Solicitud {solicitud.numero_solicitud}")
        
        y_position = 750
        
        qr_data = json.dumps(datos_filtrados)
        qr_img = qrcode.make(qr_data)
        qr_img_stream = BytesIO()
        qr_img.save(qr_img_stream, format='PNG')
        qr_img_stream.seek(0)
        
        qr_size = 100
        pdf_c.drawImage(ImageReader(qr_img_stream), 500, 700, width=qr_size, height=qr_size)
        
        pdf_c.setFont("Helvetica-Bold", 16)
        pdf_c.drawString(50, y_position, f"Solicitud de Viaje #{solicitud.numero_solicitud}")
        y_position -= 20
        
        pdf_c.setFont("Helvetica", 12)
        y_position -= 30
        
        for key, value in datos_filtrados.items():
            pdf_c.drawString(50, y_position, f"• {key}: {value}")
            y_position -= 15
        
        pdf_c.showPage()
        pdf_c.save()
        
        buffer.seek(0)
        
        if formato == 'pdf':
            return current_app.send_file(
                buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=f'solicitud_{solicitud.numero_solicitud}.pdf'
            )
        else:
            return jsonify({'success': False, 'message': 'La exportación a JPG no está completamente implementada, exporta a PDF en su lugar.'})
    
    return jsonify({'success': False, 'message': 'Formato de exportación no válido.'})

# --- RUTAS AÑADIDAS/MODIFICADAS ---

@solicitud_bp.route('/registro')
def registro_solicitudes():
    solicitudes = Solicitud.query.order_by(Solicitud.fecha_solicitud.desc()).all()
    return render_template('registro_solicitudes.html', solicitudes=solicitudes)

@solicitud_bp.route('/ver_solicitud/<int:solicitud_id>')
def ver_solicitud(solicitud_id):
    solicitud = Solicitud.query.get_or_404(solicitud_id)
    return render_template('detalle_solicitud.html', solicitud=solicitud)

@solicitud_bp.route('/registro_usuarios')
def registro_usuarios():
    users = db.session.query(User).join(SolicitudUsuario).order_by(User.id.desc()).all()
    return render_template('registro_usuarios.html', users=users)

@solicitud_bp.route('/eliminar_solicitud/<int:solicitud_id>', methods=['POST'])
def eliminar_solicitud(solicitud_id):
    solicitud = Solicitud.query.get_or_404(solicitud_id)
    try:
        db.session.delete(solicitud)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Solicitud eliminada correctamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al eliminar la solicitud: {e}'})
