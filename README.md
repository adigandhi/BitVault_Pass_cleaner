# 🛡️ Bitwarden Password Vault Cleaner

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Clean and deduplicate your Bitwarden CSV exports with modern interactive tools. Perfect for removing duplicate entries after migrating from other password managers or consolidating multiple accounts.

## ✨ Features

- 🎮 **Interactive Mode**: Arrow key navigation, space bar selection, visual interface
- 🔍 **Smart Grouping**: Groups by base URI (perfect for cleaning old accounts)
- 🔑 **Password Visibility**: Optional password display for informed decisions
- 💾 **Auto Backups**: Complete file backup before any changes
- 🌐 **URL Normalization**: Handles various URL formats intelligently
- ⚡ **Dry-Run Mode**: Preview changes without modifications
- 📁 **Config Support**: Save preferences in JSON config files
- 🔄 **Restore Options**: Multiple backup restore methods

## 🚀 Quick Start

```bash
# Install dependencies
pip install pandas tqdm  # tqdm optional for progress bars

# Export your Bitwarden vault to CSV, then:
python clean_pass.py -f export.csv --mode interactive

# Show passwords to help decide which accounts to keep
python clean_pass.py -f export.csv --mode interactive --show-passwords

# Preview changes without modifying files
python clean_pass.py -f export.csv --mode auto --dry-run
```

## 🎮 Interactive Mode

```
🔍 INTERACTIVE DUPLICATE SELECTION
Group: Base URI: facebook.com (1/3)

📋 Controls: ↑↓ navigate • SPACE select • ENTER confirm • Q skip • ESC quit

▶️ ⬜ [ 1] https://facebook.com
      👤 User: old.email@gmail.com
      🔑 Password: ******* (7 chars)

   ❌ [ 2] https://m.facebook.com  
      👤 User: current.email@gmail.com

📊 Summary: 1 of 2 entries selected for deletion
```

## 🔧 Modes

| Mode | Description | Best For |
|------|-------------|----------|
| `interactive` | Arrow key navigation, manual selection | Removing old accounts for same services |
| `auto` | Automatic domain-based cleanup | Large datasets, aggressive deduplication |
| `analyze` | Preview duplicates without changes | Understanding your data |

## 📁 Files Created

- `original_backup_YYYYMMDD_HHMMSS.csv` - Complete backup before changes
- `original_cleaned.csv` - Your cleaned database  
- `original_deleted_entries_YYYYMMDD_HHMMSS.csv` - Deleted entries for recovery

## ⚙️ Additional Commands

```bash
# Create config file with your preferences
python clean_pass.py --save-config

# List available backups
python clean_pass.py --list-backups export.csv

# Restore from backups (interactive selection)
python clean_pass.py --undo export.csv

# Show passwords in interactive mode (use carefully)
python clean_pass.py -f export.csv --mode interactive --show-passwords
```

## ⚠️ Safety First

- 💾 **Automatic backups** created before any changes
- 🔒 **Never run on public networks** - your passwords are in plaintext
- 🧪 **Test on small files first** before processing large datasets
- 📝 **Review changes** using `--dry-run` mode

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

---

**⚠️ This tool modifies your password data. Always review changes carefully.**
