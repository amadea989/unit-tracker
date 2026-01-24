# Unit Progress Tracker

A comprehensive real estate unit management system built with Flask and SQLite. Designed to help real estate companies track multiple projects, manage unit inventory, and monitor sales progress in real-time.

## Features

- **Multi-Project Management**: Organize units across multiple real estate projects/complexes
- **Unit Tracking**: Add, update, and delete units with status tracking (Available, Viewing, Reserved, Sold)
- **Buyer Management**: Record buyer details, contact information, and sale prices for sold units
- **Dashboard Analytics**: Real-time statistics and visual breakdowns of unit status distribution
- **Notes System**: Add progress notes and updates for each unit
- **Secure Authentication**: Password-protected access to prevent unauthorized changes
- **Responsive Design**: Clean, professional corporate UI that works on desktop and mobile

## Technology Stack

- **Backend**: Python 3.11, Flask 3.1
- **Database**: SQLite3
- **Frontend**: HTML5, CSS3, Jinja2 templating
- **Design**: Corporate/professional UI with responsive layout

## Installation & Setup

### Prerequisites
- Python 3.11 or higher
- Git

### Local Installation

1. Clone the repository:
```bash
git clone https://github.com/amadea989/unit-tracker.git
cd unit-tracker
```

2. Install dependencies:
```bash
pip install flask
```

3. Run the application:
```bash
python app.py
```

4. Open your browser and navigate to:
```
http://127.0.0.1:5000
```

5. Login with default credentials:
- Password: `admin123`

## Usage

### Creating a Project
1. Enter a project name in the "Create New Project" section
2. Click "Create Project"

### Adding Units
1. Within each project, use the "Add Unit" form
2. Enter unit name/number and select initial status
3. Click "Add Unit"

### Managing Unit Details
1. Click on any unit name to view full details
2. Update buyer information (only visible when status = Sold)
3. Add notes and progress updates
4. Save changes

### Viewing Analytics
- Click "Dashboard" to see overall statistics
- View total projects, units, and revenue
- See visual breakdown of unit status distribution

## Security Notes

**Important**: This application uses a simple password authentication for demonstration purposes. For production use, implement:
- Proper user authentication with hashed passwords
- Database migration from SQLite to PostgreSQL/MySQL
- Environment variables for sensitive configuration
- HTTPS/SSL certificates

## Project Structure
```
unit-tracker/
├── app.py                  # Main Flask application
├── tracker.db              # SQLite database (auto-generated)
├── templates/              # HTML templates
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   └── unit_details.html
└── static/                 # Static assets
    └── css/
        ├── style.css
        ├── login.css
        ├── dashboard.css
        └── unit_details.css
```

## Future Enhancements

- [ ] File upload functionality (receipts, KYC documents, photos)
- [ ] Multi-user support with role-based permissions
- [ ] Email notifications for status changes
- [ ] Export data to Excel/PDF
- [ ] Calendar integration for viewings
- [ ] Mobile app version

## Contributing

This is a portfolio project, but suggestions and feedback are welcome. Feel free to open an issue or submit a pull request.

## License

This project is open source and available for educational and portfolio purposes.

## Author

**Sky Amadea**  
- GitHub: [@amadea989](https://github.com/amadea989)
- Email: amdea.sky@gmail.com

---

Built as part of my technical portfolio to demonstrate full-stack web development skills.