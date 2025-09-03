from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app, send_from_directory
from models import db, bcrypt, User, SiteStats # Se eliminó la importación de 'Poliza'
from functools import wraps
import os
import shutil
from werkzeug.utils import secure_filename
from datetime import datetime

perfil_bp = Blueprint('perfil', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(roles):
    if not isinstance(roles, list):
        roles = [roles]
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'logged_in' not in session or not session.get('logged_in'):
                flash('Por favor, inicia sesión para acceder a esta página.', 'info')
                return redirect(url_for('login'))
            user_role = session.get('role')
            if user_role not in roles:
                flash('No tienes permiso para acceder a esta página.', 'danger')
                return redirect(url_for('home'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@perfil_bp.route('/')
@login_required
def perfil():
    user = User.query.get(session['user_id'])
    stats = None
    if user and user.role == 'Superuser':
        total_users = User.query.count()
        # Se eliminó la línea que contaba las pólizas
        stats = {
            'total_users': total_users,
            # Se eliminó la estadística de pólizas de aquí
        }
    return render_template('perfil.html', user=user, stats=stats)

@perfil_bp.route('/editar', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    user = User.query.get(session['user_id'])
    # Opciones para los campos de selección
    provincia_opciones = ["Cartago", "Limón", "Puntarenas", "San José", "Heredia", "Guanacaste", "Alajuela"]
    tipo_sangre_opciones = ["Seleccionar Tipo", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]
    
    if request.method == 'POST':
        # Actualizar campos
        user.nombre = request.form['nombre']
        user.primer_apellido = request.form['primer_apellido']
        user.segundo_apellido = request.form.get('segundo_apellido')
        user.telefono = request.form['telefono']
        user.email = request.form.get('email')
        user.telefono_emergencia = request.form.get('telefono_emergencia')
        user.nombre_emergencia = request.form.get('nombre_emergencia')
        user.direccion = request.form.get('direccion')
        
        db.session.commit()
        flash('Perfil actualizado con éxito.', 'success')
        return redirect(url_for('perfil.perfil'))
        
    return render_template('editar_perfil.html', user=user, provincia_opciones=provincia_opciones, tipo_sangre_opciones=tipo_sangre_opciones)

@perfil_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        user = User.query.get(session['user_id'])

        if not bcrypt.check_password_hash(user.password, current_password):
            flash('La contraseña actual es incorrecta.', 'danger')
            return redirect(url_for('perfil.change_password'))

        if new_password != confirm_password:
            flash('Las nuevas contraseñas no coinciden.', 'danger')
            return redirect(url_for('perfil.change_password'))

        hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
        user.password = hashed_password
        db.session.commit()

        flash('Contraseña actualizada con éxito.', 'success')
        return redirect(url_for('perfil.perfil'))

    return render_template('change_password.html')

@perfil_bp.route('/backup_database', methods=['POST'])
@login_required
@role_required('Superuser')
def backup_database():
    try:
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        backup_folder = os.path.join(current_app.instance_path, 'backups')
        os.makedirs(backup_folder, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_{timestamp}.db"
        backup_path = os.path.join(backup_folder, backup_filename)
        
        shutil.copy2(db_path, backup_path)
        
        flash(f'Backup de la base de datos creado exitosamente en: {backup_path}', 'success')
        return send_from_directory(directory=backup_folder, path=backup_filename, as_attachment=True)
    except Exception as e:
        flash(f'Error al crear el backup: {e}', 'danger')
        return redirect(url_for('perfil.perfil'))

@perfil_bp.route('/upload_database', methods=['POST'])
@login_required
@role_required('Superuser')
def upload_database():
    if 'db_file' not in request.files:
        flash('No se encontró el archivo.', 'danger')
        return redirect(url_for('perfil.perfil'))
    
    file = request.files['db_file']
    if file.filename == '' or not file.filename.endswith('.db'):
        flash('Archivo no válido. Por favor, sube un archivo .db.', 'danger')
        return redirect(url_for('perfil.perfil'))
        
    try:
        db_path = current_app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        filename = secure_filename(file.filename)
        upload_path = os.path.join(current_app.instance_path, filename)
        file.save(upload_path)
        
        # Cierra la conexión actual a la BD antes de reemplazar el archivo
        db.session.remove()
        db.engine.dispose()
        
        os.remove(db_path)
        shutil.move(upload_path, db_path)
        
        flash('Base de datos reemplazada. La aplicación se reiniciará.', 'success')
        # Forzar el reinicio del servidor (esto puede variar dependiendo del entorno de producción)
        os._exit(0)
        
    except Exception as e:
        flash(f'Error al subir la base de datos: {e}', 'danger')
        return redirect(url_for('perfil.perfil'))

