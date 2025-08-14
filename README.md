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
  - Interactive mode (manual selection)
  - Auto mode (automatic domain-based cleanup)
- **🔒 Security First**: Masks passwords in output, never logs sensitive data
- **💾 Backup Protection**: Automatically saves deleted entries for recovery
- **📊 Detailed Reporting**: Shows what was cleaned and statistics

## 🚀 Quick Start

### Prerequisites

```bash
pip install pandas
```

### Basic Usage

1. **Export your Bitwarden vault** to CSV format
2. **Run the script**:

   ```bash
   python clean_pass.py -f your_bitwarden_export.csv --mode interactive
   ```

3. **Choose your cleaning mode**:
   - `interactive` - Manual review and selection
   - `auto` - Automatic domain-based deduplication
   - `analyze` - Analysis only (default)

### Example Session

```
$ python clean_pass.py -f bitwarden_export.csv --mode interactive

CSV Columns:
1. folder
2. favorite
3. type
4. name
5. notes
6. fields
7. reprompt
8. login_uri
9. login_username
10. login_password
11. login_totp

==================================================
Checking for duplicate login_uri entries:
==================================================
Found 45 rows with duplicate login_uri values.

==================================================
STEP 1: Removing fully duplicate rows
==================================================
Automatically removed 12 fully duplicate rows

==================================================
STEP 1.5: Normalizing URLs and cleaning names
==================================================
✓ Cleaned 23 entries in name column (removed parentheses content)
URLs normalized (trailing slashes removed for duplicate detection)

==================================================
STEP 2: Interactive partial duplicate cleanup
==================================================
Found 33 rows with duplicate login_uri + login_username combinations

[Interactive selection process...]

SUMMARY:
========================================
Original rows: 1,247
Fully duplicate rows removed: 12
Partial duplicate rows deleted: 28
Total rows removed: 40
Remaining rows: 1,207

Cleaned CSV saved as: bitwarden_export_cleaned.csv
Deleted entries saved to: bitwarden_export_deleted_entries.csv
```

## 📖 Detailed Usage

### Understanding the Cleaning Process

The script follows a multi-step approach:

1. **Full Duplicate Removal** - Removes completely identical rows
2. **URL Normalization** - Standardizes URLs for better comparison  
3. **Name Cleanup** - Removes parentheses content from entry names (e.g., "365.altium.com (<user@email.com>)" → "365.altium.com")
4. **Duplicate Detection** - Finds entries with same URL + username
5. **User Selection** - Allows manual duplicate resolution
6. **Backup Creation** - Saves deleted entries for recovery

### Cleaning Modes Explained

#### 👆 Interactive Mode

- **Best for**: Smaller datasets or when you want control
- **Logic**: Shows each duplicate group, lets you choose what to delete
- **Speed**: Slower (requires user input)
- **Safety**: Highest (manual review)

#### 🤖 Auto Mode

- **Best for**: Automatic deduplication across similar URLs
- **Logic**: One entry per domain + username + password combination
- **Example**: Keeps `facebook.com` but removes `m.facebook.com`, `www.facebook.com`
- **⚠️ Warning**: Most aggressive, review deletions carefully

### File Outputs

| File | Description |
|------|-------------|
| `original_cleaned.csv` | Your cleaned password database |
| `original_deleted_entries.csv` | Backup of all deleted entries |

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

- **Always backup** your original Bitwarden export before running
- **Test on a small subset** first if working with large datasets
- **Review the `_deleted_entries.csv`** file before permanent deletion

### Performance

- **Memory usage** scales with file size (1000 entries ≈ 50MB RAM)
- **Large files** (10,000+ entries) should use auto mode for efficiency
- **Interactive mode** is not recommended for >500 duplicates

## 🛠️ Improvements Needed

### High Priority Fixes

- [ ] **Implement proper logging** instead of print statements  
- [ ] **Add data validation** for CSV structure before processing
- [ ] **Better error handling** with specific error messages

### Feature Enhancements

- [ ] **Add dry-run mode** to preview changes without modification
- [ ] **Support for different CSV formats** (1Password, LastPass, etc.)
- [ ] **Configuration file support** for default settings
- [ ] **Progress bars** for long-running operations
- [ ] **Undo functionality** to restore from backup files

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

