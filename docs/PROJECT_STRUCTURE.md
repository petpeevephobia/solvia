# 📁 Solvia Project Structure

## 🎯 Overview
The Solvia SEO audit tool has been reorganized into a clean, maintainable structure that separates core functionality, documentation, utilities, and configuration.

## 📂 Directory Structure

```
Solvia_v1.3/
│
├── 📁 core/                          # Core Application Code
│   ├── main.py                       # Main application logic
│   ├── 📁 modules/                   # Core modules
│   │   ├── business_analysis.py      # Business intelligence analysis
│   │   └── report_generator.py       # PDF report generation & email
│   └── 📁 prompts/                   # AI prompts
│       ├── business_analysis_enhancement.txt
│       └── seo_analysis_prompt.txt
│
├── 📁 docs/                          # Documentation
│   ├── README.md                     # Main project documentation
│   ├── PROJECT_STRUCTURE.md          # This file
│   ├── Business_Analysis_Setup.md    # Airtable setup guide
│   ├── Business_Analysis_Select_Options.md
│   └── fix_business_analysis_url.md
│
├── 📁 scripts/                       # Utility Scripts
│   ├── debug_organized_tables.py     # Debug Airtable connections
│   ├── test_airtable_connection.py   # Test connectivity
│   └── check_table_fields.py         # Field validation
│
├── 📁 tests/                         # Testing & Troubleshooting
│   └── 📁 troubleshooting/           # Troubleshooting utilities
│       ├── README.md                 # Troubleshooting guide
│       ├── Business_Analysis.csv     # Sample data
│       └── [other debug files]
│
├── 📁 config/                        # Configuration Files
│   └── token.pickle                  # Google OAuth credentials
│
├── 📁 data/                          # Data & Logs
│   └── debug.log                     # Application logs
│
├── 📁 reports/                       # Generated Reports
│   ├── 📁 generated/                 # PDF reports output
│   └── 📁 templates/                 # Report templates
│
├── 📁 venv/                          # Virtual Environment
│
├── solvia.py                         # 🚀 MAIN LAUNCHER
├── requirements.txt                  # Dependencies
├── .env                              # Environment variables
├── .gitignore                        # Git ignore rules
└── venv/                             # Virtual environment
```

## 🚀 Running the Application

### Primary Method
```bash
python solvia.py
```

### Alternative Method
```bash
cd core
python main.py
```

## 📋 File Descriptions

### Core Application (`core/`)
- **`main.py`**: Main application logic with all SEO analysis functions
- **`modules/business_analysis.py`**: Business intelligence and website analysis
- **`modules/report_generator.py`**: PDF generation and email delivery
- **`prompts/`**: AI prompt templates for enhanced analysis

### Documentation (`docs/`)
- **`README.md`**: Complete setup and usage guide
- **`PROJECT_STRUCTURE.md`**: This structure documentation
- **Setup guides**: Airtable configuration and troubleshooting

### Utility Scripts (`scripts/`)
- **`debug_organized_tables.py`**: Debug multi-table Airtable setup
- **`test_airtable_connection.py`**: Test Airtable connectivity
- **`check_table_fields.py`**: Validate Airtable field structure

### Testing (`tests/`)
- **`troubleshooting/`**: Diagnostic tools and sample data
- **Debug utilities**: For resolving setup issues

## 🔧 Configuration

### Environment Variables
Create a `.env` file in the root directory with:
```env
# Airtable Configuration
AIRTABLE_API_KEY=your_api_key
AIRTABLE_BASE_ID=your_base_id
AIRTABLE_TABLE_NAME=your_table_name  # If using single table
USE_ORGANIZED_TABLES=true             # For multi-table setup

# OpenAI Configuration
OPENAI_API_KEY=your_openai_key

# Email Configuration (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email
SMTP_PASSWORD=your_app_password
EMAIL_FROM=your_email
```

### Google OAuth
- Place `credentials.json` in the root directory
- OAuth token will be saved to `config/token.pickle`

## 🏗️ Development

### Adding New Features
1. **Core logic**: Add to `core/main.py` or create new modules in `core/modules/`
2. **AI prompts**: Add to `core/prompts/`
3. **Documentation**: Update relevant files in `docs/`
4. **Tests**: Add debugging utilities to `scripts/` or `tests/`

### Import Paths
Since `solvia.py` adds the `core/` directory to the Python path:
- Import modules normally: `from modules.business_analysis import BusinessAnalyzer`
- Config files use relative paths: `../config/token.pickle`
- Prompts use relative paths: `prompts/seo_analysis_prompt.txt`

## 🔄 Migration Benefits

### Before (Disorganized)
```
├── main.py
├── debug_organized_tables.py
├── test_airtable_connection.py
├── Business_Analysis_Setup.md
├── README.md
├── modules/
└── [mixed files]
```

### After (Organized)
```
├── solvia.py                 # Clear entry point
├── core/                     # Core application
├── docs/                     # All documentation
├── scripts/                  # Utility scripts
├── tests/                    # Testing tools
└── config/                   # Configuration
```

### Advantages
✅ **Clear separation** of concerns  
✅ **Easy navigation** and maintenance  
✅ **Professional structure** for development  
✅ **Simple entry point** with `solvia.py`  
✅ **Scalable architecture** for future features  
✅ **Better version control** organization  

## 🚨 Important Notes

### File Paths
- Always run `python solvia.py` from the root directory
- Config files use `../config/` paths from core
- All relative paths are calculated from the executing script location

### Dependencies
- All Python packages listed in `requirements.txt`
- Virtual environment recommended: `python -m venv venv`
- Activate: `venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Unix)

## 🆘 Troubleshooting

If you encounter import errors:
1. Ensure you're running from the root directory
2. Check that all files moved correctly
3. Use the diagnostic scripts in `scripts/`
4. Refer to troubleshooting guides in `docs/`

For Airtable issues:
1. Run `python scripts/test_airtable_connection.py`
2. Check field configurations with `python scripts/check_table_fields.py`
3. Debug multi-table setup with `python scripts/debug_organized_tables.py` 