from flask import Flask, render_template, request, redirect, url_for
#initialize Flask app
app = Flask(__name__)

# This is our "database" for now - just a list stored in memory
# When you restart the app, this resets. We'll fix that later with a real database

projects = []

# Route for the home page - handles GET requests (when you just visit the page)
@app.route('/')
def home():
    
    # render_template loads the HTML file and sends our 'units' list to it
    return render_template ('index.html', projects=projects)

# Route to add a new project
@app.route('/add_project', methods=['POST'])
def add_project():
    project_name = request.form['project_name']
    
    # Create new project with empty units list
    new_project = {
        'name': project_name,
        'units': []  # Each project starts with no units
    }
    
    projects.append(new_project)
    return redirect(url_for('home'))

# Route to add a unit to a specific project
# <int:project_id> means we expect the project's position in the list
@app.route('/add_unit/<int:project_id>', methods=['POST'])
def add_unit(project_id):
    unit_name = request.form['unit_name']
    status = request.form['status']
    
    # Create the unit
    new_unit = {
        'name': unit_name,
        'status': status
    }
    
    # Add unit to the specific project's units list
    if project_id < len(projects):
        projects[project_id]['units'].append(new_unit)
    
    return redirect(url_for('home'))

# Route to update a unit's status
@app.route('/update/<int:project_id>/<int:unit_id>', methods=['POST'])
def update_unit(project_id, unit_id):
    new_status = request.form['new_status']
    
    # Update the unit in the specific project
    if project_id < len(projects) and unit_id < len(projects[project_id]['units']):
        projects[project_id]['units'][unit_id]['status'] = new_status
    
    return redirect(url_for('home'))

# This runs the app in debug mode (shows errors, auto-reloads when you change code)
if __name__ == '__main__':
    app.run(debug=True)
