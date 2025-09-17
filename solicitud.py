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
import json
from sqlalchemy import or_

# Blueprint para el sistema de solicitudes
solicitud_bp = Blueprint('solicitud', __name__, template_folder='templates', static_folder='static')

# Definición del modelo de Solicitud (se mantiene en solicitud.py como se indicó)
class Solicitud(db.Model):
    __tablename__ = 'solicitudes'
    id = db.Column(db.Integer, primary_key=True)
    numero_solicitud = db.Column(db.String(255), unique=True, nullable=False)
    # Columna tipo_servicio (Particular o Empresarial)
    tipo_servicio = db.Column(db.String(50), nullable=False)
    # Relación con el usuario si existe
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Datos Personales / Empresariales
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

    # Datos del Viaje
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

    # Datos de Cancelación
    motivo_cancelacion = db.Column(db.Text, nullable=True)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_cancelacion = db.Column(db.DateTime, nullable=True)

# Rutas del Blueprint de Solicitud
@solicitud_bp.route('/crear_solicitud', methods=['GET', 'POST'])
def crear_solicitud():
    tipo_servicio_opciones = ["Particular", "Empresarial"]
    actividad_opciones = ["Senderismo", "Comparsa", "Disciplina Deportiva", "Turismo", "Paseo"]
    return render_template(
        'crear_solicitud.html',
        tipo_servicio_opciones=tipo_servicio_opciones,
        actividad_opciones=actividad_opciones
    )
    
@solicitud_bp.route('/registro_solicitudes')
def registro_solicitudes():
    solicitudes = Solicitud.query.order_by(Solicitud.id.desc()).all()
    return render_template('registro_solicitudes.html', solicitudes=solicitudes)

@solicitud_bp.route('/consulta_usuarios')
def consulta_usuarios():
    users = User.query.all()
    return render_template('consulta_usuarios.html', users=users)

@solicitud_bp.route('/editar_usuario/<int:user_id>')
def editar_usuario(user_id):
    user = User.query.get_or_404(user_id)
    return render_template('editar_usuario.html', user=user)

@solicitud_bp.route('/guardar_usuario', methods=['POST'])
def guardar_usuario():
    try:
        data = request.json
        user_id = data.get('id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado.'})

        user.nombre = data.get('nombre')
        user.primer_apellido = data.get('primer_apellido')
        user.segundo_apellido = data.get('segundo_apellido')
        user.telefono = data.get('telefono')
        user.email = data.get('email')

        db.session.commit()
        return jsonify({'success': True, 'message': 'Usuario actualizado correctamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Error al guardar el usuario: {str(e)}'})

@solicitud_bp.route('/eliminar_usuario/<int:user_id>', methods=['POST'])
def eliminar_usuario(user_id):
    try:
        user = User.query.get_or_404(user_id)
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Usuario eliminado correctamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Ocurrió un error al eliminar el usuario: {str(e)}'})

@solicitud_bp.route('/ver_detalle_solicitud/<int:solicitud_id>')
def ver_detalle_solicitud(solicitud_id):
    solicitud = Solicitud.query.get(solicitud_id)
    if not solicitud:
        return render_template('detalle_solicitud.html', solicitud=None, error_message="No existen Solicitudes con este ID."), 404
    return render_template('detalle_solicitud.html', solicitud=solicitud)

@solicitud_bp.route('/check_user', methods=['POST'])
def check_user():
    numero_usuario = request.form.get('numero_usuario')
    user = User.query.filter_by(telefono=numero_usuario).first()

    if user:
        solicitudes = Solicitud.query.filter(
            or_(
                Solicitud.user_id == user.id,
                Solicitud.telefono == numero_usuario # Para solicitudes empresariales sin user_id
            )
        ).order_by(Solicitud.id.desc()).all()
        
        viajes = []
        for s in solicitudes:
            viajes.append({
                'id': s.id,
                'destino': s.destino,
                'fecha_viaje': s.fecha_viaje.strftime('%Y-%m-%d') if s.fecha_viaje else '',
                'estado': 'Pendiente' if s.fecha_viaje and s.fecha_viaje >= date.today() else 'Culminado',
                'cancelable': (s.fecha_viaje - date.today()).days > 5 if s.fecha_viaje else False
            })
            
        return jsonify({
            'success': True,
            'id': user.id,
            'nombre': user.nombre,
            'primer_apellido': user.primer_apellido,
            'segundo_apellido': user.segundo_apellido,
            'telefono': user.telefono,
            'es_empresarial': False, # Se asume que el usuario es particular.
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
    tipo_servicio = data.get('tipo_servicio_nuevo') or "Particular" # Asumir Particular si ya tiene cuenta

    # Recoger datos del formulario de viaje (siempre se recogen)
    destino = data.get('a_donde_va')
    cantidad_personas_str = data.get('cantidad_personas')
    cantidad_personas = int(cantidad_personas_str) if cantidad_personas_str and cantidad_personas_str.isdigit() else None
    actividad_select = data.get('actividad_select')
    otra_actividad = data.get('otra_actividad')
    actividad = otra_actividad if actividad_select == 'Otro' else actividad_select
    lugar_salida = data.get('lugar_salida')
    lugar_destino = data.get('lugar_destino')
    puntos_encuentro = data.get('puntos_encuentro')
    hora_salida = data.get('hora_salida')
    hora_retorno = data.get('hora_retorno')
    fecha_viaje_str = data.get('fecha')
    fecha_viaje = datetime.strptime(fecha_viaje_str, '%Y-%m-%d').date() if fecha_viaje_str else None
    enlace_mapa = data.get('enlace_mapa')
    
    # Validar que los campos de viaje no estén vacíos antes de guardar
    if not (destino and cantidad_personas and actividad and lugar_salida and lugar_destino and fecha_viaje):
        return jsonify({'success': False, 'message': 'Faltan datos obligatorios del viaje.'})
        
    nueva_solicitud = None
    if user_has_account:
        # Lógica para usuario existente
        user_id = data.get('id')
        user = User.query.get(user_id)
        if not user:
            return jsonify({'success': False, 'message': 'Usuario no encontrado.'})
        
        iniciales = (user.nombre[0] if user.nombre else '') + \
                    (user.primer_apellido[0] if user.primer_apellido else '') + \
                    (user.segundo_apellido[0] if user.segundo_apellido else '')
        numero_solicitud_generado = f"{iniciales.upper()}{user.telefono}-{str(uuid.uuid4())[:8]}".upper()

        nueva_solicitud = Solicitud(
            numero_solicitud=numero_solicitud_generado,
            tipo_servicio="Particular",
            user_id=user.id,
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
            fecha_viaje=fecha_viaje,
            enlace_mapa=enlace_mapa
        )
    else: # Nuevo usuario
        if tipo_servicio == "Particular":
            nombre = data.get('nombre_personal')
            primer_apellido = data.get('primer_apellido_personal')
            segundo_apellido = data.get('segundo_apellido_personal')
            telefono = data.get('telefono_personal')

            if not (nombre and primer_apellido and telefono):
                return jsonify({'success': False, 'message': 'Faltan datos personales obligatorios.'})

            iniciales = (nombre[0] if nombre else '') + \
                        (primer_apellido[0] if primer_apellido else '') + \
                        (segundo_apellido[0] if segundo_apellido else '')
            numero_solicitud_generado = f"{iniciales.upper()}{telefono}-{str(uuid.uuid4())[:8]}"

            # Crear el nuevo usuario en la base de datos de usuarios
            nuevo_usuario = User(
                username=str(uuid.uuid4()),
                nombre=nombre,
                primer_apellido=primer_apellido,
                segundo_apellido=segundo_apellido,
                telefono=telefono,
                email=f"{str(uuid.uuid4())[:8]}@example.com"
            )
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            nueva_solicitud = Solicitud(
                numero_solicitud=numero_solicitud_generado,
                tipo_servicio=tipo_servicio,
                user_id=nuevo_usuario.id,
                nombre=nombre,
                primer_apellido=primer_apellido,
                segundo_apellido=segundo_apellido,
                telefono=telefono,
                destino=destino,
                cantidad_personas=cantidad_personas,
                actividad=actividad,
                lugar_salida=lugar_salida,
                lugar_destino=lugar_destino,
                puntos_encuentro=puntos_encuentro,
                hora_salida=hora_salida,
                hora_retorno=hora_retorno,
                fecha_viaje=fecha_viaje,
                enlace_mapa=enlace_mapa
            )
        elif tipo_servicio == "Empresarial":
            # Lógica para nuevo usuario empresarial
            nombre_empresa = data.get('nombre_empresa')
            nombre_contacto = data.get('nombre_contacto')
            telefono_empresa = data.get('telefono_empresa')

            if not (nombre_empresa and nombre_contacto and telefono_empresa):
                return jsonify({'success': False, 'message': 'Faltan datos empresariales obligatorios.'})

            iniciales = (nombre_contacto[0] if nombre_contacto else '')
            numero_solicitud_generado = f"{iniciales.upper()}{telefono_empresa}-{str(uuid.uuid4())[:8]}"

            nueva_solicitud = Solicitud(
                numero_solicitud=numero_solicitud_generado,
                tipo_servicio=tipo_servicio,
                nombre_empresa=nombre_empresa,
                nombre_contacto=nombre_contacto,
                telefono_empresa=telefono_empresa,
                extension=data.get('extension'),
                whatsapp=data.get('whatsapp_empresa'),
                email=data.get('email_empresa'),
                horario_atencion=data.get('horario_atencion'),
                nota=data.get('nota_empresa'),
                destino=destino,
                cantidad_personas=cantidad_personas,
                actividad=actividad,
                lugar_salida=lugar_salida,
                lugar_destino=lugar_destino,
                puntos_encuentro=puntos_encuentro,
                hora_salida=hora_salida,
                hora_retorno=hora_retorno,
                fecha_viaje=fecha_viaje,
                enlace_mapa=enlace_mapa
            )
        else:
            return jsonify({'success': False, 'message': 'Tipo de servicio no válido.'})

    try:
        db.session.add(nueva_solicitud)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': '¡Su solicitud ha sido guardada!',
            'numero_solicitud': nueva_solicitud.numero_solicitud,
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
        'telefono': solicitud.telefono, # Añadir teléfono para el botón de WhatsApp
        'whatsapp': solicitud.whatsapp, # Añadir WhatsApp para el botón de WhatsApp empresarial
        'telefono_empresa': solicitud.telefono_empresa, # Añadir Teléfono de la empresa
        'tipo_servicio': solicitud.tipo_servicio, # Añadir el tipo de servicio
        'nombre_empresa': solicitud.nombre_empresa,
        'nombre_contacto': solicitud.nombre_contacto,
        'destino': solicitud.destino,
        'cantidad_personas': solicitud.cantidad_personas,
        'actividad': solicitud.actividad,
        'lugar_salida': solicitud.lugar_salida,
        'lugar_destino': solicitud.lugar_destino,
        'puntos_encuentro': solicitud.puntos_encuentro,
        'hora_salida': solicitud.hora_salida,
        'hora_retorno': solicitud.hora_retorno,
        'fecha_viaje': solicitud.fecha_viaje.strftime('%Y-%m-%d') if solicitud.fecha_viaje else None,
        'enlace_mapa': solicitud.enlace_mapa
    }
    return jsonify({'success': True, 'solicitud': solicitud_data})


@solicitud_bp.route('/exportar/<int:solicitud_id>/<string:formato>')
def exportar_solicitud(solicitud_id, formato):
    solicitud = Solicitud.query.get_or_404(solicitud_id)
    
    # 1. Recopilar datos y limpiar campos vacíos o con valores en cero
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
        # ... y cualquier otro campo que desees exportar
    }
    
    # Filtrar campos nulos, vacíos o en cero
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
        
        # Generar y dibujar el código de barras/QR
        qr_data = json.dumps(datos_filtrados)
        qr_img = qrcode.make(qr_data)
        qr_img_stream = BytesIO()
        qr_img.save(qr_img_stream, format='PNG')
        qr_img_stream.seek(0)
        
        # Ajusta el tamaño y la posición del código QR
        qr_size = 100
        pdf_c.drawImage(ImageReader(qr_img_stream), 500, 700, width=qr_size, height=qr_size)
        
        # Dibujar los datos
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
            # Para JPG, se puede generar el PDF y luego convertir, o usar una librería de imagen.
            # Este es un enfoque simplificado, la conversión real es más compleja.
            # Por ahora, devolvemos un mensaje o un PDF renombrado.
            # Puedes usar una herramienta como `Wand` para convertir PDF a JPG
            # `from wand.image import Image`
            # `with Image(file=buffer, resolution=150) as img:`
            # `    img.format = 'jpeg'`
            # `    return current_app.send_file(img, mimetype='image/jpeg', as_attachment=True, download_name=f'solicitud_{solicitud.numero_solicitud}.jpg')`
            return jsonify({'success': False, 'message': 'La exportación a JPG no está completamente implementada, exporta a PDF en su lugar.'})
    
    return jsonify({'success': False, 'message': 'Formato de exportación no válido.'})

@solicitud_bp.route('/eliminar_solicitud/<int:solicitud_id>', methods=['POST'])
def eliminar_solicitud(solicitud_id):
    try:
        solicitud = Solicitud.query.get_or_404(solicitud_id)
        db.session.delete(solicitud)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Solicitud eliminada correctamente.'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Ocurrió un error al eliminar la solicitud.'})
