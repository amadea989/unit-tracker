from flask import Flask, render_template, request, redirect, url_for
#initialize Flask app
app = Flask(__name__)

# This is our "database" for now - just a list stored in memory
# When you restart the app, this resets. We'll fix that later with a real database

units = []

# Route for the home page - handles GET requests (when you just visit the page)
@app.route('/')
def home():
    
    # render_template loads the HTML file and sends our 'units' list to it
    return render_template ('index.html', units=units)

# Route for adding units - handles POST requests (when form is submitted)
@app.route('/add', methods=['POST'])
def add_unit():
    # request.form gets the data from the form submission
    # request.form['unit_name'] gets the value from the input with name="unit_name"
    unit_name = request.form ['unit_name']
    status = request.form['status']
    # Create a dictionary (like an object) for this unit
    new_unit = {
        'name': unit_name,
        'status': status
    }
    
    # Add it to our unit list
    units.append(new_unit)
    
    # Redirect back to home page so user sees the updated list
    # This prevents the "resubmit form" issue if user refreshes
    return redirect(url_for('home'))

# This runs the app in debug mode (shows errors, auto-reloads when you change code)
if __name__ == '__main__':
    app.run(debug=True)
