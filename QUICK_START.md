# 🚀 Solvia Quick Start Guide

## ⚡ Run Solvia
```bash
python solvia.py
```

## 🔧 Common Commands

### Test Airtable Connection
```bash
python scripts/test_airtable_connection.py
```

### Debug Multi-Table Setup
```bash
python scripts/debug_organized_tables.py
```

### Check Table Fields
```bash
python scripts/check_table_fields.py
```

## 📁 Key Files
- **`solvia.py`** - Main launcher
- **`core/main.py`** - Core application
- **`.env`** - Environment configuration
- **`docs/README.md`** - Full documentation
- **`docs/PROJECT_STRUCTURE.md`** - File organization

## 🆘 Quick Troubleshooting
1. **Import errors**: Run from root directory
2. **Airtable errors**: Check `.env` configuration
3. **OAuth errors**: Delete `config/token.pickle` and re-authenticate
4. **Missing dependencies**: `pip install -r requirements.txt`

## 📋 Environment Setup
Create `.env` file with:
```env
AIRTABLE_API_KEY=your_key
AIRTABLE_BASE_ID=your_base
USE_ORGANIZED_TABLES=true
OPENAI_API_KEY=your_openai_key
```

For detailed setup, see `docs/README.md` 