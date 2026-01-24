from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import json

app = Flask(__name__)

# Function to get database connection
def get_db():
    conn = sqlite3.connect('tracker.db')
    conn.row_factory = sqlite3.Row  # This lets us access columns by name
    return conn

# Initialize database - creates tables if they don't exist
def init_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS units (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            name TEXT NOT NULL,
            status TEXT NOT NULL,
            buyer_name TEXT,
            buyer_phone TEXT,
            buyer_email TEXT,
            sale_price TEXT,
            notes TEXT,
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    ''')
    conn.commit()
    conn.close()

# Call this when app starts
init_db()

@app.route('/')
def home():
    conn = get_db()
    
    # Get all projects
    projects_data = conn.execute('SELECT * FROM projects').fetchall()
    
    # Build projects list with their units
    projects = []
    for project in projects_data:
        units_data = conn.execute(
            'SELECT * FROM units WHERE project_id = ?', 
            (project['id'],)
        ).fetchall()
        
        # Convert units to list of dicts
        units = [{'name': u['name'], 'status': u['status'], 'id': u['id']} 
                for u in units_data]
        
        projects.append({
            'id': project['id'],
            'name': project['name'],
            'units': units
        })
    
    conn.close()
    return render_template('index.html', projects=projects)

@app.route('/add_project', methods=['POST'])
def add_project():
    project_name = request.form['project_name']
    
    conn = get_db()
    conn.execute('INSERT INTO projects (name) VALUES (?)', (project_name,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('home'))

@app.route('/add_unit/<int:project_id>', methods=['POST'])
def add_unit(project_id):
    unit_name = request.form['unit_name']
    status = request.form['status']
    
    conn = get_db()
    conn.execute(
        'INSERT INTO units (project_id, name, status) VALUES (?, ?, ?)',
        (project_id, unit_name, status)
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for('home'))

@app.route('/update/<int:project_id>/<int:unit_id>', methods=['POST'])
def update_unit(project_id, unit_id):
    new_status = request.form['new_status']
    
    conn = get_db()
    conn.execute(
        'UPDATE units SET status = ? WHERE id = ?',
        (new_status, unit_id)
    )
    conn.commit()
    conn.close()
    
    return redirect(url_for('home'))

# Route to view unit details
@app.route('/unit/<int:unit_id>')
def unit_details(unit_id):
    conn = get_db()
    unit = conn.execute('SELECT * FROM units WHERE id = ?', (unit_id,)).fetchone()
    project = conn.execute('SELECT * FROM projects WHERE id = ?', (unit['project_id'],)).fetchone()
    conn.close()
    
    return render_template('unit_details.html', unit=unit, project=project)

# Route to update unit details
@app.route('/update_details/<int:unit_id>', methods=['POST'])
def update_details(unit_id):
    buyer_name = request.form.get('buyer_name', '')
    buyer_phone = request.form.get('buyer_phone', '')
    buyer_email = request.form.get('buyer_email', '')
    sale_price = request.form.get('sale_price', '')
    notes = request.form.get('notes', '')
    
    conn = get_db()
    conn.execute('''
        UPDATE units 
        SET buyer_name = ?, buyer_phone = ?, buyer_email = ?, sale_price = ?, notes = ?
        WHERE id = ?
    ''', (buyer_name, buyer_phone, buyer_email, sale_price, notes, unit_id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('unit_details', unit_id=unit_id))

# Route to delete a unit
@app.route('/delete_unit/<int:unit_id>', methods=['POST'])
def delete_unit(unit_id):
    conn = get_db()
    conn.execute('DELETE FROM units WHERE id = ?', (unit_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

# Route to delete a project (and all its units)
@app.route('/delete_project/<int:project_id>', methods=['POST'])
def delete_project(project_id):
    conn = get_db()
    # Delete all units in this project first
    conn.execute('DELETE FROM units WHERE project_id = ?', (project_id,))
    # Then delete the project
    conn.execute('DELETE FROM projects WHERE id = ?', (project_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)