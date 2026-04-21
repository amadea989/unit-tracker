from flask import Flask, render_template, request, redirect, url_for, session, Response, flash
import psycopg2
import psycopg2.extras
import os
import csv
import io
import bcrypt
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'amadea'  # Change this in production

# Database URL - use environment variable in production
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_T02hPfBmDCnA@ep-solitary-brook-a10tx7u7-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require')

# Helper function to format price
def format_price(price_str):
    """Format price to MUR X,XXX,XXX.XX"""
    if not price_str:
        return None
    
    # Remove existing MUR, commas, and spaces
    cleaned = price_str.replace('MUR', '').replace(',', '').replace(' ', '').strip()
    
    if not cleaned:
        return None
    
    try:
        # Convert to float
        amount = float(cleaned)
        # Format with commas and 2 decimal places
        return f"MUR {amount:,.2f}"
    except:
        # If conversion fails, return original
        return price_str

# Helper function to hash passwords
def hash_password(password):
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

# Helper function to verify passwords
def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

# Helper function to log audit trail
def log_audit(user_id, action, entity_type, entity_id, entity_name, old_value=None, new_value=None):
    """Log an action to the audit trail"""
    try:
        conn = get_db()
        cur = conn.cursor()
        ip_address = request.remote_addr if request else None
        
        cur.execute('''
            INSERT INTO audit_log (user_id, action, entity_type, entity_id, entity_name, old_value, new_value, ip_address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ''', (user_id, action, entity_type, entity_id, entity_name, old_value, new_value, ip_address))
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Audit log error: {e}")

# Decorator to require login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Decorator to require admin role
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        
        if session.get('role') != 'admin':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('home'))
        
        return f(*args, **kwargs)
    return decorated_function

# Function to get database connection
def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

# Initialize database
def init_db():
    conn = get_db()
    cur = conn.cursor()
    
    # Users table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            is_active BOOLEAN DEFAULT TRUE,
            must_change_password BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            created_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS units (
            id SERIAL PRIMARY KEY,
            project_id INTEGER REFERENCES projects(id),
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            size_sqm REAL,
            bedrooms INTEGER,
            bathrooms INTEGER,
            floor_number TEXT,
            selling_price TEXT,
            buyer_name TEXT,
            buyer_phone TEXT,
            buyer_email TEXT,
            sale_price TEXT,
            notes TEXT,
            created_by INTEGER REFERENCES users(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Project details table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS project_details (
            id SERIAL PRIMARY KEY,
            project_id INTEGER REFERENCES projects(id) UNIQUE,
            location TEXT,
            total_area REAL,
            num_floors INTEGER,
            completion_date TEXT,
            construction_status TEXT,
            developer_name TEXT,
            developer_contact TEXT,
            description TEXT,
            amenities TEXT,
            building_permit_link TEXT,
            floor_plans_link TEXT,
            master_plan_link TEXT,
            certificate_link TEXT,
            marketing_materials_link TEXT,
            site_photos_link TEXT,
            timeline_notes TEXT
        )
    ''')
    
    # Audit log table
    cur.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            entity_name TEXT,
            old_value TEXT,
            new_value TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

init_db()

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    # Check if any users exist
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT COUNT(*) as count FROM users')
    user_count = cur.fetchone()['count']
    
    # If no users exist, show first admin creation form
    if user_count == 0:
        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip()
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            password = request.form.get('password', '').strip()
            confirm_password = request.form.get('confirm_password', '').strip()
            
            # Validation
            if not all([username, email, first_name, last_name, password]):
                cur.close()
                conn.close()
                return render_template('create_first_admin.html', error='All fields are required')
            
            if password != confirm_password:
                cur.close()
                conn.close()
                return render_template('create_first_admin.html', error='Passwords do not match')
            
            if len(password) < 6:
                cur.close()
                conn.close()
                return render_template('create_first_admin.html', error='Password must be at least 6 characters')
            
            # Create first admin user
            password_hash = hash_password(password)
            
            cur.execute('''
                INSERT INTO users (username, email, password_hash, first_name, last_name, role, must_change_password)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            ''', (username, email, password_hash, first_name, last_name, 'admin', False))
            
            user_id = cur.fetchone()['id']
            conn.commit()
            
            # Log the creation
            log_audit(user_id, 'create', 'user', user_id, username, None, f'First admin user created')
            
            # Auto-login
            session['user_id'] = user_id
            session['username'] = username
            session['role'] = 'admin'
            session['full_name'] = f"{first_name} {last_name}"
            
            cur.close()
            conn.close()
            
            flash(f'Welcome {first_name}! You are now the first administrator.', 'success')
            return redirect(url_for('home'))
        
        cur.close()
        conn.close()
        return render_template('create_first_admin.html')
    
    # Normal login for existing users
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        
        if not username or not password:
            cur.close()
            conn.close()
            return render_template('login.html', error='Username and password are required')
        
        # Find user
        cur.execute('SELECT * FROM users WHERE username = %s AND is_active = TRUE', (username,))
        user = cur.fetchone()
        
        if not user:
            cur.close()
            conn.close()
            return render_template('login.html', error='Invalid username or password')
        
        # Verify password
        if not verify_password(password, user['password_hash']):
            cur.close()
            conn.close()
            return render_template('login.html', error='Invalid username or password')
        
        # Set session
        session['user_id'] = user['id']
        session['username'] = user['username']
        session['role'] = user['role']
        session['full_name'] = f"{user['first_name']} {user['last_name']}"
        session['must_change_password'] = user['must_change_password']
        
        # Log the login
        log_audit(user['id'], 'login', 'user', user['id'], username, None, 'User logged in')
        
        cur.close()
        conn.close()
        
        # Check if password change required
        if user['must_change_password']:
            flash('You must change your password before continuing.', 'error')
            return redirect(url_for('change_password'))
        
        flash(f'Welcome back, {user["first_name"]}!', 'success')
        return redirect(url_for('home'))
    
    cur.close()
    conn.close()
    return render_template('login.html')

# Logout route
@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    username = session.get('username')
    
    if user_id:
        log_audit(user_id, 'logout', 'user', user_id, username, None, 'User logged out')
    
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))

# Check if user is logged in
@app.before_request
def require_login():
    allowed_routes = ['login', 'static']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))

@app.route('/')
def home():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get all projects
    cur.execute('SELECT * FROM projects')
    projects_data = cur.fetchall()
    
    # Build projects list with their units
    projects = []
    for project in projects_data:
        cur.execute('SELECT * FROM units WHERE project_id = %s', (project['id'],))
        units_data = cur.fetchall()
        
        units = [{'name': u['name'], 'status': u['status'], 'id': u['id']} for u in units_data]
        
        projects.append({
            'id': project['id'],
            'name': project['name'],
            'units': units
        })
    
    cur.close()
    conn.close()
    return render_template('index.html', projects=projects)

@app.route('/project/<int:project_id>')
def project_overview(project_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get project
    cur.execute('SELECT * FROM projects WHERE id = %s', (project_id,))
    project = cur.fetchone()
    
    if not project:
        cur.close()
        conn.close()
        return redirect(url_for('home'))
    
    # Get project details (or create if doesn't exist)
    cur.execute('SELECT * FROM project_details WHERE project_id = %s', (project_id,))
    details = cur.fetchone()
    
    if not details:
        # Create empty details record
        cur.execute('INSERT INTO project_details (project_id) VALUES (%s)', (project_id,))
        conn.commit()
        cur.execute('SELECT * FROM project_details WHERE project_id = %s', (project_id,))
        details = cur.fetchone()
    
    # Get all units for this project
    cur.execute('SELECT * FROM units WHERE project_id = %s ORDER BY name', (project_id,))
    units = cur.fetchall()
    
    # Calculate statistics
    total_units = len(units)
    available = sum(1 for u in units if u['status'] == 'Available')
    viewing = sum(1 for u in units if u['status'] == 'Viewing')
    reserved = sum(1 for u in units if u['status'] == 'Reserved')
    sold = sum(1 for u in units if u['status'] == 'Sold')
    
    # Calculate financial summary
    total_value = 0
    sold_value = 0
    
    for unit in units:
        if unit['selling_price']:
            price_str = unit['selling_price'].replace('MUR', '').replace(',', '').replace(' ', '').strip()
            try:
                price = float(price_str)
                total_value += price
                if unit['status'] == 'Sold' and unit['sale_price']:
                    sale_str = unit['sale_price'].replace('MUR', '').replace(',', '').replace(' ', '').strip()
                    sold_value += float(sale_str)
            except:
                pass
    
    avg_price = total_value / total_units if total_units > 0 else 0
    revenue_percentage = (sold_value / total_value * 100) if total_value > 0 else 0
    
    stats = {
        'total_units': total_units,
        'available': available,
        'viewing': viewing,
        'reserved': reserved,
        'sold': sold,
        'total_value': total_value,
        'sold_value': sold_value,
        'avg_price': avg_price,
        'revenue_percentage': revenue_percentage
    }
    
    cur.close()
    conn.close()
    
    return render_template('project_overview.html', project=project, details=details, units=units, stats=stats)

@app.route('/dashboard')
def dashboard():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get total counts
    cur.execute('SELECT COUNT(*) as count FROM projects')
    total_projects = cur.fetchone()['count']
    
    cur.execute('SELECT COUNT(*) as count FROM units')
    total_units = cur.fetchone()['count']
    
    # Get units by status
    cur.execute('SELECT COUNT(*) as count FROM units WHERE status = %s', ('Available',))
    available = cur.fetchone()['count']
    
    cur.execute('SELECT COUNT(*) as count FROM units WHERE status = %s', ('Viewing',))
    viewing = cur.fetchone()['count']
    
    cur.execute('SELECT COUNT(*) as count FROM units WHERE status = %s', ('Reserved',))
    reserved = cur.fetchone()['count']
    
    cur.execute('SELECT COUNT(*) as count FROM units WHERE status = %s', ('Sold',))
    sold = cur.fetchone()['count']
    
    # Calculate total revenue
    cur.execute('SELECT sale_price FROM units WHERE status = %s AND sale_price IS NOT NULL', ('Sold',))
    revenue_data = cur.fetchall()
    
    total_revenue = 0
    for row in revenue_data:
        if row['sale_price']:
            price_str = row['sale_price'].replace('MUR', '').replace(',', '').replace(' ', '').strip()
            try:
                total_revenue += float(price_str)
            except:
                pass
    
    cur.close()
    conn.close()
    
    stats = {
        'total_projects': total_projects,
        'total_units': total_units,
        'available': available,
        'viewing': viewing,
        'reserved': reserved,
        'sold': sold,
        'total_revenue': total_revenue
    }
    
    return render_template('dashboard.html', stats=stats)

@app.route('/update_project_name/<int:project_id>', methods=['POST'])
def update_project_name(project_id):
    new_name = request.form.get('project_name', '').strip()
    
    if not new_name:
        flash('Project name cannot be empty.', 'error')
        return redirect(url_for('project_overview', project_id=project_id))
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE projects SET name = %s WHERE id = %s', (new_name, project_id))
    conn.commit()
    cur.close()
    conn.close()
    
    flash('Project name updated successfully!', 'success')
    return redirect(url_for('project_overview', project_id=project_id))

@app.route('/delete_project_full/<int:project_id>', methods=['POST'])
def delete_project_full(project_id):
    confirmation_name = request.form.get('confirmation_name', '').strip()
    
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    # Get project name
    cur.execute('SELECT name FROM projects WHERE id = %s', (project_id,))
    project = cur.fetchone()
    
    if not project:
        cur.close()
        conn.close()
        flash('Project not found.', 'error')
        return redirect(url_for('home'))
    
    # Verify confirmation name matches
    if confirmation_name != project['name']:
        cur.close()
        conn.close()
        flash('Project name does not match. Deletion cancelled.', 'error')
        return redirect(url_for('project_overview', project_id=project_id))
    
    # Delete project details first
    cur.execute('DELETE FROM project_details WHERE project_id = %s', (project_id,))
    
    # Delete all units in this project
    cur.execute('DELETE FROM units WHERE project_id = %s', (project_id,))
    
    # Delete the project
    cur.execute('DELETE FROM projects WHERE id = %s', (project_id,))
    
    conn.commit()
    cur.close()
    conn.close()
    
    flash(f'Project "{project["name"]}" and all its units have been deleted.', 'success')
    return redirect(url_for('home'))

@app.route('/update_project_details/<int:project_id>', methods=['POST'])
def update_project_details(project_id):
    location = request.form.get('location', '')
    total_area = request.form.get('total_area', None)
    num_floors = request.form.get('num_floors', None)
    completion_date = request.form.get('completion_date', '')
    construction_status = request.form.get('construction_status', '')
    developer_name = request.form.get('developer_name', '')
    developer_contact = request.form.get('developer_contact', '')
    description = request.form.get('description', '')
    amenities = request.form.get('amenities', '')
    building_permit_link = request.form.get('building_permit_link', '')
    floor_plans_link = request.form.get('floor_plans_link', '')
    master_plan_link = request.form.get('master_plan_link', '')
    certificate_link = request.form.get('certificate_link', '')
    marketing_materials_link = request.form.get('marketing_materials_link', '')
    site_photos_link = request.form.get('site_photos_link', '')
    timeline_notes = request.form.get('timeline_notes', '')
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        UPDATE project_details 
        SET location = %s, total_area = %s, num_floors = %s, completion_date = %s,
            construction_status = %s, developer_name = %s, developer_contact = %s,
            description = %s, amenities = %s, building_permit_link = %s,
            floor_plans_link = %s, master_plan_link = %s, certificate_link = %s,
            marketing_materials_link = %s, site_photos_link = %s, timeline_notes = %s
        WHERE project_id = %s
    ''', (location, total_area, num_floors, completion_date, construction_status,
          developer_name, developer_contact, description, amenities,
          building_permit_link, floor_plans_link, master_plan_link, certificate_link,
          marketing_materials_link, site_photos_link, timeline_notes, project_id))
    conn.commit()
    cur.close()
    conn.close()
    
    flash('Project details updated successfully!', 'success')
    return redirect(url_for('project_overview', project_id=project_id))

@app.route('/add_project', methods=['POST'])
def add_project():
    project_name = request.form['project_name']
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO projects (name) VALUES (%s)', (project_name,))
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for('home'))

@app.route('/add_unit/<int:project_id>', methods=['POST'])
def add_unit(project_id):
    unit_name = request.form['unit_name']
    status = request.form['status']
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('INSERT INTO units (project_id, name, status) VALUES (%s, %s, %s)', 
                (project_id, unit_name, status))
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for('home'))

@app.route('/update/<int:project_id>/<int:unit_id>', methods=['POST'])
def update_unit(project_id, unit_id):
    new_status = request.form['new_status']
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE units SET status = %s WHERE id = %s', (new_status, unit_id))
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for('home'))

@app.route('/unit/<int:unit_id>')
def unit_details(unit_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    
    cur.execute('SELECT * FROM units WHERE id = %s', (unit_id,))
    unit = cur.fetchone()
    
    cur.execute('SELECT * FROM projects WHERE id = %s', (unit['project_id'],))
    project = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return render_template('unit_details.html', unit=unit, project=project)

@app.route('/update_details/<int:unit_id>', methods=['POST'])
def update_details(unit_id):
    buyer_name = request.form.get('buyer_name', '')
    buyer_phone = request.form.get('buyer_phone', '')
    buyer_email = request.form.get('buyer_email', '')
    sale_price = request.form.get('sale_price', '')
    notes = request.form.get('notes', '')
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        UPDATE units 
        SET buyer_name = %s, buyer_phone = %s, buyer_email = %s, sale_price = %s, notes = %s
        WHERE id = %s
    ''', (buyer_name, buyer_phone, buyer_email, sale_price, notes, unit_id))
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for('unit_details', unit_id=unit_id))

@app.route('/delete_unit/<int:unit_id>', methods=['POST'])
def delete_unit(unit_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM units WHERE id = %s', (unit_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('home'))

@app.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM units WHERE project_id = %s', (project_id,))
    cur.execute('DELETE FROM projects WHERE id = %s', (project_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('home'))

@app.route('/update_status/<int:unit_id>', methods=['POST'])
def update_status(unit_id):
    new_status = request.form['new_status']
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE units SET status = %s WHERE id = %s', (new_status, unit_id))
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for('unit_details', unit_id=unit_id))

@app.route('/update_specs/<int:unit_id>', methods=['POST'])
def update_specs(unit_id):
    size_sqm = request.form.get('size_sqm', None)
    bedrooms = request.form.get('bedrooms', None)
    bathrooms = request.form.get('bathrooms', None)
    floor_number = request.form.get('floor_number', '')
    selling_price = request.form.get('selling_price', '')
    
    # Format the selling price
    if selling_price:
        selling_price = format_price(selling_price)
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        UPDATE units 
        SET size_sqm = %s, bedrooms = %s, bathrooms = %s, floor_number = %s, selling_price = %s
        WHERE id = %s
    ''', (size_sqm, bedrooms, bathrooms, floor_number, selling_price, unit_id))
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for('unit_details', unit_id=unit_id))

@app.route('/update_buyer/<int:unit_id>', methods=['POST'])
def update_buyer(unit_id):
    buyer_name = request.form.get('buyer_name', '')
    buyer_phone = request.form.get('buyer_phone', '')
    buyer_email = request.form.get('buyer_email', '')
    sale_price = request.form.get('sale_price', '')
    
    # Format the sale price
    if sale_price:
        sale_price = format_price(sale_price)
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        UPDATE units 
        SET buyer_name = %s, buyer_phone = %s, buyer_email = %s, sale_price = %s
        WHERE id = %s
    ''', (buyer_name, buyer_phone, buyer_email, sale_price, unit_id))
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for('unit_details', unit_id=unit_id))

@app.route('/update_notes/<int:unit_id>', methods=['POST'])
def update_notes(unit_id):
    notes = request.form.get('notes', '')
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE units SET notes = %s WHERE id = %s', (notes, unit_id))
    conn.commit()
    cur.close()
    conn.close()
    
    return redirect(url_for('unit_details', unit_id=unit_id))

@app.route('/download_template')
def download_template():
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(['name', 'status', 'size_sqm', 'bedrooms', 'bathrooms', 'floor_number', 'selling_price', 'notes'])
    writer.writerow(['Unit 101', 'Available', '85.5', '2', '1', 'First', 'MUR 5,000,000', 'Corner unit with sea view'])
    
    response = Response(output.getvalue(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=unit_import_template.csv'
    
    return response

@app.route('/import_csv/<int:project_id>', methods=['POST'])
def import_csv(project_id):
    if 'csv_file' not in request.files:
        flash('No file selected. Please choose a CSV file.', 'error')
        return redirect(url_for('home'))
    
    file = request.files['csv_file']
    
    if file.filename == '':
        flash('No file selected. Please choose a CSV file.', 'error')
        return redirect(url_for('home'))
    
    if not file.filename.endswith('.csv'):
        flash('Invalid file type. Please upload a CSV file.', 'error')
        return redirect(url_for('home'))
    
    try:
        raw_data = file.stream.read()
        
        try:
            text_data = raw_data.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text_data = raw_data.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    text_data = raw_data.decode('cp1252')
                except UnicodeDecodeError:
                    text_data = raw_data.decode('latin-1')
        
        stream = io.StringIO(text_data, newline=None)
        csv_reader = csv.DictReader(stream)
        
        if csv_reader.fieldnames:
            cleaned_headers = [h.strip() for h in csv_reader.fieldnames]
            csv_reader.fieldnames = cleaned_headers
        
        required_headers = ['name', 'status']
        
        if not csv_reader.fieldnames or not all(header in csv_reader.fieldnames for header in required_headers):
            flash('Invalid CSV format. Required columns: name, status. Please check the template.', 'error')
            return redirect(url_for('home'))
        
        valid_statuses = ['Available', 'Viewing', 'Reserved', 'Sold']
        
        conn = get_db()
        cur = conn.cursor()
        imported_count = 0
        
        for row in csv_reader:
            if not any(row.values()):
                continue
                
            if not row.get('name') or not row.get('name').strip():
                cur.close()
                conn.close()
                flash('CSV contains empty unit names. Please fix and try again.', 'error')
                return redirect(url_for('home'))
            
            status = row.get('status', '').strip()
            if status not in valid_statuses:
                cur.close()
                conn.close()
                flash(f'Invalid status "{status}" in CSV. Must be: Available, Viewing, Reserved, or Sold.', 'error')
                return redirect(url_for('home'))
            
            name = row.get('name', '').strip()
            size_sqm = row.get('size_sqm', '').strip() or None
            bedrooms = row.get('bedrooms', '').strip() or None
            bathrooms = row.get('bathrooms', '').strip() or None
            floor_number = row.get('floor_number', '').strip() or None
            selling_price = row.get('selling_price', '').strip() or None
            notes = row.get('notes', '').strip() or None
            
            # Format selling price if present
            if selling_price:
                selling_price = format_price(selling_price)
            
            if size_sqm:
                try:
                    size_sqm = float(size_sqm)
                except:
                    cur.close()
                    conn.close()
                    flash(f'Invalid size value for unit "{name}". Must be a number.', 'error')
                    return redirect(url_for('home'))
            
            if bedrooms:
                try:
                    bedrooms = int(bedrooms)
                except:
                    cur.close()
                    conn.close()
                    flash(f'Invalid bedrooms value for unit "{name}". Must be a whole number.', 'error')
                    return redirect(url_for('home'))
            
            if bathrooms:
                try:
                    bathrooms = int(bathrooms)
                except:
                    cur.close()
                    conn.close()
                    flash(f'Invalid bathrooms value for unit "{name}". Must be a whole number.', 'error')
                    return redirect(url_for('home'))
            
            cur.execute('''
                INSERT INTO units (
                    project_id, name, status, size_sqm, bedrooms, bathrooms, 
                    floor_number, selling_price, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (project_id, name, status, size_sqm, bedrooms, bathrooms, floor_number, selling_price, notes))
            
            imported_count += 1
        
        conn.commit()
        cur.close()
        conn.close()
        
        flash(f'Import successful! {imported_count} units added.', 'success')
        return redirect(url_for('home'))
        
    except Exception as e:
        flash(f'CSV import failed: {str(e)}. Please check the file format and try again.', 'error')
        return redirect(url_for('home'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)