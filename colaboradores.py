# colaboradores.py
# Módulo de colaboradores
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory, current_app
from models import db, User
from functools import wraps
from datetime import datetime, date
from werkzeug.utils import secure_filename
import os
import re
import json
import uuid
import tempfile
import qrcode
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
import pandas as pd
from sqlalchemy.orm.attributes import get_history

# Define el Blueprint
colaboradores_bp = Blueprint('colaboradores', __name__)

# NUEVO FILTRO PARA CONVERTIR A JSON DENTRO DEL BLUEPRINT
def to_json_filter(value):
    """
    Convierte un objeto de Python a una cadena JSON.
    """
    # Función de serialización personalizada para objetos de base de datos
    def serialize_colaborador(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, db.Model):
            # Lógica para serializar relaciones de vehículos
            data = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
            if hasattr(obj, 'vehiculos'):
                data['vehiculos'] = [serialize_vehiculo(v) for v in obj.vehiculos]
            return data
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    def serialize_vehiculo(vehiculo):
        data = {c.name: getattr(vehiculo, c.name) for c in vehiculo.__table__.columns}
        if hasattr(vehiculo, 'revisiones_tecnicas'):
            data['revisiones_tecnicas'] = [
                {c.name: getattr(r, c.name) for c in r.__table__.columns}
                for r in vehiculo.revisiones_tecnicas
            ]
        if hasattr(vehiculo, 'polizas'):
            data['polizas'] = [
                {c.name: getattr(p, c.name) for c in p.__table__.columns}
                for p in vehiculo.polizas
            ]
        if hasattr(vehiculo, 'fotografias'):
            data['fotografias'] = [
                {c.name: getattr(f, c.name) for c in f.__table__.columns}
                for f in vehiculo.fotografias
            ]
        return data

    return json.dumps(value, default=serialize_colaborador)

# Registra el filtro con el Blueprint
colaboradores_bp.app_template_filter('to_json')(to_json_filter)

# Modelos (se deben mover a models.py si no están ya ahí, pero se incluyen aquí para la demostración)
class Colaborador(db.Model):
    __tablename__ = 'colaboradores'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    primer_apellido = db.Column(db.String(100), nullable=False)
    segundo_apellido = db.Column(db.String(100), nullable=True)
    cedula = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    telefono = db.Column(db.String(20), nullable=False)
    movil = db.Column(db.String(20), nullable=True)
    foto_perfil = db.Column(db.String(200), nullable=True, default='uploads/colaboradores/default.png')
    vehiculos = db.relationship('Vehiculo', backref='colaborador', lazy=True, cascade="all, delete-orphan")
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Vehiculo(db.Model):
    __tablename__ = 'vehiculos'
    id = db.Column(db.Integer, primary_key=True)
    colaborador_id = db.Column(db.Integer, db.ForeignKey('colaboradores.id'), nullable=False)
    marca = db.Column(db.String(50), nullable=False)
    modelo = db.Column(db.String(50), nullable=False)
    tipo_combustible = db.Column(db.String(20), nullable=False)
    anio = db.Column(db.Integer, nullable=False)
    propietario_registral = db.Column(db.String(100), nullable=False)
    tipo_servicio = db.Column(db.String(50), nullable=False)
    capacidad = db.Column(db.Integer, nullable=False)
    estado_vehiculo = db.Column(db.String(50), nullable=False)
    revisiones_tecnicas = db.relationship('RevisionTecnica', backref='vehiculo', lazy=True, cascade="all, delete-orphan")
    polizas = db.relationship('Poliza', backref='vehiculo', lazy=True, cascade="all, delete-orphan")
    fotografias = db.relationship('FotografiaVehiculo', backref='vehiculo', lazy=True, cascade="all, delete-orphan")

class RevisionTecnica(db.Model):
    __tablename__ = 'revisiones_tecnicas'
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculos.id'), nullable=False)
    placa = db.Column(db.String(20), nullable=False)
    fecha_primera_revision = db.Column(db.Date, nullable=False)
    fecha_segunda_revision = db.Column(db.Date, nullable=True)

class Poliza(db.Model):
    __tablename__ = 'polizas'
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculos.id'), nullable=False)
    numero_poliza = db.Column(db.String(50), nullable=False)
    cobertura_desde = db.Column(db.Date, nullable=False)
    cobertura_hasta = db.Column(db.Date, nullable=False)
    fecha_limite_pago = db.Column(db.Date, nullable=False)

class FotografiaVehiculo(db.Model):
    __tablename__ = 'fotografias_vehiculos'
    id = db.Column(db.Integer, primary_key=True)
    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculos.id'), nullable=False)
    url_foto = db.Column(db.String(200), nullable=False)

def role_required(roles):
    if not isinstance(roles, list):
        roles = [roles]
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session:
                flash('Por favor, inicia sesión para acceder a esta página.', 'info')
                return redirect(url_for('login'))
            user_role = session.get('role')
            if user_role not in roles:
                flash('No tienes permiso para acceder a esta página.', 'danger')
                return redirect(url_for('perfil.perfil'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Rutas para el Blueprint de Colaboradores
@colaboradores_bp.route('/colaboradores/crear', methods=['GET', 'POST'])
@role_required(['Superuser', 'Administrador'])
def crear_colaborador():
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            nombre = request.form['nombre']
            primer_apellido = request.form['primer_apellido']
            segundo_apellido = request.form.get('segundo_apellido')
            cedula = request.form['cedula']
            email = request.form['email']
            telefono = request.form['telefono']
            movil = request.form.get('movil')

            # Validar que los campos numéricos no contengan letras o caracteres especiales
            if not telefono.isdigit() or (movil and not movil.isdigit()):
                flash('Los campos de teléfono y móvil solo deben contener números.', 'danger')
                return redirect(url_for('colaboradores.crear_colaborador'))

            # Manejo de la foto del colaborador
            foto_perfil_url = 'uploads/colaboradores/default.png'
            if 'foto_perfil' in request.files and request.files['foto_perfil'].filename != '':
                foto_perfil = request.files['foto_perfil']
                filename = secure_filename(foto_perfil.filename)
                ext = filename.rsplit('.', 1)[1].lower()
                if ext not in ['jpg', 'png', 'jpeg']:
                    flash('Formato de imagen de perfil no permitido.', 'danger')
                    return redirect(url_for('colaboradores.crear_colaborador'))
                unique_filename = f"{uuid.uuid4()}.{ext}"
                foto_perfil_path = os.path.join(current_app.config['UPLOAD_FILES_FOLDER'], unique_filename)
                foto_perfil.save(foto_perfil_path)
                foto_perfil_url = f'uploads/colaboradores/{unique_filename}'

            # Crear el nuevo colaborador
            new_colaborador = Colaborador(
                nombre=nombre,
                primer_apellido=primer_apellido,
                segundo_apellido=segundo_apellido,
                cedula=cedula,
                email=email,
                telefono=telefono,
                movil=movil,
                foto_perfil=foto_perfil_url
            )
            db.session.add(new_colaborador)
            db.session.commit()

            # Manejar los datos del vehículo
            vehiculos_data = json.loads(request.form.get('vehiculos_data', '[]'))
            for v_data in vehiculos_data:
                # Validar campos numéricos del vehículo
                if 'capacidad' in v_data and not str(v_data['capacidad']).isdigit():
                    flash('El campo capacidad del vehículo solo debe contener números.', 'danger')
                    db.session.rollback()
                    return redirect(url_for('colaboradores.crear_colaborador'))

                new_vehiculo = Vehiculo(
                    colaborador_id=new_colaborador.id,
                    marca=v_data['marca'],
                    modelo=v_data['modelo'],
                    tipo_combustible=v_data['tipo_combustible'],
                    anio=int(v_data['anio']),
                    propietario_registral=v_data['propietario_registral'],
                    tipo_servicio=v_data['tipo_servicio'],
                    capacidad=int(v_data['capacidad']),
                    estado_vehiculo=v_data['estado_vehiculo']
                )
                db.session.add(new_vehiculo)
                db.session.commit()

                # Manejar revisión técnica
                placa = v_data.get('placa')
                fecha_primera = datetime.strptime(v_data['fecha_primera_revision'], '%Y-%m-%d').date() if v_data.get('fecha_primera_revision') else None
                fecha_segunda = datetime.strptime(v_data['fecha_segunda_revision'], '%Y-%m-%d').date() if v_data.get('fecha_segunda_revision') else None
                new_revision = RevisionTecnica(
                    vehiculo_id=new_vehiculo.id,
                    placa=placa,
                    fecha_primera_revision=fecha_primera,
                    fecha_segunda_revision=fecha_segunda
                )
                db.session.add(new_revision)
                
                # Manejar póliza
                cobertura_desde = v_data.get('cobertura_desde')
                cobertura_hasta = v_data.get('cobertura_hasta')
                fecha_limite_pago = v_data.get('fecha_limite_pago')

                # CORRECCIÓN: Solo crea la póliza si los campos no están vacíos
                if cobertura_desde and cobertura_hasta and fecha_limite_pago:
                    cobertura_desde = datetime.strptime(cobertura_desde, '%Y-%m-%d').date()
                    cobertura_hasta = datetime.strptime(cobertura_hasta, '%Y-%m-%d').date()
                    fecha_limite_pago = datetime.strptime(fecha_limite_pago, '%Y-%m-%d').date()
                    new_poliza = Poliza(
                        vehiculo_id=new_vehiculo.id,
                        numero_poliza=v_data['numero_poliza'],
                        cobertura_desde=cobertura_desde,
                        cobertura_hasta=cobertura_hasta,
                        fecha_limite_pago=fecha_limite_pago
                    )
                    db.session.add(new_poliza)
                
                db.session.commit()

                # Manejar fotos del vehículo
                if f'vehiculo_fotos_{v_data["temp_id"]}' in request.files:
                    fotos = request.files.getlist(f'vehiculo_fotos_{v_data["temp_id"]}')
                    if len(fotos) > 5:
                        flash('Solo puedes subir un máximo de 5 fotos por vehículo.', 'danger')
                        db.session.rollback()
                        return redirect(url_for('colaboradores.crear_colaborador'))

                    for foto in fotos:
                        if foto and foto.filename != '':
                            filename = secure_filename(foto.filename)
                            ext = filename.rsplit('.', 1)[1].lower()
                            if ext not in ['jpg', 'png', 'jpeg']:
                                flash('Formato de imagen de vehículo no permitido.', 'danger')
                                db.session.rollback()
                                return redirect(url_for('colaboradores.crear_colaborador'))
                            unique_filename = f"{uuid.uuid4()}.{ext}"
                            foto_path = os.path.join(current_app.config['UPLOAD_FILES_FOLDER'], unique_filename)
                            # Se guarda la imagen en la carpeta 'uploads/vehiculos'
                            foto.save(foto_path.replace('uploads/colaboradores', 'uploads/vehiculos')) 
                            new_foto = FotografiaVehiculo(
                                vehiculo_id=new_vehiculo.id,
                                url_foto=f'uploads/vehiculos/{unique_filename}'
                            )
                            db.session.add(new_foto)
                            db.session.commit()

            flash('Colaborador y vehículo(s) creados exitosamente!', 'success')
            return redirect(url_for('colaboradores.ver_colaboradores'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al crear colaborador: {e}")
            flash(f'Error al crear el colaborador: {e}', 'danger')
            return redirect(url_for('colaboradores.crear_colaborador'))

    return render_template('crear_colaborador.html')

@colaboradores_bp.route('/colaboradores/editar/<int:id>', methods=['GET', 'POST'])
@role_required(['Superuser', 'Administrador'])
def editar_colaborador(id):
    colaborador = Colaborador.query.get_or_404(id)
    if request.method == 'POST':
        try:
            # Lógica de edición
            colaborador.nombre = request.form['nombre']
            colaborador.primer_apellido = request.form['primer_apellido']
            colaborador.segundo_apellido = request.form.get('segundo_apellido')
            colaborador.cedula = request.form['cedula']
            colaborador.email = request.form['email']
            colaborador.telefono = request.form['telefono']
            colaborador.movil = request.form.get('movil')

            # Manejo de la foto del colaborador
            if 'foto_perfil' in request.files and request.files['foto_perfil'].filename != '':
                foto_perfil = request.files['foto_perfil']
                filename = secure_filename(foto_perfil.filename)
                ext = filename.rsplit('.', 1)[1].lower()
                if ext not in ['jpg', 'png', 'jpeg']:
                    flash('Formato de imagen de perfil no permitido.', 'danger')
                    return redirect(url_for('colaboradores.editar_colaborador', id=id))
                unique_filename = f"{uuid.uuid4()}.{ext}"
                foto_perfil_path = os.path.join(current_app.config['UPLOAD_FILES_FOLDER'], unique_filename)
                foto_perfil.save(foto_perfil_path)
                colaborador.foto_perfil = f'uploads/colaboradores/{unique_filename}'

            # Eliminar vehículos antiguos
            db.session.query(Vehiculo).filter_by(colaborador_id=colaborador.id).delete()
            db.session.commit()

            # Manejar los datos del vehículo
            vehiculos_data = json.loads(request.form.get('vehiculos_data', '[]'))
            for v_data in vehiculos_data:
                # Validar campos numéricos del vehículo
                if 'capacidad' in v_data and not str(v_data['capacidad']).isdigit():
                    flash('El campo capacidad del vehículo solo debe contener números.', 'danger')
                    db.session.rollback()
                    return redirect(url_for('colaboradores.editar_colaborador', id=id))
                
                new_vehiculo = Vehiculo(
                    colaborador_id=colaborador.id,
                    marca=v_data['marca'],
                    modelo=v_data['modelo'],
                    tipo_combustible=v_data['tipo_combustible'],
                    anio=int(v_data['anio']),
                    propietario_registral=v_data['propietario_registral'],
                    tipo_servicio=v_data['tipo_servicio'],
                    capacidad=int(v_data['capacidad']),
                    estado_vehiculo=v_data['estado_vehiculo']
                )
                db.session.add(new_vehiculo)
                db.session.commit()

                # Manejar revisión técnica
                placa = v_data.get('placa')
                fecha_primera = datetime.strptime(v_data['fecha_primera_revision'], '%Y-%m-%d').date() if v_data.get('fecha_primera_revision') else None
                fecha_segunda = datetime.strptime(v_data['fecha_segunda_revision'], '%Y-%m-%d').date() if v_data.get('fecha_segunda_revision') else None
                new_revision = RevisionTecnica(
                    vehiculo_id=new_vehiculo.id,
                    placa=placa,
                    fecha_primera_revision=fecha_primera,
                    fecha_segunda_revision=fecha_segunda
                )
                db.session.add(new_revision)
                
                # Manejar póliza
                cobertura_desde = v_data.get('cobertura_desde')
                cobertura_hasta = v_data.get('cobertura_hasta')
                fecha_limite_pago = v_data.get('fecha_limite_pago')

                # CORRECCIÓN: Solo crea la póliza si los campos no están vacíos
                if cobertura_desde and cobertura_hasta and fecha_limite_pago:
                    cobertura_desde = datetime.strptime(cobertura_desde, '%Y-%m-%d').date()
                    cobertura_hasta = datetime.strptime(cobertura_hasta, '%Y-%m-%d').date()
                    fecha_limite_pago = datetime.strptime(fecha_limite_pago, '%Y-%m-%d').date()
                    new_poliza = Poliza(
                        vehiculo_id=new_vehiculo.id,
                        numero_poliza=v_data['numero_poliza'],
                        cobertura_desde=cobertura_desde,
                        cobertura_hasta=cobertura_hasta,
                        fecha_limite_pago=fecha_limite_pago
                    )
                    db.session.add(new_poliza)
                
                db.session.commit()

                # Manejar fotos del vehículo
                if f'vehiculo_fotos_{v_data["temp_id"]}' in request.files:
                    fotos = request.files.getlist(f'vehiculo_fotos_{v_data["temp_id"]}')
                    if len(fotos) > 5:
                        flash('Solo puedes subir un máximo de 5 fotos por vehículo.', 'danger')
                        db.session.rollback()
                        return redirect(url_for('colaboradores.editar_colaborador', id=id))

                    for foto in fotos:
                        if foto and foto.filename != '':
                            filename = secure_filename(foto.filename)
                            ext = filename.rsplit('.', 1)[1].lower()
                            if ext not in ['jpg', 'png', 'jpeg']:
                                flash('Formato de imagen de vehículo no permitido.', 'danger')
                                db.session.rollback()
                                return redirect(url_for('colaboradores.editar_colaborador', id=id))
                            unique_filename = f"{uuid.uuid4()}.{ext}"
                            foto_path = os.path.join(current_app.config['UPLOAD_FILES_FOLDER'], unique_filename)
                            # Se guarda la imagen en la carpeta 'uploads/vehiculos'
                            foto.save(foto_path.replace('uploads/colaboradores', 'uploads/vehiculos'))
                            new_foto = FotografiaVehiculo(
                                vehiculo_id=new_vehiculo.id,
                                url_foto=f'uploads/vehiculos/{unique_filename}'
                            )
                            db.session.add(new_foto)
                            db.session.commit()

            db.session.commit()
            flash('Colaborador actualizado exitosamente!', 'success')
            return redirect(url_for('colaboradores.ver_colaboradores'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error al editar colaborador: {e}")
            flash(f'Error al editar el colaborador: {e}', 'danger')
            return redirect(url_for('colaboradores.editar_colaborador', id=id))

    return render_template('editar_colaborador.html', colaborador=colaborador)

@colaboradores_bp.route('/colaboradores/eliminar/<int:id>', methods=['POST'])
@role_required(['Superuser'])
def eliminar_colaborador(id):
    colaborador = Colaborador.query.get_or_404(id)
    try:
        db.session.delete(colaborador)
        db.session.commit()
        flash('Colaborador eliminado exitosamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar el colaborador: {e}', 'danger')
    return redirect(url_for('colaboradores.ver_colaboradores'))

@colaboradores_bp.route('/colaboradores/ver')
def ver_colaboradores():
    colaboradores = Colaborador.query.all()
    # Pasa el rol de sesión a la plantilla para controlar la visibilidad de los botones
    return render_template('ver_colaborador.html', colaboradores=colaboradores, user_role=session.get('role'))

@colaboradores_bp.route('/colaboradores/detalle/<int:id>')
def detalle_colaborador(id):
    colaborador = Colaborador.query.get_or_404(id)
    return render_template('detalle_colaborador.html', colaborador=colaborador, user_role=session.get('role'))

@colaboradores_bp.route('/uploads/colaboradores/<filename>')
@colaboradores_bp.route('/uploads/vehiculos/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FILES_FOLDER'], filename)

# Rutas de exportación
@colaboradores_bp.route('/colaboradores/exportar/<int:id>/<format>')
def exportar_colaborador(id, format):
    colaborador = Colaborador.query.get_or_404(id)
    if format == 'pdf':
        try:
            # Crear archivo PDF temporal
            temp_dir = tempfile.mkdtemp()
            pdf_path = os.path.join(temp_dir, f'colaborador_{colaborador.id}.pdf')
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter
            
            # Título
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, f"Detalles del Colaborador: {colaborador.nombre} {colaborador.primer_apellido}")
            
            # Información del colaborador
            c.setFont("Helvetica", 12)
            y = height - 80
            c.drawString(50, y, f"Cédula: {colaborador.cedula}")
            y -= 20
            c.drawString(50, y, f"Email: {colaborador.email if colaborador.email else 'N/A'}")
            y -= 20
            c.drawString(50, y, f"Teléfono: {colaborador.telefono}")
            y -= 20
            c.drawString(50, y, f"Móvil: {colaborador.movil if colaborador.movil else 'N/A'}")
            y -= 40

            # Información de vehículos
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y, "Vehículos:")
            y -= 20
            
            for vehiculo in colaborador.vehiculos:
                c.setFont("Helvetica", 12)
                c.drawString(70, y, f"Marca: {vehiculo.marca}")
                y -= 20
                c.drawString(70, y, f"Modelo: {vehiculo.modelo}")
                y -= 20
                c.drawString(70, y, f"Capacidad: {vehiculo.capacidad}")
                y -= 20
                c.drawString(70, y, f"Año: {vehiculo.anio}")
                y -= 20
                c.drawString(70, y, f"Tipo de Servicio: {vehiculo.tipo_servicio}")
                y -= 20
                
                if vehiculo.revisiones_tecnicas:
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(90, y, "Revisión Técnica:")
                    y -= 20
                    for revision in vehiculo.revisiones_tecnicas:
                        c.setFont("Helvetica", 10)
                        c.drawString(110, y, f"Placa: {revision.placa}")
                        y -= 15
                        c.drawString(110, y, f"Primera Revisión: {revision.fecha_primera_revision}")
                        y -= 15
                        c.drawString(110, y, f"Segunda Revisión: {revision.fecha_segunda_revision if revision.fecha_segunda_revision else 'N/A'}")
                        y -= 20
                
                if vehiculo.polizas:
                    c.setFont("Helvetica-Bold", 12)
                    c.drawString(90, y, "Póliza:")
                    y -= 20
                    for poliza in vehiculo.polizas:
                        c.setFont("Helvetica", 10)
                        c.drawString(110, y, f"Número: {poliza.numero_poliza}")
                        y -= 15
                        c.drawString(110, y, f"Cobertura: {poliza.cobertura_desde} a {poliza.cobertura_hasta}")
                        y -= 15
                        c.drawString(110, y, f"Fecha Límite de Pago: {poliza.fecha_limite_pago}")
                        y -= 20
                
                y -= 20
            
            c.save()
            return send_from_directory(temp_dir, f'colaborador_{colaborador.id}.pdf', as_attachment=True)
            
        except Exception as e:
            current_app.logger.error(f"Error al exportar a PDF: {e}")
            flash(f'Error al exportar a PDF: {e}', 'danger')
            return redirect(url_for('colaboradores.detalle_colaborador', id=id))
    
    elif format == 'txt':
        try:
            temp_dir = tempfile.mkdtemp()
            txt_path = os.path.join(temp_dir, f'colaborador_{colaborador.id}.txt')
            with open(txt_path, 'w') as f:
                f.write(f"Detalles del Colaborador: {colaborador.nombre} {colaborador.primer_apellido}\n")
                f.write("----------------------------------------\n")
                f.write(f"Cédula: {colaborador.cedula}\n")
                f.write(f"Email: {colaborador.email if colaborador.email else 'N/A'}\n")
                f.write(f"Teléfono: {colaborador.telefono}\n")
                f.write(f"Móvil: {colaborador.movil if colaborador.movil else 'N/A'}\n\n")
                
                f.write("Vehículos:\n")
                for vehiculo in colaborador.vehiculos:
                    f.write(f"  - Marca: {vehiculo.marca}\n")
                    f.write(f"  - Modelo: {vehiculo.modelo}\n")
                    f.write(f"  - Capacidad: {vehiculo.capacidad}\n")
                    f.write(f"  - Año: {vehiculo.anio}\n")
                    f.write(f"  - Tipo de Servicio: {vehiculo.tipo_servicio}\n")
                    
                    if vehiculo.revisiones_tecnicas:
                        f.write("    Revisión Técnica:\n")
                        for revision in vehiculo.revisiones_tecnicas:
                            f.write(f"      Placa: {revision.placa}\n")
                            f.write(f"      Primera Revisión: {revision.fecha_primera_revision}\n")
                            f.write(f"      Segunda Revisión: {revision.fecha_segunda_revision if revision.fecha_segunda_revision else 'N/A'}\n")
                    
                    if vehiculo.polizas:
                        f.write("    Póliza:\n")
                        for poliza in vehiculo.polizas:
                            f.write(f"      Número: {poliza.numero_poliza}\n")
                            f.write(f"      Cobertura: {poliza.cobertura_desde} a {poliza.cobertura_hasta}\n")
                            f.write(f"      Fecha Límite de Pago: {poliza.fecha_limite_pago}\n")
                    f.write("\n")
            
            return send_from_directory(temp_dir, f'colaborador_{colaborador.id}.txt', as_attachment=True)
            
        except Exception as e:
            current_app.logger.error(f"Error al exportar a TXT: {e}")
            flash(f'Error al exportar a TXT: {e}', 'danger')
            return redirect(url_for('colaboradores.detalle_colaborador', id=id))

    elif format == 'jpg' or format == 'png':
        try:
            # Generar una imagen de la tarjeta de perfil
            from PIL import Image, ImageDraw, ImageFont
            
            # Creación de una imagen básica, esto es una simplificación
            img = Image.new('RGB', (800, 600), color = 'white')
            d = ImageDraw.Draw(img)
            
            try:
                # Intenta cargar una fuente
                font_path = "arial.ttf" # Requiere una fuente .ttf en la misma carpeta o accesible
                fnt_bold = ImageFont.truetype(font_path, 24)
                fnt_normal = ImageFont.truetype(font_path, 16)
            except IOError:
                # Usa la fuente por defecto si no se encuentra
                fnt_bold = ImageFont.load_default()
                fnt_normal = ImageFont.load_default()
            
            y_offset = 50
            d.text((50, y_offset), f"Detalles del Colaborador: {colaborador.nombre} {colaborador.primer_apellido}", font=fnt_bold, fill=(0, 0, 0))
            y_offset += 50
            d.text((50, y_offset), f"Cédula: {colaborador.cedula}", font=fnt_normal, fill=(0, 0, 0))
            y_offset += 25
            d.text((50, y_offset), f"Teléfono: {colaborador.telefono}", font=fnt_normal, fill=(0, 0, 0))
            
            temp_dir = tempfile.mkdtemp()
            img_path = os.path.join(temp_dir, f'colaborador_{colaborador.id}.{format}')
            img.save(img_path)
            
            return send_from_directory(temp_dir, f'colaborador_{colaborador.id}.{format}', as_attachment=True)
            
        except Exception as e:
            current_app.logger.error(f"Error al exportar a imagen: {e}")
            flash(f'Error al exportar a {format}: {e}', 'danger')
            return redirect(url_for('colaboradores.detalle_colaborador', id=id))

    elif format == 'xls':
        try:
            data = []
            for vehiculo in colaborador.vehiculos:
                row = {
                    "Nombre Colaborador": f"{colaborador.nombre} {colaborador.primer_apellido}",
                    "Cédula": colaborador.cedula,
                    "Email": colaborador.email,
                    "Teléfono": colaborador.telefono,
                    "Móvil": colaborador.movil,
                    "Marca Vehículo": vehiculo.marca,
                    "Modelo Vehículo": vehiculo.modelo,
                    "Tipo Combustible": vehiculo.tipo_combustible,
                    "Año": vehiculo.anio,
                    "Capacidad": vehiculo.capacidad,
                    "Estado Vehículo": vehiculo.estado_vehiculo,
                    "Placa": vehiculo.revisiones_tecnicas[0].placa if vehiculo.revisiones_tecnicas else "N/A",
                    "Número Póliza": vehiculo.polizas[0].numero_poliza if vehiculo.polizas else "N/A",
                }
                data.append(row)
            
            if not data:
                # Si no hay vehículos, crea una fila con solo los datos del colaborador
                data.append({
                    "Nombre Colaborador": f"{colaborador.nombre} {colaborador.primer_apellido}",
                    "Cédula": colaborador.cedula,
                    "Email": colaborador.email,
                    "Teléfono": colaborador.telefono,
                    "Móvil": colaborador.movil,
                    "Marca Vehículo": "N/A",
                    "Modelo Vehículo": "N/A",
                    "Tipo Combustible": "N/A",
                    "Año": "N/A",
                    "Capacidad": "N/A",
                    "Estado Vehículo": "N/A",
                    "Placa": "N/A",
                    "Número Póliza": "N/A",
                })
                
            df = pd.DataFrame(data)
            
            temp_dir = tempfile.mkdtemp()
            xls_path = os.path.join(temp_dir, f'colaborador_{colaborador.id}.xlsx')
            df.to_excel(xls_path, index=False)
            
            return send_from_directory(temp_dir, f'colaborador_{colaborador.id}.xlsx', as_attachment=True)
        
        except Exception as e:
            current_app.logger.error(f"Error al exportar a XLS: {e}")
            flash(f'Error al exportar a XLS: {e}', 'danger')
            return redirect(url_for('colaboradores.detalle_colaborador', id=id))

    else:
        flash('Formato de exportación no válido.', 'danger')
        return redirect(url_for('colaboradores.detalle_colaborador', id=id))
