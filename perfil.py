from flask import Blueprint, render_template, request, flash, redirect, url_for, session, current_app, send_from_directory
from models import db, bcrypt, User
from functools import wraps
import os
import shutil
from werkzeug.utils import secure_filename
from datetime import datetime
import uuid # Importar para nombres de archivo únicos

perfil_bp = Blueprint('perfil', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('Por favor, inicia sesión para acceder a esta página.', 'info')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- RUTA PRINCIPAL DEL PERFIL (SOLO MUESTRA INFORMACIÓN) ---
@perfil_bp.route('/')
@login_required
def perfil():
    user = User.query.get_or_404(session['user_id'])
    return render_template('perfil.html', user=user)

# --- NUEVA RUTA DEDICADA PARA EDITAR EL PERFIL ---
@perfil_bp.route('/editar', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    user = User.query.get_or_404(session['user_id'])
    
    # Opciones para los <select> del formulario
    provincia_opciones = ["Cartago", "Limón", "Puntarenas", "San José", "Heredia", "Guanacaste", "Alajuela"]
    tipo_sangre_opciones = ["Seleccionar Tipo", "A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

    if request.method == 'POST':
        # --- Lógica para actualizar el perfil ---
        # Validar unicidad de username y email si cambian
        new_username = request.form.get('username')
        new_email = request.form.get('email')

        if new_username != user.username and User.query.filter_by(username=new_username).first():
            flash('Ese nombre de usuario ya está en uso. Por favor, elige otro.', 'danger')
        elif new_email and new_email != user.email and User.query.filter_by(email=new_email).first():
            flash('Ese correo electrónico ya está registrado. Por favor, usa otro.', 'danger')
        else:
            user.username = new_username
            user.email = new_email
            user.nombre = request.form.get('nombre')
            user.primer_apellido = request.form.get('primer_apellido')
            user.segundo_apellido = request.form.get('segundo_apellido')
            user.telefono = request.form.get('telefono')
            user.cedula = request.form.get('cedula')
            user.direccion = request.form.get('direccion')
            user.nombre_emergencia = request.form.get('nombre_emergencia')
            user.telefono_emergencia = request.form.get('telefono_emergencia')
            user.tipo_sangre = request.form.get('tipo_sangre')
            user.empresa = request.form.get('empresa')
            user.poliza = request.form.get('poliza')
            user.aseguradora = request.form.get('aseguradora')
            user.alergias = request.form.get('alergias')
            user.enfermedades_cronicas = request.form.get('enfermedades_cronicas')

            fecha_cumpleanos_str = request.form.get('fecha_cumpleanos')
            if fecha_cumpleanos_str:
                user.fecha_cumpleanos = datetime.strptime(fecha_cumpleanos_str, '%Y-%m-%d').date()
            else:
                user.fecha_cumpleanos = None

            # Lógica para actualizar el avatar
            if 'avatar' in request.files:
                avatar_file = request.files['avatar']
                if avatar_file.filename != '':
                    filename = secure_filename(avatar_file.filename)
                    unique_filename = str(uuid.uuid4()) + os.path.splitext(filename)[1]
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    file_path = os.path.join(upload_folder, unique_filename)
                    avatar_file.save(file_path)
                    user.avatar_url = os.path.join('uploads', 'avatars', unique_filename).replace('\\', '/')

            db.session.commit()
            flash('¡Perfil actualizado con éxito!', 'success')
            return redirect(url_for('perfil.perfil'))

    return render_template('editar_perfil.html', 
                           user=user, 
                           provincia_opciones=provincia_opciones, 
                           tipo_sangre_opciones=tipo_sangre_opciones)


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
        elif new_password != confirm_password:
            flash('Las nuevas contraseñas no coinciden.', 'danger')
        else:
            hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            user.password = hashed_password
            db.session.commit()
            flash('Contraseña actualizada con éxito.', 'success')
            return redirect(url_for('perfil.perfil'))
    return render_template('change_password.html')

# (El resto de tus rutas como backup_database, etc. pueden permanecer aquí sin cambios)

