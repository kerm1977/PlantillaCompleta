from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app, session
import json
import os

# Define the blueprint
btns_bp = Blueprint('btns', __name__)

# --- Configuration File Handling ---

def get_config_path():
    """Constructs the absolute path to the configuration file."""
    # Creates the path inside the 'instance' folder, e.g., /path/to/your/app/instance/btns_config.json
    return os.path.join(current_app.instance_path, 'btns_config.json')

def load_config():
    """
    Loads the button configuration from the JSON file.
    Returns a default configuration if the file doesn't exist or is invalid.
    """
    config_path = get_config_path()
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Default structure if file is missing or corrupt
        return {
            'button_one': {'is_visible': False, 'link': '', 'icon': 'fa-link', 'visibility_state': 'all'},
            'button_two': {'is_visible': False, 'link': '', 'icon': 'fa-file-pdf', 'visibility_state': 'all'}
        }

def save_config(config):
    """
    Saves the button configuration to the JSON file.
    Returns True on success, False on failure.
    """
    config_path = get_config_path()
    try:
        # Ensure the instance folder exists before trying to write to it
        os.makedirs(current_app.instance_path, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except IOError as e:
        current_app.logger.error(f"Error writing to config file {config_path}: {e}")
        return False

# --- Helper Functions ---

def process_link(link_text):
    """
    Strips whitespace and adds 'https://' if no protocol is present.
    Ignores internal links (starting with '/') or anchor links (starting with '#').
    """
    processed_link = link_text.strip()
    if processed_link and not processed_link.startswith(('http://', 'https://', '/', '#')):
        processed_link = 'https://' + processed_link
    return processed_link

# --- Routes ---

@btns_bp.route('/btns/crear', methods=['GET', 'POST'])
# @role_required('Superuser') # This should be uncommented if you have a role decorator
def crear_btns():
    """
    Handles the creation and updating of the dynamic floating buttons.
    """
    if request.method == 'POST':
        # --- Collect and process form data ---
        form_data = {
            'button_one': {
                'is_visible': 'is_visible_one' in request.form,
                'link': process_link(request.form.get('link_one', '')),
                'icon': request.form.get('icon_one', 'fa-link').strip() or 'fa-link',
                'visibility_state': request.form.get('visibility_state_one', 'all')
            },
            'button_two': {
                'is_visible': 'is_visible_two' in request.form,
                'link': process_link(request.form.get('link_two', '')),
                'icon': request.form.get('icon_two', 'fa-file-pdf').strip() or 'fa-file-pdf',
                'visibility_state': request.form.get('visibility_state_two', 'all')
            }
        }

        # --- Server-side Validation ---
        has_errors = False
        if form_data['button_one']['is_visible'] and not form_data['button_one']['link']:
            flash('No se puede activar el Botón 1 sin proporcionar una URL.', 'danger')
            has_errors = True

        if form_data['button_two']['is_visible'] and not form_data['button_two']['link']:
            flash('No se puede activar el Botón 2 sin proporcionar una URL.', 'danger')
            has_errors = True

        if has_errors:
            # If validation fails, re-render the template with the submitted data so user doesn't lose their input
            return render_template('crear_btns.html', config=form_data)

        # --- Save configuration and redirect ---
        if save_config(form_data):
            flash('Configuración de botones guardada exitosamente.', 'success')
        else:
            flash('Error al guardar la configuración. Revise los permisos del servidor.', 'danger')

        return redirect(url_for('btns.crear_btns'))

    # For GET requests, load and display the current configuration
    config = load_config()
    return render_template('crear_btns.html', config=config)


@btns_bp.route('/api/btns/config')
def get_btn_config():
    """API endpoint to provide button configuration to the frontend script."""
    return jsonify(load_config())


@btns_bp.route('/api/session_status')
def get_session_status():
    """
    API endpoint to check the user's session status (logged in, role).
    This helps the frontend decide whether to show buttons based on visibility rules.
    """
    return jsonify({
        'logged_in': session.get('logged_in', False),
        'is_superuser': session.get('role') == 'Superuser'
    })

