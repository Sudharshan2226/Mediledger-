# Technology Stack & Build System

## Core Technologies

### Backend
- **Framework**: Flask (Python web framework)
- **Database**: SQLite (development) / PostgreSQL (production ready)
- **ORM**: Flask-SQLAlchemy for database operations
- **Authentication**: Flask-Login with Werkzeug password hashing
- **Blockchain**: Custom implementation with REST API

### Frontend
- **Styling**: TailwindCSS for responsive design
- **JavaScript**: Vanilla JS with Chart.js and ApexCharts for analytics
- **Icons**: Font Awesome 6.0
- **Fonts**: Inter font family from Google Fonts

### Key Libraries
- **QR Codes**: `qrcode` library for batch identification
- **HTTP Requests**: `requests` for blockchain server communication  
- **Data Processing**: `pandas` for analytics and reporting
- **Excel Export**: `openpyxl` and `xlsxwriter` for report generation
- **Image Processing**: `Pillow` for QR code generation

## Architecture Components

### Main Application (`app.py`)
- Flask web server running on port 8080
- Role-based routing for manufacturers, distributors, pharmacies
- SQLAlchemy models for users, products, tracking, inventory, alerts
- QR code generation and blockchain integration

### Blockchain Server (`blockchain_server.py`)
- Separate Flask server on port 5000
- Custom blockchain implementation with proof-of-work
- REST API endpoints for transaction management
- Thread-safe operations with mining capabilities

### Database Models
- User management with role-based access
- Product lifecycle tracking
- Transport and inventory management
- Alert system for quality monitoring

## Common Commands

### Development Setup
```bash
# Create virtual environment
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -r requirements.txt

# Database migration
python migrate_db.py

# Run blockchain server (separate terminal)
python blockchain_server.py

# Run main application
python app.py
```

### Application Access
- **Main App**: http://localhost:8080
- **Blockchain Server**: http://localhost:5000
- **QR Codes**: Generated in `static/qr_codes/` directory

### Database Operations
- SQLite database stored in `instance/medical_tracking.db`
- Use `migrate_db.py` for schema updates (drops existing data)
- Models auto-create tables on first run

## Development Notes
- Blockchain server must run separately from main application
- QR codes link to blockchain server for product tracking
- Static files served from `static/` directory
- Templates use Jinja2 with TailwindCSS styling