# 🛡️ Bitwarden Password Vault Cleaner

[![Python 3.6+](https://img.shields.io/badge/python-3.6+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/yourusername/bitwarden-cleaner/graphs/commit-activity)

A powerful Python utility to clean and deduplicate Bitwarden CSV exports, specifically designed to handle duplicates that occur when importing passwords from multiple devices into a single vault.

## 🎯 Purpose

When migrating to Bitwarden from other password managers or consolidating multiple accounts, you often end up with duplicate entries in your vault. This tool intelligently identifies and removes these duplicates while preserving your important login data.

## ✨ Features

- **🔍 Smart Duplicate Detection**: Identifies duplicates based on URL + username combinations
- **🌐 URL Normalization**: Handles various URL formats (with/without trailing slashes, www prefixes)
- **🏷️ Domain-Based Cleanup**: Groups entries by domain for more intelligent deduplication
- **✨ Name Column Cleanup**: Automatically removes parentheses content from entry names
- **⚙️ Multiple Cleaning Modes**:
  - Interactive mode (arrow key navigation, URI-based grouping)
  - Auto mode (automatic domain-based cleanup)
  - Analyze mode (analysis only)
- **🔍 Dry-Run Mode**: Preview changes without modifying files
- **📁 Configuration Support**: Save default settings in config files
- **📊 Progress Indicators**: Visual progress bars for long-running operations
- **🔄 Undo Functionality**: Restore from backup files with interactive selection
- **🔒 Security First**: Masks passwords in output, never logs sensitive data
- **💾 Automatic Backups**: Creates complete backup of original file before any changes
- **📊 Detailed Reporting**: Shows what was cleaned and statistics

## 🚀 Quick Start

### Prerequisites

```bash
pip install pandas
```

**Optional (for enhanced progress bars):**
```bash
pip install tqdm
```

### Basic Usage

1. **Export your Bitwarden vault** to CSV format
2. **Run the script**:

   ```bash
   python clean_pass.py -f your_bitwarden_export.csv --mode interactive
   ```

3. **Choose your cleaning mode**:
   - `interactive` - Manual review and selection with arrow key navigation
   - `auto` - Automatic domain-based deduplication
   - `analyze` - Analysis only (default)

4. **Optional: Show passwords for decision-making**:
   ```bash
   python clean_pass.py -f your_export.csv --mode interactive --show-passwords
   ```
   ⚠️ **Warning**: Only use `--show-passwords` in secure environments. Passwords will be visible on screen.

### Example Sessions

#### Basic Cleaning
```
$ python clean_pass.py -f bitwarden_export.csv --mode interactive

📄 Loaded configuration from: ~/.clean_pass_config.json
✓ CSV validation passed

💾 Creating backup of original file...
💾 Original file backed up to: bitwarden_export_backup_20241201_143020.csv

CSV Columns:
1. folder
2. favorite
...
10. login_password
11. login_totp

==================================================
Checking for duplicate login_uri entries:
==================================================
Found 45 rows with duplicate login_uri values.

📊 Processing duplicate groups: 100%|████████| 15/15 [00:02<00:00,  7.2it/s]

SUMMARY:
========================================
Original rows: 1,247
Fully duplicate rows removed: 12
Partial duplicate rows deleted: 28
Total rows removed: 40
Remaining rows: 1,207

Cleaned CSV saved as: bitwarden_export_cleaned.csv
Deleted entries saved to: bitwarden_export_deleted_entries_20241201_143022.csv
```

#### Dry Run Mode
```
$ python clean_pass.py -f bitwarden_export.csv --mode auto --dry-run

🔍 DRY RUN MODE: Previewing changes without modification

DRY RUN SUMMARY:
================
Original rows: 1,247
Would remove: 40 entries
Would keep: 1,207 entries

🔍 This was a DRY RUN - no changes were made to your data.
🔍 DRY RUN: No files were saved.
```

#### Interactive Mode with Password Visibility
```
$ python clean_pass.py -f export.csv --mode interactive --show-passwords

🔍 INTERACTIVE DUPLICATE CLEANUP
Now matching only on base URI (ignoring username/password)
This allows you to clean up old/inactive accounts for the same service

▶️ ⬜ [ 1] https://oldsite.com
      👤 User: user@email.com
      🔑 Password: oldpassword123
      🏷️  Name: Old Account

   ⬜ [ 2] https://oldsite.com
      👤 User: user@email.com  
      🔑 Password: newpassword456
      🏷️  Name: Current Account

Press ENTER to confirm, Q to skip, ESC to quit, ↑↓ to navigate, SPACE to toggle
```

#### Configuration and Undo
```
$ python clean_pass.py --save-config
✅ Configuration template saved to: ~/.clean_pass_config.json

$ python clean_pass.py --list-backups bitwarden_export.csv

💾 Available backup files for bitwarden_export.csv:
============================================================
 1. bitwarden_export_backup_20241201_143020.csv
    Type: Original file backup
    Size: 2.1 MB
    Modified: 2024-12-01 14:30:20

 2. bitwarden_export_deleted_entries_20241201_143022.csv
    Type: Deleted entries backup
    Size: 0.2 MB
    Modified: 2024-12-01 14:30:22

 3. bitwarden_export_cleaned.csv
    Type: Cleaned data file
    Size: 1.8 MB
    Modified: 2024-12-01 14:30:20

$ python clean_pass.py --undo bitwarden_export.csv
🔄 Restoring deleted entries from: bitwarden_export_deleted_entries_20241201_143022.csv
✅ Successfully restored 40 deleted entries
```

## 📖 Detailed Usage

### Understanding the Cleaning Process

The script follows a multi-step approach:

1. **Full Duplicate Removal** - Removes completely identical rows
2. **URL Normalization** - Standardizes URLs for better comparison  
3. **Name Cleanup** - Removes parentheses content from entry names (e.g., "365.altium.com (<user@email.com>)" → "365.altium.com")
4. **Duplicate Detection** - Finds entries with same URL + username
5. **User Selection** - Allows manual duplicate resolution  
6. **Backup Creation** - Creates complete backup of original file before changes
7. **Deleted Entry Tracking** - Saves deleted entries for recovery

### Cleaning Modes Explained

#### 👆 Interactive Mode

- **Best for**: Cleaning up old/inactive accounts for the same services
- **Logic**: Groups entries by base URI only (ignores username/password), arrow key navigation
- **Interface**: Modern keyboard navigation (↑↓ to navigate, SPACE to select, ENTER to confirm)
- **Speed**: Slower (requires user input)
- **Safety**: Highest (manual review with visual interface)
- **Use case**: Perfect for removing old accounts: `facebook.com` with old email vs new email

#### 🤖 Auto Mode

- **Best for**: Automatic deduplication across similar URLs
- **Logic**: One entry per domain + username + password combination
- **Example**: Keeps `facebook.com` but removes `m.facebook.com`, `www.facebook.com`
- **⚠️ Warning**: Most aggressive, review deletions carefully

### File Outputs

| File | Description |
|------|-------------|
| `original_backup_YYYYMMDD_HHMMSS.csv` | Complete backup of original file (created before any changes) |
| `original_cleaned.csv` | Your cleaned password database |
| `original_deleted_entries_YYYYMMDD_HHMMSS.csv` | Timestamped backup of deleted entries |

## 🚀 Advanced Features

### Configuration Files

Create a configuration file to set default preferences:

```bash
python clean_pass.py --save-config
```

This creates `~/.clean_pass_config.json`:

```json
{
  "mode": "analyze",
  "verbose": false,
  "dry_run": false,
  "output": null
}
```

### Dry-Run Mode

Preview changes without modifying files:

```bash
python clean_pass.py -f export.csv --mode auto --dry-run
```

### Progress Indicators

For large files (1000+ entries), the script automatically shows progress bars:
- **File loading**: Shows loading progress for files >10MB
- **URL normalization**: Progress for >5000 entries
- **Domain extraction**: Progress for >1000 entries
- **Duplicate processing**: Progress for >10 duplicate groups

*Note: Requires `tqdm` package for enhanced progress bars. Falls back to simple indicators if not available.*

### Interactive Mode Controls

The enhanced interactive mode provides powerful keyboard navigation:

**Navigation & Selection:**
- **↑/↓ Arrow Keys**: Move between duplicate entries
- **SPACE**: Toggle selection for deletion (❌/⬜)
- **ENTER**: Confirm selections and proceed to next group
- **Q**: Skip current group (leave all entries)
- **ESC**: Exit interactive mode completely (process deletions so far)

**Password Visibility:**
```bash
# Show masked passwords (default - secure)
python clean_pass.py -f export.csv --mode interactive

# Show actual passwords (use with caution)
python clean_pass.py -f export.csv --mode interactive --show-passwords
```

**Entry Information Displayed:**
- 🌐 **URI**: Full login URL
- 👤 **Username**: Login username
- 🔑 **Password**: Masked (●●●●●●●) or visible based on `--show-passwords`
- 🏷️ **Name**: Entry name/title (if available)
- 📅 **Created**: Creation date (if available)

### Backup and Restore

List available backups:
```bash
python clean_pass.py --list-backups export.csv
```

Restore from backups:
```bash
python clean_pass.py --undo export.csv
```

The restore function can:
- **Restore original file** from complete backup (before any changes)
- **Merge deleted entries** back with cleaned data  
- **Restore cleaned files** to original location
- **Interactive selection** of which backup to restore

### Enhanced Interactive Mode

The interactive mode now features a modern keyboard-driven interface:

```
🔍 INTERACTIVE DUPLICATE SELECTION
============================================================
Group: Base URI: facebook.com (1/3)
============================================================

📋 Instructions:
  ↑↓ : Navigate between entries
  SPACE: Toggle selection for deletion
  ENTER: Confirm selections
  Q: Skip this group
  ESC: Quit interactive mode completely

🗂️  Entries (❌ = selected for deletion):
------------------------------------------------------------

▶️ ⬜ [ 1] https://facebook.com
      👤 User: old.email@gmail.com
      🔑 Password: ******* (7 chars)
      🏷️  Name: Facebook (old account)

   ❌ [ 2] https://m.facebook.com
      👤 User: current.email@gmail.com

   ⬜ [ 3] https://www.facebook.com
      👤 User: backup.email@yahoo.com

📊 Summary: 1 of 3 entries selected for deletion

Press ENTER to confirm, Q to skip, ↑↓ to navigate, SPACE to toggle selection
```

**Key Improvements:**
- **URI-only matching**: Groups by base URI, ignoring username/password differences
- **Visual navigation**: Arrow keys to move, space bar to select
- **Clear indicators**: ▶️ shows current position, ❌ shows selected for deletion
- **Password visibility**: Optional `--show-passwords` flag to show actual passwords vs masked
- **Early exit**: ESC key to quit interactive mode without processing all groups
- **Cross-platform**: Works on Windows, macOS, and Linux
- **Fallback support**: Automatic fallback to text input if keyboard navigation fails

## 🔧 Core Functions

### Analysis Functions

- `read_csv_and_print_columns()` - Displays CSV structure
- `find_duplicate_login_uris()` - Finds duplicate URLs
- `find_duplicate_uri_and_username()` - Finds duplicate URL+username pairs

### Cleaning Functions

- `interactive_delete_duplicates()` - Manual duplicate selection
- `automatic_delete_duplicates()` - Automated duplicate removal
- `automatic_domain_cleanup()` - Domain-based aggressive cleanup

### Utility Functions

- `normalize_urls()` - Standardizes URL formats
- `extract_domain()` - Intelligent domain extraction
- `remove_fully_duplicate_rows()` - Removes identical entries

## ⚠️ Important Considerations

### Security

- **Never run on unencrypted networks** - CSV contains passwords in plaintext
- **Delete CSV files after use** - Don't leave sensitive files on disk
- **Review deleted entries** - Always check the backup file before permanent deletion

### Data Safety

- **Automatic backups** - Complete backup of original file created before any changes
- **Test on a small subset** first if working with large datasets  
- **Review deleted entries** - Check `_deleted_entries.csv` files before permanent deletion
- **Multiple restore options** - Restore original file or merge back deleted entries

### Performance

- **Memory usage** scales with file size (1000 entries ≈ 50MB RAM)
- **Large files** (10,000+ entries) should use auto mode for efficiency
- **Interactive mode** is not recommended for >500 duplicates

## 🛠️ Improvements Needed

### High Priority Fixes

- [x] **Implement proper logging** instead of print statements ✅  
- [x] **Add data validation** for CSV structure before processing ✅
- [x] **Better error handling** with specific error messages ✅

### Feature Enhancements

- [x] **Add dry-run mode** to preview changes without modification ✅
- [ ] **Support for different CSV formats** (1Password, LastPass, etc.)
- [x] **Configuration file support** for default settings ✅
- [x] **Progress bars** for long-running operations ✅
- [x] **Undo functionality** to restore from backup files ✅

### Code Quality Improvements

- [ ] **Split into modules** - separate analysis, cleaning, and utilities
- [ ] **Add type hints** throughout the codebase
- [ ] **Implement proper exception classes** for different error types
- [ ] **Add comprehensive unit tests**
- [ ] **Code documentation** and docstrings for all functions

### Security Enhancements

- [ ] **Option to work with encrypted files** (password-protected CSVs)
- [ ] **Secure memory handling** for password data
- [ ] **Audit logging** for compliance tracking
- [ ] **Integration with secure storage** (avoid plaintext CSVs)

## 🤝 Contributing

Found a bug or want to add a feature? Contributions are welcome!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚡ Quick Tips

- **Start with analysis** - Always run the script first to see what duplicates exist
- **Use interactive mode** for careful manual review
- **Use auto mode** for large datasets to save time
- **Keep backups** - The `_deleted_entries.csv` file is your safety net
- **Test incrementally** - Clean a few duplicates first, then proceed with bulk operations
- **Review auto cleanup carefully** - It's the most aggressive option

---

**⚠️ Disclaimer**: This tool modifies your password data. Always backup your original files and test on a small dataset first. The authors are not responsible for any data loss.
