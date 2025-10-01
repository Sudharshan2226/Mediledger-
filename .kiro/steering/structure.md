# Project Structure & Organization

## Root Directory Layout

```
MediLedger/
├── app.py                    # Main Flask application
├── blockchain.py             # Custom blockchain implementation
├── blockchain_server.py      # Blockchain REST API server
├── migrate_db.py            # Database migration utility
├── requirements.txt         # Python dependencies
├── README.md               # Project documentation
├── HACKATHON_PRESENTATION_OUTLINE.md  # Presentation materials
├── instance/               # SQLite database storage
│   └── medical_tracking.db
├── static/                 # Static assets
│   └── qr_codes/          # Generated QR code images
├── templates/             # Jinja2 HTML templates
└── docs/                  # Static demo site for GitHub Pages
```

## Key Directories

### `/templates/` - Frontend Templates
- **Role-based dashboards**: `manufacturer.html`, `distributor.html`, `pharmacy.html`
- **Authentication**: `login.html`, `register.html`
- **Public pages**: `index.html`, `consumer.html`
- **Utility pages**: `alerts.html`, `reports.html`
- Uses TailwindCSS with responsive design patterns
- Consistent navigation and sidebar components across dashboards

### `/static/` - Static Assets
- **QR Codes**: Auto-generated in `qr_codes/` subdirectory
- **Naming Convention**: QR files named by batch ID (e.g., `{batch_id}.png`)
- **Access Pattern**: Served directly by Flask static file handler

### `/docs/` - Demo Site
- Static HTML versions for GitHub Pages deployment
- Mirrors main application functionality without backend
- Self-contained with embedded CSS and JavaScript

### `/instance/` - Database Storage
- SQLite database file location
- Automatically created by Flask-SQLAlchemy
- Contains all application data (users, products, tracking, etc.)

## Code Organization Patterns

### Database Models (in `app.py`)
- **User**: Authentication and role management
- **Product**: Core medicine/product information
- **TransportTracking**: Supply chain movement data
- **PharmacyInventory**: Stock management
- **Alert**: Notification system

### Route Structure
- **Public routes**: `/`, `/register`, `/login`, `/track/<batch_id>`
- **Role-based routes**: `/manufacturer`, `/distributor`, `/pharmacy`
- **API endpoints**: `/alerts`, `/reports`, `/api/analytics`
- **Utility routes**: `/logout`, `/profile`

### Template Inheritance
- Base templates with common navigation and styling
- Role-specific dashboard layouts
- Consistent form patterns across user types
- Responsive design with mobile-first approach

## File Naming Conventions

### Python Files
- Snake_case for all Python modules
- Descriptive names reflecting functionality
- Separate concerns (app logic, blockchain, migration)

### Templates
- Lowercase with hyphens for multi-word names
- Role-based prefixes where applicable
- Consistent naming across similar functionality

### Static Assets
- QR codes use UUID-based batch IDs as filenames
- Organized in subdirectories by asset type
- Direct correlation between database records and file paths

## Development Workflow

### Adding New Features
1. Update database models in `app.py` if needed
2. Run `migrate_db.py` for schema changes
3. Add routes and business logic to `app.py`
4. Create/update templates in `/templates/`
5. Update blockchain integration if tracking is involved

### Database Changes
- Always use `migrate_db.py` for schema updates
- Backup data before running migrations (drops all tables)
- Test with fresh database after model changes

### Static File Management
- QR codes generated automatically on product creation
- Files persist in `/static/qr_codes/` directory
- Clean up orphaned files periodically in production