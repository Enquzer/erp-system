Carement-System/
│
├── app.py                  # Main Flask application file
├── database.db             # SQLite database file (auto-generated)
├── requirements.txt        # Python dependencies
├── README.md               # Project documentation
│
├── static/                 # Static files (CSS, JS, images)
│   ├── css/
│   │   └── style.css       # Custom CSS with Carement colors
│   ├── js/
│   │   └── script.js       # JavaScript for frontend interactivity
│   └── images/
│       └── carement_logo.png  # Carement logo
│       └── products/       # Folder for product images (uploaded by factory)
│
├── templates/              # HTML templates for Flask
│   ├── base.html           # Base template with navigation and styling
│   ├── factory_upload.html # Factory product upload page
│   ├── shop_view.html      # Shop view of available products
│   ├── shop_order.html     # Shop reorder page
│   └── order_confirmation.html  # Order confirmation page with export option
│
└── scripts/                # Python scripts for database setup and utilities
    ├── db_setup.py         # Script to initialize SQLite database
    └── export_order.py     # Script to export orders as PDF/Excel