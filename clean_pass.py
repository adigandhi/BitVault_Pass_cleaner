import pandas as pd
from urllib.parse import urlparse
import argparse
import logging
import sys
from pathlib import Path
import json
import os
import datetime
import shutil
from glob import glob

# For interactive keyboard input
try:
    import select
    import termios
    import tty
    UNIX_TERMINAL = True
except ImportError:
    # Windows doesn't have these modules
    UNIX_TERMINAL = False

# Optional progress bar support
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    # Fallback progress indicator
    class tqdm:
        def __init__(self, iterable=None, total=None, desc=None, **kwargs):
            self.iterable = iterable
            self.total = total
            self.desc = desc
            self.current = 0
            if desc:
                print(f"{desc}...")
        
        def __iter__(self):
            if self.iterable:
                for item in self.iterable:
                    yield item
                    self.current += 1
            return self
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            if self.desc:
                print(f"{self.desc} complete.")
        
        def update(self, n=1):
            self.current += n
            if self.total and self.current % max(1, self.total // 10) == 0:
                progress = (self.current / self.total) * 100
                print(f"Progress: {progress:.0f}%")
        
        def set_description(self, desc):
            self.desc = desc
            print(f"{desc}...")
        
        def close(self):
            if self.desc:
                print(f"{self.desc} complete.")

class KeyboardInput:
    """Handle keyboard input for interactive selection."""
    
    def __init__(self):
        self.old_settings = None
    
    def __enter__(self):
        if UNIX_TERMINAL:
            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setraw(sys.stdin.fileno())
        return self
    
    def __exit__(self, type, value, traceback):
        if UNIX_TERMINAL and self.old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
    
    def get_key(self):
        """Get a single keypress."""
        if sys.platform == 'win32':
            try:
                import msvcrt
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key == b'\xe0':  # Arrow key prefix on Windows
                        key = msvcrt.getch()
                        if key == b'H': return 'UP'
                        elif key == b'P': return 'DOWN'
                        elif key == b'K': return 'LEFT'
                        elif key == b'M': return 'RIGHT'
                    elif key == b' ': return 'SPACE'
                    elif key == b'\r': return 'ENTER'
                    elif key == b'\x03': return 'CTRL_C'
                    elif key == b'\x1b': return 'ESC'  # ESC key
                    elif key in [b'q', b'Q']: return 'QUIT'
                    return key.decode('utf-8', errors='ignore')
                return None
            except ImportError:
                return None
        elif UNIX_TERMINAL:
            if select.select([sys.stdin], [], [], 0.1) == ([sys.stdin], [], []):
                char = sys.stdin.read(1)
                if char == '\x1b':  # ESC sequence
                    # Try to read more characters for arrow keys
                    try:
                        next_chars = sys.stdin.read(2)
                        if next_chars == '[A': return 'UP'
                        elif next_chars == '[B': return 'DOWN'
                        elif next_chars == '[C': return 'RIGHT'
                        elif next_chars == '[D': return 'LEFT'
                        else:
                            return 'ESC'  # Plain ESC key
                    except:
                        return 'ESC'  # Plain ESC key
                elif char == ' ': return 'SPACE'
                elif char == '\r' or char == '\n': return 'ENTER'
                elif char == '\x03': return 'CTRL_C'
                elif char == 'q' or char == 'Q': return 'QUIT'
                return char
            return None
        else:
            # Fallback for systems without terminal support
            return None

def display_duplicate_group_interactive(group_df, group_info, selected_indices=None):
    """Display a group of duplicates with interactive selection."""
    if selected_indices is None:
        selected_indices = set()
    
    os.system('clear' if os.name == 'posix' else 'cls')
    
    print("🔍 INTERACTIVE DUPLICATE SELECTION")
    print("=" * 60)
    print(f"Group: {group_info}")
    print("=" * 60)
    print()
    print("📋 Instructions:")
    print("  ↑↓ : Navigate between entries")
    print("  SPACE: Toggle selection for deletion")
    print("  ENTER: Confirm selections")
    print("  Q: Skip this group")
    print()
    print("🗂️  Entries (❌ = selected for deletion):")
    print("-" * 60)
    
    for idx, (_, row) in enumerate(group_df.iterrows()):
        marker = "❌" if idx in selected_indices else "  "
        print(f"{marker} [{idx + 1:2d}] {row['login_uri']}")
        print(f"      👤 User: {row['login_username']}")
        if 'name' in row and pd.notna(row['name']) and row['name'].strip():
            print(f"      🏷️  Name: {row['name']}")
        print()
    
    print(f"📊 Summary: {len(selected_indices)} of {len(group_df)} entries selected for deletion")
    return len(group_df)

def interactive_select_entries(group_df, group_info, show_passwords=False):
    """Interactive selection of entries using arrow keys and space bar."""
    selected_indices = set()
    current_row = 0
    total_rows = len(group_df)
    
    while True:
        # Clear screen and display current state
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🔍 INTERACTIVE DUPLICATE SELECTION")
        print("=" * 60)
        print(f"Group: {group_info}")
        print("=" * 60)
        print()
        print("📋 Instructions:")
        print("  ↑↓ : Navigate between entries")
        print("  SPACE: Toggle selection for deletion")
        print("  ENTER: Confirm selections")
        print("  Q: Skip this group")
        print("  ESC: Quit interactive mode completely")
        print()
        print("🗂️  Entries (❌ = selected for deletion):")
        print("-" * 60)
        
        # Display entries with highlighting
        for idx, (_, row) in enumerate(group_df.iterrows()):
            # Highlight current row
            if idx == current_row:
                print("▶️ ", end="")
            else:
                print("   ", end="")
            
            # Selection marker
            marker = "❌" if idx in selected_indices else "⬜"
            print(f"{marker} [{idx + 1:2d}] {row['login_uri']}")
            
            # User info
            if idx == current_row:
                print(f"      👤 User: {row['login_username']}")
                if 'login_password' in row:
                    if show_passwords:
                        password_display = str(row['login_password']) if pd.notna(row['login_password']) else "[empty]"
                        print(f"      🔑 Password: {password_display}")
                    else:
                        password_length = len(str(row['login_password'])) if pd.notna(row['login_password']) else 0
                        print(f"      🔑 Password: {'*' * password_length} ({password_length} chars)")
                if 'name' in row and pd.notna(row['name']) and row['name'].strip():
                    print(f"      🏷️  Name: {row['name']}")
                # Show creation date if available
                if 'creation_date' in row and pd.notna(row['creation_date']):
                    print(f"      📅 Created: {row['creation_date']}")
            print()
        
        print(f"📊 Summary: {len(selected_indices)} of {total_rows} entries selected for deletion")
        print()
        print("Press ENTER to confirm, Q to skip, ↑↓ to navigate, SPACE to toggle selection")
        
        # Get keyboard input
        try:
            with KeyboardInput() as kb:
                while True:
                    key = kb.get_key()
                    if key is None:
                        continue
                    
                    if key == 'UP':
                        current_row = (current_row - 1) % total_rows
                        break
                    elif key == 'DOWN':
                        current_row = (current_row + 1) % total_rows
                        break
                    elif key == 'SPACE':
                        if current_row in selected_indices:
                            selected_indices.remove(current_row)
                        else:
                            selected_indices.add(current_row)
                        break
                    elif key == 'ENTER':
                        return [group_df.iloc[i].name for i in selected_indices]
                    elif key == 'QUIT' or key == 'CTRL_C':
                        return []
                    elif key == 'ESC':
                        return 'QUIT_ALL'  # Special signal to quit all interactive mode
                    
        except KeyboardInterrupt:
            return []
        except Exception as e:
            # Fallback to text input if keyboard handling fails
            print(f"\n⚠️  Keyboard navigation not available ({e})")
            print("Falling back to text input mode...")
            
            print("\nWhich entries would you like to DELETE?")
            print("Enter row numbers (1-{}) separated by commas, or 'none' to keep all:".format(total_rows))
            
            while True:
                try:
                    user_input = input("Rows to delete: ").strip().lower()
                    
                    if user_input == 'none' or user_input == '':
                        return []
                    
                    selected_rows = [int(x.strip()) for x in user_input.split(',')]
                    
                    if all(1 <= row <= total_rows for row in selected_rows):
                        return [group_df.iloc[row - 1].name for row in selected_rows]
                    else:
                        print(f"Please enter numbers between 1 and {total_rows}")
                        
                except ValueError:
                    print("Invalid input. Please enter numbers separated by commas or 'none'")
                except KeyboardInterrupt:
                    return []

def setup_logging(verbose=False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(__name__)

class CSVValidationError(Exception):
    """Custom exception for CSV validation errors."""
    pass

class BitwandenCSVValidator:
    """Validator for Bitwarden CSV exports."""
    
    REQUIRED_COLUMNS = ['login_uri', 'login_username']
    OPTIONAL_COLUMNS = ['folder', 'favorite', 'type', 'name', 'notes', 'fields', 
                       'reprompt', 'login_password', 'login_totp']
    
    @staticmethod
    def validate_file_exists(csv_file_path):
        """Validate that the CSV file exists and is readable."""
        path = Path(csv_file_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {csv_file_path}")
        if path.stat().st_size == 0:
            raise ValueError(f"CSV file is empty: {csv_file_path}")
        return True
    
    @staticmethod
    def validate_csv_structure(df, logger=None):
        """Validate CSV structure and content."""
        errors = []
        warnings = []
        
        # Check if DataFrame is empty
        if df.empty:
            errors.append("CSV file contains no data rows")
        
        # Check for required columns
        missing_required = [col for col in BitwandenCSVValidator.REQUIRED_COLUMNS 
                           if col not in df.columns]
        if missing_required:
            errors.append(f"Missing required columns: {missing_required}")
        
        # Check for suspicious column names (might indicate wrong CSV format)
        expected_cols = set(BitwandenCSVValidator.REQUIRED_COLUMNS + BitwandenCSVValidator.OPTIONAL_COLUMNS)
        actual_cols = set(df.columns)
        unexpected_cols = actual_cols - expected_cols
        
        if len(unexpected_cols) > len(actual_cols) * 0.5:  # More than 50% unexpected
            warnings.append(f"Many unexpected columns found: {list(unexpected_cols)[:5]}... "
                          f"This might not be a Bitwarden CSV export")
        
        # Check for completely empty columns
        empty_cols = [col for col in df.columns if df[col].isna().all()]
        if empty_cols:
            warnings.append(f"Completely empty columns found: {empty_cols}")
        
        # Check data quality in required columns
        if 'login_uri' in df.columns:
            empty_uris = df['login_uri'].isna().sum()
            if empty_uris > 0:
                warnings.append(f"{empty_uris} entries have empty login_uri")
                
        if 'login_username' in df.columns:
            empty_usernames = df['login_username'].isna().sum()
            if empty_usernames > 0:
                warnings.append(f"{empty_usernames} entries have empty login_username")
        
        # Log findings
        if logger:
            if errors:
                for error in errors:
                    logger.error(f"CSV Validation Error: {error}")
            if warnings:
                for warning in warnings:
                    logger.warning(f"CSV Validation Warning: {warning}")
        
        # Print critical issues
        if errors:
            print("❌ CSV Validation Errors:")
            for error in errors:
                print(f"   • {error}")
        
        if warnings:
            print("⚠️  CSV Validation Warnings:")
            for warning in warnings:
                print(f"   • {warning}")
        
        if errors:
            raise CSVValidationError(f"CSV validation failed: {'; '.join(errors)}")
        
        return len(warnings) == 0  # Return True if no warnings

def validate_csv_file(csv_file_path, logger=None):
    """Validate CSV file exists and has proper structure."""
    try:
        # Check file existence
        BitwandenCSVValidator.validate_file_exists(csv_file_path)
        
        # Try to read and validate structure
        df = pd.read_csv(csv_file_path, nrows=100)  # Read sample for validation
        BitwandenCSVValidator.validate_csv_structure(df, logger)
        
        if logger:
            logger.info(f"CSV validation passed for: {csv_file_path}")
        
        return True
        
    except (FileNotFoundError, ValueError, CSVValidationError) as e:
        if logger:
            logger.error(f"CSV validation failed: {e}")
        raise
    except Exception as e:
        error_msg = f"Unexpected error during CSV validation: {e}"
        if logger:
            logger.error(error_msg)
        raise CSVValidationError(error_msg)

def get_file_size_mb(file_path):
    """Get file size in megabytes."""
    return Path(file_path).stat().st_size / (1024 * 1024)

def read_csv_and_print_columns(csv_file_path, logger=None):
    """Read CSV file and display column information."""
    try:
        validate_csv_file(csv_file_path)
        
        # Check file size for memory optimization warning
        file_size_mb = get_file_size_mb(csv_file_path)
        if file_size_mb > 100:
            warning_msg = f"Large file detected ({file_size_mb:.1f}MB). Consider using automatic mode for better performance."
            if logger:
                logger.warning(warning_msg)
            print(f"⚠️  WARNING: {warning_msg}")
        
        # For very large files, just read a sample to get columns
        if file_size_mb > 500:
            df_sample = pd.read_csv(csv_file_path, nrows=100)
            # Get total row count more efficiently
            with open(csv_file_path, 'r', encoding='utf-8') as f:
                total_rows = sum(1 for _ in f) - 1  # Subtract header
            
            if logger:
                logger.info(f"Large file: {total_rows} rows estimated, {len(df_sample.columns)} columns")
            print(f"📊 Large file detected: ~{total_rows:,} rows (estimated)")
            
            print("Column names:")
            for i, column in enumerate(df_sample.columns, 1):
                print(f"{i}. {column}")
            
            return df_sample.columns.tolist()
        
        else:
            if TQDM_AVAILABLE and get_file_size_mb(csv_file_path) > 10:
                print("📁 Loading large CSV file...")
                df = pd.read_csv(csv_file_path)
                print(f"✅ Loaded {len(df):,} rows successfully")
            else:
                df = pd.read_csv(csv_file_path)
            
            if logger:
                logger.info(f"Successfully loaded CSV with {len(df)} rows and {len(df.columns)} columns")
            
            print("Column names:")
            for i, column in enumerate(df.columns, 1):
                print(f"{i}. {column}")
            
            return df.columns.tolist()
    except FileNotFoundError as e:
        error_msg = f"File not found: {csv_file_path}"
        if logger:
            logger.error(error_msg)
        print(f"Error: {error_msg}")
        return None
    except pd.errors.EmptyDataError:
        error_msg = f"CSV file is empty or invalid: {csv_file_path}"
        if logger:
            logger.error(error_msg)
        print(f"Error: {error_msg}")
        return None
    except Exception as e:
        error_msg = f"Error reading CSV file: {e}"
        if logger:
            logger.error(error_msg)
        print(f"Error: {error_msg}")
        return None

def find_duplicate_login_uris(csv_file_path, logger=None):
    """Find rows with duplicate login_uri values."""
    try:
        validate_csv_file(csv_file_path)
        df = pd.read_csv(csv_file_path)
        
        if 'login_uri' not in df.columns:
            error_msg = "'login_uri' column not found in the CSV file"
            if logger:
                logger.error(error_msg)
            print(f"Error: {error_msg}.")
            return []
        
        duplicate_rows = df[df.duplicated(subset=['login_uri'], keep=False)]
        
        if duplicate_rows.empty:
            message = "No duplicate login_uri entries found"
            if logger:
                logger.info(message)
            print(f"{message}.")
            return []
        
        message = f"Found {len(duplicate_rows)} rows with duplicate login_uri values"
        if logger:
            logger.info(message)
        print(f"{message}.")
        print("(Row details hidden for security - use interactive mode to see specific entries)")
        
        return duplicate_rows.to_dict('records')
        
    except FileNotFoundError as e:
        error_msg = f"File not found: {csv_file_path}"
        if logger:
            logger.error(error_msg)
        print(f"Error: {error_msg}")
        return []
    except Exception as e:
        error_msg = f"Error processing CSV file: {e}"
        if logger:
            logger.error(error_msg)
        print(f"Error: {error_msg}")
        return []

def find_duplicate_uri_and_username(csv_file_path, logger=None):
    try:
        df = pd.read_csv(csv_file_path)
        
        required_columns = ['login_uri', 'login_username']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"Error: Missing columns: {missing_columns}")
            return []
        
        duplicate_uri_rows = df[df.duplicated(subset=['login_uri'], keep=False)]
        
        if duplicate_uri_rows.empty:
            print("No duplicate login_uri entries found.")
            return []
        
        duplicate_uri_and_username = duplicate_uri_rows[
            duplicate_uri_rows.duplicated(subset=['login_uri', 'login_username'], keep=False)
        ]
        
        if duplicate_uri_and_username.empty:
            print("No rows found with duplicate login_uri AND login_username combinations.")
            return []
        
        print(f"Found {len(duplicate_uri_and_username)} rows with duplicate login_uri AND login_username.")
        print("(Row details hidden for security - use deletion options to see specific entries)")
        
        return duplicate_uri_and_username.to_dict('records')
        
    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
        return []
    except Exception as e:
        print(f"Error processing CSV file: {e}")
        return []

def remove_fully_duplicate_rows(df, logger=None):
    """Remove rows that are completely identical across all columns, keeping only one copy."""
    original_count = len(df)
    
    # Remove fully duplicate rows (keep='first' keeps the first occurrence)
    if TQDM_AVAILABLE and len(df) > 1000:
        with tqdm(total=1, desc="Removing duplicate rows") as pbar:
            df_no_full_dupes = df.drop_duplicates(keep='first')
            pbar.update(1)
    else:
        df_no_full_dupes = df.drop_duplicates(keep='first')
    
    removed_count = original_count - len(df_no_full_dupes)
    
    if removed_count > 0:
        message = f"Automatically removed {removed_count} fully duplicate rows (identical across all columns)"
        if logger:
            logger.info(message)
        print(f"\n{message}")
        print(f"Rows remaining: {len(df_no_full_dupes)}")
    else:
        message = "No fully duplicate rows found"
        if logger:
            logger.info(message)
        print(f"\n{message}.")
    
    return df_no_full_dupes, removed_count

def normalize_urls(df, logger=None):
    """Normalize login_uri by removing trailing slashes and creating a normalized column for comparison."""
    # Memory efficient: modify in place instead of copying when possible
    if 'login_uri' in df.columns:
        # Create a normalized version for comparison (remove trailing slashes)
        if TQDM_AVAILABLE and len(df) > 5000:
            tqdm.pandas(desc="Normalizing URLs")
            df['login_uri_normalized'] = df['login_uri'].astype(str).progress_apply(lambda x: str(x).rstrip('/'))
        else:
            df['login_uri_normalized'] = df['login_uri'].astype(str).str.rstrip('/')
        message = "URLs normalized (trailing slashes removed for duplicate detection)"
        if logger:
            logger.info(message)
        print(message)
    
    return df

def extract_domain(url):
    """Extract domain from URL with validation."""
    try:
        if pd.isna(url) or url == '':
            return ''
        
        url_str = str(url).strip()
        
        # Check if it's likely an IP address (better handling for IPs with ports/paths)
        import re
        # Extract just the host part for IP checking
        host_part = url_str.split('/')[0]
        # Handle IP addresses with ports (e.g., 192.168.1.1:8080)
        ip_pattern = r'^(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?$'
        if re.match(ip_pattern, host_part):
            return host_part  # Return IP with port as is
        
        # Handle IPv6 addresses (basic check for brackets)
        if '[' in host_part and ']' in host_part:
            return host_part  # Return IPv6 as is
        
        # Only add http:// if it looks like a domain/URL (improved validation)
        if not url_str.startswith(('http://', 'https://', 'ftp://', 'file://')):
            # Better validation for URL patterns
            if ('.' in url_str and not url_str.endswith('.')) or any(keyword in url_str.lower() for keyword in ['localhost', 'api', 'www', 'app', 'portal']):
                url_str = 'http://' + url_str
            else:
                # Return original if it doesn't look like a URL
                return url_str.lower()
            
        parsed = urlparse(url_str)
        domain = parsed.netloc.lower()
        
        # Validate domain is not empty and reasonable
        if not domain:
            return str(url).lower()  # Return original if domain extraction failed
        
        # Handle special cases: localhost, IP addresses, and valid single-word domains
        if domain in ['localhost'] or re.match(ip_pattern, domain) or '[' in domain:
            return domain  # Keep as is for special cases
        
        # For regular domains, ensure they have a dot (except localhost)
        if '.' not in domain:
            return str(url).lower()  # Return original if no dot in domain
        
        # Remove 'www.' prefix if present
        if domain.startswith('www.'):
            domain = domain[4:]
            
        # Improved validation: ensure domain has valid characters and structure
        # Allow letters, numbers, dots, hyphens, and underscores (common in internal domains)
        if not re.match(r'^[a-zA-Z0-9._-]+$', domain):
            return str(url).lower()  # Return original if domain has invalid characters
        
        # Basic check: domain should not start or end with dot/hyphen
        if domain.startswith(('.', '-')) or domain.endswith(('.', '-')):
            return str(url).lower()  # Return original if malformed
            
        return domain
    except Exception:
        return str(url).lower()  # Fallback to original URL if parsing fails

def add_domain_column(df):
    """Add domain column extracted from login_uri_normalized."""
    # Memory efficient: modify in place
    if 'login_uri_normalized' in df.columns:
        if TQDM_AVAILABLE and len(df) > 1000:
            tqdm.pandas(desc="Extracting domains")
            df['domain'] = df['login_uri_normalized'].progress_apply(extract_domain)
        else:
            df['domain'] = df['login_uri_normalized'].apply(extract_domain)
        print("Domain column added for duplicate detection")
    
    return df

def clean_name_column(df, logger=None):
    """Clean the name column by removing text in parentheses and extra whitespace."""
    if 'name' not in df.columns:
        if logger:
            logger.info("No 'name' column found to clean")
        return df
    
    # Count entries that will be cleaned
    if TQDM_AVAILABLE and len(df) > 5000:
        with tqdm(total=1, desc="Checking name column") as pbar:
            entries_with_parentheses = df['name'].str.contains(r'\([^)]*\)', na=False).sum()
            pbar.update(1)
    else:
        entries_with_parentheses = df['name'].str.contains(r'\([^)]*\)', na=False).sum()
    
    if entries_with_parentheses == 0:
        if logger:
            logger.info("No entries with parentheses found in name column")
        print("No parentheses found in name column to clean")
        return df
    
    # Clean the name column
    if TQDM_AVAILABLE and len(df) > 5000:
        with tqdm(total=2, desc="Cleaning name column") as pbar:
            # Remove everything in parentheses including the parentheses themselves
            df['name'] = df['name'].str.replace(r'\s*\([^)]*\)\s*', '', regex=True)
            pbar.update(1)
            
            # Clean up any double spaces and strip whitespace
            df['name'] = df['name'].str.replace(r'\s+', ' ', regex=True).str.strip()
            pbar.update(1)
    else:
        # Remove everything in parentheses including the parentheses themselves
        df['name'] = df['name'].str.replace(r'\s*\([^)]*\)\s*', '', regex=True)
        
        # Clean up any double spaces and strip whitespace
        df['name'] = df['name'].str.replace(r'\s+', ' ', regex=True).str.strip()
    
    message = f"Cleaned {entries_with_parentheses} entries in name column (removed parentheses content)"
    if logger:
        logger.info(message)
    print(f"✓ {message}")
    
    return df

def interactive_delete_duplicates(csv_file_path, logger=None, show_passwords=False):
    """Interactive deletion with arrow key navigation, matching only on base URI."""
    try:
        df = pd.read_csv(csv_file_path)
        original_count = len(df)
        
        print("\n🔍 INTERACTIVE DUPLICATE CLEANUP")
        print("Now matching only on base URI (ignoring username/password)")
        print("This allows you to clean up old/inactive accounts for the same service")
        
        # First, automatically remove fully duplicate rows
        print("\n" + "=" * 50)
        print("STEP 1: Removing fully duplicate rows")
        print("=" * 50)
        df, fully_removed_count = remove_fully_duplicate_rows(df, logger)
        
        # Normalize URLs for better duplicate detection
        print("\n" + "=" * 50)
        print("STEP 1.5: Normalizing URLs and cleaning names")
        print("=" * 50)
        df = normalize_urls(df, logger)
        df = clean_name_column(df, logger)
        
        required_columns = ['login_uri']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"Error: Missing columns: {missing_columns}")
            return None
        
        # Find rows with duplicate login_uri (base URI only - changed from username+URI)
        duplicate_uri_rows = df[df.duplicated(subset=['login_uri_normalized'], keep=False)]
        
        if duplicate_uri_rows.empty:
            print("\nNo duplicate base URIs found after removing fully duplicate rows.")
            if fully_removed_count > 0:
                print(f"Total cleanup: {fully_removed_count} fully duplicate rows removed.")
            # Clean up temporary columns
            df_cleaned = df.drop(columns=['login_uri_normalized'], errors='ignore')
            return df_cleaned
        
        print("\n" + "=" * 50)
        print("STEP 2: Interactive URI-based duplicate cleanup")
        print("=" * 50)
        print(f"Found {len(duplicate_uri_rows)} rows with duplicate base URIs")
        print("You'll be able to review each group and select accounts to remove")
        
        rows_to_delete = []
        # Group by normalized login_uri only (removed username grouping)
        unique_uris = duplicate_uri_rows['login_uri_normalized'].drop_duplicates()
        
        print(f"\n📊 Processing {len(unique_uris)} unique base URIs with duplicates...")
        
        # Process each URI group
        total_groups = len(unique_uris)
        current_group = 0
        
        for uri_normalized in unique_uris:
            current_group += 1
            
            # Get all rows with this specific normalized login_uri
            uri_group = df[df['login_uri_normalized'] == uri_normalized].copy()
            
            if len(uri_group) < 2:  # Skip if only one entry
                continue
            
            # Create group info for display
            group_info = f"Base URI: {uri_normalized} ({current_group}/{total_groups})"
            
            # Use new interactive selection interface
            selected_indices = interactive_select_entries(uri_group, group_info, show_passwords)
            
            # Check for quit signal
            if selected_indices == 'QUIT_ALL':
                print("\n\n🚪 Exiting interactive mode...")
                print(f"📊 Processed {current_group-1} of {total_groups} groups before exit")
                break
            
            # Add selected indices to deletion list
            rows_to_delete.extend(selected_indices)
        
        # Process deletions
        if rows_to_delete:
            # Get deleted entries before dropping them
            deleted_df = df.loc[rows_to_delete].copy()
            
            df_cleaned = df.drop(rows_to_delete)
            df_cleaned.reset_index(drop=True, inplace=True)
            
            # Remove the temporary columns from final output
            df_cleaned = df_cleaned.drop(columns=['login_uri_normalized'], errors='ignore')
            deleted_df = deleted_df.drop(columns=['login_uri_normalized'], errors='ignore')
            
            # Save deleted entries
            save_deleted_entries(deleted_df, csv_file_path)
            
            # Final summary
            os.system('clear' if os.name == 'posix' else 'cls')
            print("✅ CLEANUP COMPLETE!")
            print("=" * 50)
            print(f"📊 SUMMARY:")
            print("=" * 50)
            print(f"Original rows: {original_count:,}")
            print(f"Fully duplicate rows removed: {fully_removed_count:,}")
            print(f"URI-based duplicates deleted: {len(rows_to_delete):,}")
            print(f"Total rows removed: {fully_removed_count + len(rows_to_delete):,}")
            print(f"Remaining rows: {len(df_cleaned):,}")
            print()
            print("🎉 Your password database has been cleaned!")
            
            return df_cleaned
        else:
            print("\n📋 No rows selected for deletion.")
            if fully_removed_count > 0:
                print(f"Total cleanup: {fully_removed_count} fully duplicate rows removed.")
            
            # Remove temporary columns
            df_cleaned = df.drop(columns=['login_uri_normalized'], errors='ignore')
            return df_cleaned
            
    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
        return None
    except KeyboardInterrupt:
        print("\n\n❌ Operation cancelled by user.")
        return None
    except Exception as e:
        print(f"Error processing CSV file: {e}")
        return None

def automatic_delete_duplicates(csv_file_path, logger=None, dry_run=False):
    """Automatically delete duplicate login_uri + login_username combinations, keeping only the first occurrence."""
    try:
        df = pd.read_csv(csv_file_path)
        original_count = len(df)
        
        if dry_run:
            print("\n🔍 DRY RUN MODE: Previewing changes without modification\n")
        
        # First, automatically remove fully duplicate rows
        print("\n" + "=" * 50)
        print("STEP 1: Removing fully duplicate rows")
        print("=" * 50)
        if dry_run:
            df_temp, fully_removed_count = remove_fully_duplicate_rows(df.copy(), logger)
            print(f"DRY RUN: Would remove {fully_removed_count} fully duplicate rows")
        else:
            df, fully_removed_count = remove_fully_duplicate_rows(df, logger)
        
        # Normalize URLs for better duplicate detection
        print("\n" + "=" * 50)
        print("STEP 1.5: Normalizing URLs and cleaning names")
        print("=" * 50)
        if dry_run:
            df_temp = normalize_urls(df_temp, logger)
            df_temp = clean_name_column(df_temp, logger)
            working_df = df_temp
        else:
            df = normalize_urls(df, logger)
            df = clean_name_column(df, logger)
            working_df = df
        
        required_columns = ['login_uri', 'login_username']
        missing_columns = [col for col in required_columns if col not in working_df.columns]
        
        if missing_columns:
            print(f"Error: Missing columns: {missing_columns}")
            return None, None
        
        # Find rows with duplicate login_uri AND login_username combinations (using normalized URLs)
        duplicate_uri_username_rows = working_df[working_df.duplicated(subset=['login_uri_normalized', 'login_username'], keep=False)]
        
        if duplicate_uri_username_rows.empty:
            print("\nNo remaining duplicate login_uri + login_username combinations found after removing fully duplicate rows.")
            if fully_removed_count > 0:
                if dry_run:
                    print(f"DRY RUN: Would clean {fully_removed_count} fully duplicate rows total.")
                else:
                    print(f"Total cleanup: {fully_removed_count} fully duplicate rows removed.")
            return df, pd.DataFrame()  # Return empty DataFrame for deleted rows
        
        print("\n" + "=" * 50)
        print("STEP 2: Automatic partial duplicate cleanup")
        print("=" * 50)
        print(f"Found {len(duplicate_uri_username_rows)} rows with duplicate login_uri + login_username combinations")
        
        # Keep only the shortest URI for each normalized login_uri + login_username combination
        def keep_shortest_uri_auto(group):
            # Memory efficient: find shortest without creating extra columns
            min_length_idx = group['login_uri_normalized'].str.len().idxmin()
            return group.loc[[min_length_idx]]
        
        # Group by normalized URI + username and apply the shortest URI selection
        df_cleaned = working_df.groupby(['login_uri_normalized', 'login_username'], group_keys=False).apply(keep_shortest_uri_auto).reset_index(drop=True)
        
        # Find the rows that were removed
        removed_indices = set(working_df.index) - set(df_cleaned.index)
        deleted_rows = working_df.loc[list(removed_indices)]
        
        partial_removed_count = len(deleted_rows)
        
        if dry_run:
            print(f"DRY RUN: Would remove {partial_removed_count} duplicate login_uri + login_username entries (kept shortest URI)")
        else:
            print(f"Automatically removed {partial_removed_count} duplicate login_uri + login_username entries (kept shortest URI)")
        
        # Remove the normalized column from final output (it was just for comparison)
        if 'login_uri_normalized' in df_cleaned.columns:
            df_cleaned = df_cleaned.drop('login_uri_normalized', axis=1)
        if 'login_uri_normalized' in deleted_rows.columns:
            deleted_rows = deleted_rows.drop('login_uri_normalized', axis=1)
        
        print(f"\n{'='*50}")
        if dry_run:
            print(f"DRY RUN SUMMARY:")
        else:
            print(f"SUMMARY:")
        print(f"{'='*50}")
        print(f"Original rows: {original_count}")
        if dry_run:
            print(f"Fully duplicate rows would be removed: {fully_removed_count}")
            print(f"Partial duplicate rows would be removed: {partial_removed_count}")
            print(f"Total rows would be removed: {fully_removed_count + partial_removed_count}")
            print(f"Rows would remain: {len(df_cleaned)}")
            print(f"\n🔍 This was a DRY RUN - no changes were made to your data.")
            return df, pd.DataFrame()  # Return original data unchanged
        else:
            print(f"Fully duplicate rows removed: {fully_removed_count}")
            print(f"Partial duplicate rows removed: {partial_removed_count}")
            print(f"Total rows removed: {fully_removed_count + partial_removed_count}")
            print(f"Remaining rows: {len(df_cleaned)}")
            return df_cleaned, deleted_rows
        
    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
        return None, None
    except Exception as e:
        print(f"Error processing CSV file: {e}")
        return None, None

def create_backup(original_path, logger=None):
    """Create a backup of the original file before any modifications."""
    try:
        # Validate original file exists
        if not Path(original_path).exists():
            raise FileNotFoundError(f"Original file not found: {original_path}")
        
        base_name = original_path.rsplit('.', 1)[0]
        extension = original_path.rsplit('.', 1)[1] if '.' in original_path else 'csv'
        
        # Add timestamp to backup files
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{base_name}_backup_{timestamp}.{extension}"
        
        # Create backup using shutil for better file handling
        shutil.copy2(original_path, backup_path)
        
        message = f"Original file backed up to: {backup_path}"
        if logger:
            logger.info(message)
        print(f"💾 {message}")
        
        return backup_path
        
    except Exception as e:
        error_msg = f"Error creating backup: {e}"
        if logger:
            logger.error(error_msg)
        print(f"❌ {error_msg}")
        return None

def save_deleted_entries(deleted_df, original_path):
    """Save deleted entries to a backup file."""
    if deleted_df is None or deleted_df.empty:
        print("No deleted entries to save.")
        return None
    
    base_name = original_path.rsplit('.', 1)[0]
    extension = original_path.rsplit('.', 1)[1] if '.' in original_path else 'csv'
    
    # Add timestamp to backup files for multiple backups
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    deleted_path = f"{base_name}_deleted_entries_{timestamp}.{extension}"
    
    try:
        deleted_df.to_csv(deleted_path, index=False)
        print(f"Deleted entries saved to: {deleted_path}")
        return deleted_path
    except Exception as e:
        print(f"Error saving deleted entries: {e}")
        return None

def list_backup_files(original_path):
    """List available backup files for the given original file."""
    base_name = original_path.rsplit('.', 1)[0]
    extension = original_path.rsplit('.', 1)[1] if '.' in original_path else 'csv'
    
    # Look for backup patterns
    backup_patterns = [
        f"{base_name}_backup_*.{extension}",
        f"{base_name}_deleted_entries_*.{extension}",
        f"{base_name}_cleaned.{extension}"
    ]
    
    backup_files = []
    
    for pattern in backup_patterns:
        matches = glob(pattern)
        backup_files.extend(matches)
    
    if not backup_files:
        print(f"No backup files found for: {original_path}")
        return []
    
    print(f"\n💾 Available backup files for {original_path}:")
    print("=" * 60)
    
    backup_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    for i, backup_file in enumerate(backup_files, 1):
        file_path = Path(backup_file)
        size_mb = file_path.stat().st_size / (1024 * 1024)
        mod_time = datetime.datetime.fromtimestamp(file_path.stat().st_mtime)
        
        if "backup_" in backup_file:
            file_type = "Original file backup"
        elif "deleted_entries" in backup_file:
            file_type = "Deleted entries backup"
        elif "cleaned" in backup_file:
            file_type = "Cleaned data file"
        else:
            file_type = "Backup file"
        
        print(f"{i:2d}. {file_path.name}")
        print(f"    Type: {file_type}")
        print(f"    Size: {size_mb:.1f} MB")
        print(f"    Modified: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    return backup_files

def restore_from_backup(original_path, backup_file=None, interactive=True):
    """Restore data from backup files."""
    backup_files = list_backup_files(original_path)
    
    if not backup_files:
        return False
    
    if backup_file:
        # Specific backup file provided
        if backup_file not in backup_files:
            print(f"❌ Error: Backup file not found: {backup_file}")
            return False
        selected_backup = backup_file
    elif interactive:
        # Interactive selection
        print("\n🔄 Select backup file to restore:")
        while True:
            try:
                choice = input(f"Enter backup number (1-{len(backup_files)}) or 'q' to quit: ").strip()
                if choice.lower() == 'q':
                    print("Restore cancelled.")
                    return False
                
                backup_index = int(choice) - 1
                if 0 <= backup_index < len(backup_files):
                    selected_backup = backup_files[backup_index]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(backup_files)}")
            except ValueError:
                print("Invalid input. Please enter a number or 'q' to quit.")
    else:
        # Non-interactive: use most recent backup
        selected_backup = backup_files[0]
    
    # Determine restore type and method
    base_name = original_path.rsplit('.', 1)[0]
    extension = original_path.rsplit('.', 1)[1] if '.' in original_path else 'csv'
    
    if "deleted_entries" in selected_backup:
        # This is a deleted entries backup - need to merge with current cleaned file
        cleaned_file = f"{base_name}_cleaned.{extension}"
        
        if not Path(cleaned_file).exists():
            print(f"❌ Error: Cleaned file not found: {cleaned_file}")
            print("Cannot restore deleted entries without the cleaned file.")
            return False
        
        print(f"\n🔄 Restoring deleted entries from: {Path(selected_backup).name}")
        print(f"Merging with cleaned file: {Path(cleaned_file).name}")
        
        try:
            # Read both files
            deleted_df = pd.read_csv(selected_backup)
            cleaned_df = pd.read_csv(cleaned_file)
            
            # Combine them
            restored_df = pd.concat([cleaned_df, deleted_df], ignore_index=True)
            
            # Create restoration file
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            restore_path = f"{base_name}_restored_{timestamp}.{extension}"
            
            restored_df.to_csv(restore_path, index=False)
            
            print(f"✅ Successfully restored {len(deleted_df)} deleted entries")
            print(f"Combined {len(cleaned_df)} cleaned + {len(deleted_df)} deleted = {len(restored_df)} total entries")
            print(f"Restored data saved to: {restore_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during restoration: {e}")
            return False
    
    elif "backup_" in selected_backup:
        # This is an original file backup - copy it back to original location
        print(f"\n🔄 Restoring original file from: {Path(selected_backup).name}")
        
        # Ask for confirmation before overwriting
        if Path(original_path).exists():
            print(f"⚠️  Warning: This will overwrite the current file: {original_path}")
            if interactive:
                confirm = input("Continue? (y/N): ").strip().lower()
                if confirm != 'y':
                    print("Restore cancelled.")
                    return False
        
        try:
            # Copy the backup to original location
            shutil.copy2(selected_backup, original_path)
            
            print(f"✅ Successfully restored original file to: {original_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error during restoration: {e}")
            return False
    
    elif "cleaned" in selected_backup:
        # This is a cleaned file - copy it back to original location
        print(f"\n🔄 Restoring cleaned file: {Path(selected_backup).name}")
        
        # Ask for confirmation before overwriting
        if Path(original_path).exists():
            print(f"⚠️  Warning: This will overwrite the existing file: {original_path}")
            if interactive:
                confirm = input("Continue? (y/N): ").strip().lower()
                if confirm != 'y':
                    print("Restore cancelled.")
                    return False
        
        try:
            # Copy the backup to original location
            shutil.copy2(selected_backup, original_path)
            
            print(f"✅ Successfully restored file to: {original_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error during restoration: {e}")
            return False
    
    else:
        print(f"❌ Error: Unknown backup file type: {selected_backup}")
        return False

def find_partial_uri_matches(df):
    """Find rows with partial URI matches but same username and password."""
    required_columns = ['login_uri_normalized', 'login_username', 'login_password']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        print(f"Warning: Cannot check partial URI matches. Missing columns: {missing_columns}")
        return []
    
    # Group by username and password combinations
    credential_groups = df.groupby(['login_username', 'login_password'])
    
    partial_match_groups = []
    
    for (username, password), group in credential_groups:
        if len(group) > 1:  # More than one entry with same credentials
            unique_uris = group['login_uri_normalized'].unique()
            if len(unique_uris) > 1:  # Different URIs for same credentials
                # Check if URIs are partial matches (one contains the other)
                potential_matches = []
                for i, uri1 in enumerate(unique_uris):
                    for j, uri2 in enumerate(unique_uris):
                        if i != j and (uri1 in uri2 or uri2 in uri1):
                            potential_matches.append((uri1, uri2))
                
                if potential_matches:
                    partial_match_groups.append({
                        'username': username,
                        'password': password,
                        'group': group,
                        'uris': unique_uris,
                        'matches': potential_matches
                    })
    
    return partial_match_groups

def automatic_domain_cleanup(csv_file_path, logger=None, dry_run=False):
    """Automatically clean up entries with same domain + username, keeping only the first occurrence."""
    try:
        df = pd.read_csv(csv_file_path)
        original_count = len(df)
        
        if dry_run:
            print("\n🔍 DRY RUN MODE: Previewing changes without modification\n")
        
        # Normalize URLs and extract domains
        print("\n" + "=" * 60)
        print("DOMAIN-BASED DUPLICATE CLEANUP")
        print("=" * 60)
        
        # Work on a copy for dry run
        working_df = df.copy() if dry_run else df
        working_df = normalize_urls(working_df, logger)
        working_df = clean_name_column(working_df, logger)
        working_df = add_domain_column(working_df)
        
        required_columns = ['login_uri', 'login_username', 'login_password']
        missing_columns = [col for col in required_columns if col not in working_df.columns]
        
        if missing_columns:
            print(f"Error: Missing columns for domain cleanup: {missing_columns}")
            return None, None
        
        # Check if we have domain column
        if 'domain' not in working_df.columns:
            print("Error: Domain extraction failed.")
            return None, None
        
        print("Looking for entries with same domain + username + password combinations...")
        
        # Find duplicates based on domain + username + password
        domain_credentials_duplicates = working_df[working_df.duplicated(subset=['domain', 'login_username', 'login_password'], keep=False)]
        
        if domain_credentials_duplicates.empty:
            print("No duplicate domain + username + password combinations found.")
            # Clean up temporary columns
            df_cleaned = working_df.drop(['login_uri_normalized', 'domain'], axis=1, errors='ignore')
            return df, pd.DataFrame()  # Return original data for dry run
        
        print(f"Found {len(domain_credentials_duplicates)} rows with duplicate domain + username + password combinations")
        
        # Show summary of what will be cleaned
        unique_combinations = domain_credentials_duplicates[['domain', 'login_username', 'login_password']].drop_duplicates()
        action_word = "Would clean" if dry_run else "Will clean"
        print(f"\n{action_word} {len(unique_combinations)} unique domain + username + password combinations:")
        
        total_to_remove = 0
        combo_iterator = tqdm(unique_combinations.iterrows(), 
                             total=len(unique_combinations), 
                             desc="Analyzing combinations") if TQDM_AVAILABLE and len(unique_combinations) > 50 else unique_combinations.iterrows()
        
        for _, combo in combo_iterator:
            domain = combo['domain']
            username = combo['login_username']
            password_masked = '*' * len(str(combo['login_password']))  # Mask password for security
            count = len(working_df[(working_df['domain'] == domain) & (working_df['login_username'] == username) & (working_df['login_password'] == combo['login_password'])])
            total_to_remove += (count - 1)  # Will keep 1, remove others
            action_word = "would keep" if dry_run else "keep"
            print(f"  - Domain: {domain}, Username: {username}, Password: {password_masked} ({count} entries → {action_word} 1, remove {count-1})")
        
        action_word = "Would remove" if dry_run else "Will remove"
        print(f"\nSUMMARY: {action_word} {total_to_remove} entries total, keeping shortest URI for each domain + username + password combination.")
        
        # Add data loss warnings
        print("\n" + "⚠️" * 50)
        print("⚠️  DATA LOSS WARNING")
        print("⚠️" * 50)
        print("This operation will PERMANENTLY DELETE entries from your dataset!")
        print("What will be deleted:")
        print("  • Longer URLs (keeps shortest URL for each credential set)")
        print("  • URL paths, parameters, and specific endpoints")
        print("  • Backup entries for the same login credentials")
        print("\nWhat will be PRESERVED:")
        print("  ✓ One entry per unique domain + username + password combination")
        print("  ✓ The shortest/base URL for each credential set")
        print("  ✓ All entries with different passwords (even same domain + username)")
        print("\nDeleted entries will be saved to a backup file for recovery.")
        
        # Show preview of what will be deleted
        print(f"\n{'='*60}")
        print("PREVIEW: DATA TO BE DELETED")
        print(f"{'='*60}")
        
        # Simulate the deletion to show what will be removed
        def preview_shortest_uri(group):
            min_length_idx = group['login_uri_normalized'].str.len().idxmin()
            return group.loc[[min_length_idx]]
        
        # Get what would be kept
        preview_kept = df.groupby(['domain', 'login_username', 'login_password'], group_keys=False).apply(preview_shortest_uri).reset_index(drop=True)
        preview_deleted_indices = set(df.index) - set(preview_kept.index)
        preview_deleted = df.loc[list(preview_deleted_indices)]
        
        if len(preview_deleted) <= 10:
            # Show all deleted entries if 10 or fewer
            print("All entries that will be DELETED:")
            for idx, row in preview_deleted.iterrows():
                print(f"\n  Row {idx + 1}:")
                print(f"    URI: {row['login_uri']}")
                print(f"    Username: {row['login_username']}")
                print(f"    Password: {'*' * len(str(row['login_password']))}")
                if 'name' in row:
                    print(f"    Name: {row['name']}")
        else:
            # Show first 5 and last 5 if more than 10
            print("Sample of entries that will be DELETED (showing first 5 and last 5):")
            preview_sample = pd.concat([preview_deleted.head(5), preview_deleted.tail(5)])
            for idx, row in preview_sample.iterrows():
                print(f"\n  Row {idx + 1}:")
                print(f"    URI: {row['login_uri']}")
                print(f"    Username: {row['login_username']}")
                print(f"    Password: {'*' * len(str(row['login_password']))}")
                if 'name' in row:
                    print(f"    Name: {row['name']}")
            if len(preview_deleted) > 10:
                print(f"\n  ... and {len(preview_deleted) - 10} more entries")
        
        print(f"\n{'='*60}")
        print("PREVIEW: DATA TO BE KEPT")
        print(f"{'='*60}")
        
        if len(preview_kept) <= 5:
            print("All entries that will be KEPT (shortest URLs):")
            for idx, row in preview_kept.iterrows():
                print(f"\n  Row {idx + 1}:")
                print(f"    URI: {row['login_uri']}")
                print(f"    Username: {row['login_username']}")
                print(f"    Password: {'*' * len(str(row['login_password']))}")
                if 'name' in row:
                    print(f"    Name: {row['name']}")
        else:
            print("Sample of entries that will be KEPT (showing first 5):")
            for idx, row in preview_kept.head(5).iterrows():
                print(f"\n  Row {idx + 1}:")
                print(f"    URI: {row['login_uri']}")
                print(f"    Username: {row['login_username']}")
                print(f"    Password: {'*' * len(str(row['login_password']))}")
                if 'name' in row:
                    print(f"    Name: {row['name']}")
            print(f"\n  ... and {len(preview_kept) - 5} more entries will be kept")
        
        if dry_run:
            print(f"\n🔍 DRY RUN COMPLETE: Would delete {total_to_remove} entries and keep {len(working_df) - total_to_remove} entries.")
            print("No changes were made to your data.")
            return df, pd.DataFrame()
        
        # Ask for user confirmation before proceeding
        print(f"\n{'='*60}")
        print("PROCEED WITH DELETION?")
        print(f"{'='*60}")
        print(f"This will delete {total_to_remove} entries and keep {len(working_df) - total_to_remove} entries.")
        confirmation = input("Type 'DELETE' to confirm, or 'n' to cancel: ").strip()
        
        if confirmation.upper() != 'DELETE':
            print("Domain cleanup cancelled by user.")
            # Clean up temporary columns
            df_cleaned = working_df.drop(['login_uri_normalized', 'domain'], axis=1, errors='ignore')
            return df, pd.DataFrame()
        
        print("\nProceeding with domain cleanup...")
        
        # For each domain + username combination, keep the entry with the shortest URI
        def keep_shortest_uri(group):
            # Memory efficient: find shortest without creating extra columns
            min_length_idx = group['login_uri_normalized'].str.len().idxmin()
            return group.loc[[min_length_idx]]
        
        # Group by domain + username + password and apply the shortest URI selection
        df_cleaned = working_df.groupby(['domain', 'login_username', 'login_password'], group_keys=False).apply(keep_shortest_uri).reset_index(drop=True)
        
        # Find the rows that were removed
        removed_indices = set(working_df.index) - set(df_cleaned.index)
        deleted_rows = working_df.loc[list(removed_indices)]
        
        removed_count = len(deleted_rows)
        
        # Clean up temporary columns from final output
        if 'login_uri_normalized' in df_cleaned.columns:
            df_cleaned = df_cleaned.drop('login_uri_normalized', axis=1)
        if 'domain' in df_cleaned.columns:
            df_cleaned = df_cleaned.drop('domain', axis=1)
        
        print(f"\n{'='*50}")
        print(f"DOMAIN CLEANUP SUMMARY:")
        print(f"{'='*50}")
        print(f"Original rows: {original_count}")
        print(f"Rows removed (same domain + username + password, kept shortest URI): {removed_count}")
        print(f"Remaining rows: {len(df_cleaned)}")
        
        return df_cleaned, deleted_rows
        
    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
        return None, None
    except Exception as e:
        print(f"Error processing CSV file: {e}")
        return None, None

def save_cleaned_csv(df, original_path, logger=None):
    if df is None:
        print("No data to save.")
        return
    
    base_name = original_path.rsplit('.', 1)[0]
    extension = original_path.rsplit('.', 1)[1] if '.' in original_path else 'csv'
    new_path = f"{base_name}_cleaned.{extension}"
    
    try:
        df.to_csv(new_path, index=False)
        message = f"Cleaned CSV saved as: {new_path}"
        if logger:
            logger.info(message)
        print(f"\n{message}")
        return new_path
    except Exception as e:
        error_msg = f"Error saving cleaned CSV: {e}"
        if logger:
            logger.error(error_msg)
        print(f"Error: {error_msg}")
        return None

def load_config(config_path=None):
    """Load configuration from file."""
    default_config = {
        'mode': 'analyze',
        'verbose': False,
        'dry_run': False,
        'output': None,
        'show_passwords': False
    }
    
    # Try to find config file
    config_locations = [
        config_path,  # User specified
        os.path.expanduser('~/.clean_pass_config.json'),  # Home directory
        './clean_pass_config.json',  # Current directory
        './.clean_pass.json'  # Alternative name
    ]
    
    for config_file in config_locations:
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                    # Merge user config with defaults
                    config = {**default_config, **user_config}
                    print(f"📄 Loaded configuration from: {config_file}")
                    return config, config_file
            except (json.JSONDecodeError, IOError) as e:
                print(f"⚠️  Warning: Could not load config file {config_file}: {e}")
                continue
    
    return default_config, None

def save_config_template(config_path=None):
    """Save a configuration template file."""
    if not config_path:
        config_path = os.path.expanduser('~/.clean_pass_config.json')
    
    template_config = {
        "_comment": "Configuration file for clean_pass.py - remove this comment line before use",
        "mode": "analyze",
        "verbose": False,
        "dry_run": False,
        "output": None,
        "show_passwords": False,
        "_settings_info": {
            "mode": "Options: analyze, interactive, auto",
            "verbose": "Boolean: true for detailed logging",
            "dry_run": "Boolean: true to preview changes without modifying files",
            "output": "String: custom output file path (null for auto-generated)",
            "show_passwords": "Boolean: true to show passwords in interactive mode (use with caution)"
        }
    }
    
    try:
        with open(config_path, 'w') as f:
            json.dump(template_config, f, indent=2)
        print(f"✅ Configuration template saved to: {config_path}")
        print("Edit this file to set your default preferences.")
        return config_path
    except IOError as e:
        print(f"❌ Error saving config template: {e}")
        return None

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Clean and deduplicate Bitwarden CSV exports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -f export.csv --mode interactive --verbose
  %(prog)s -f export.csv --mode interactive --show-passwords
  %(prog)s -f export.csv --mode auto --dry-run
  %(prog)s -f export.csv --mode analyze
  %(prog)s --save-config  # Create configuration template
  %(prog)s --list-backups export.csv  # Show available backups
  %(prog)s --undo export.csv  # Restore from backups
"""
    )
    
    parser.add_argument(
        '-f', '--file',
        required=True,
        help='Path to the Bitwarden CSV export file'
    )
    
    parser.add_argument(
        '--mode',
        choices=['interactive', 'auto', 'analyze'],
        default='analyze',
        help='Cleaning mode (default: analyze)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without making changes'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--output',
        help='Output file path (default: auto-generated)'
    )
    
    parser.add_argument(
        '--config',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--save-config',
        action='store_true',
        help='Save a configuration file template and exit'
    )
    
    parser.add_argument(
        '--undo',
        help='Restore from backup files (provide original file path)'
    )
    
    parser.add_argument(
        '--list-backups',
        help='List available backup files for the specified CSV file'
    )
    
    parser.add_argument(
        '--show-passwords',
        action='store_true',
        help='Show passwords in interactive mode (use with caution)'
    )
    
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    
    # Handle config template creation
    if args.save_config:
        config_path = args.config if args.config else None
        save_config_template(config_path)
        return
    
    # Handle backup operations
    if args.list_backups:
        list_backup_files(args.list_backups)
        return
    
    if args.undo:
        success = restore_from_backup(args.undo)
        if success:
            print("✅ Restore operation completed successfully.")
        else:
            print("❌ Restore operation failed.")
            sys.exit(1)
        return
    
    # Load configuration
    config, config_file = load_config(args.config)
    
    # Command line arguments override config file settings
    if hasattr(args, 'mode') and args.mode != 'analyze':  # Only override if explicitly set
        config['mode'] = args.mode
    if args.verbose:
        config['verbose'] = True
    if args.dry_run:
        config['dry_run'] = True
    if args.output:
        config['output'] = args.output
    if args.show_passwords:
        config['show_passwords'] = True
    
    # Ensure file argument is always from command line
    if not hasattr(args, 'file') or not args.file:
        print("❌ Error: --file argument is required")
        sys.exit(1)
    
    logger = setup_logging(config['verbose'])
    
    try:
        # Validate input file
        csv_file = args.file
        logger.info(f"Processing file: {csv_file}")
        
        if config_file:
            logger.info(f"Using configuration from: {config_file}")
            logger.debug(f"Active config: {config}")
        
        # Comprehensive CSV validation
        try:
            validate_csv_file(csv_file, logger)
            print("✓ CSV validation passed")
        except (FileNotFoundError, ValueError, CSVValidationError) as e:
            logger.error(f"CSV validation failed: {e}")
            print(f"❌ Error: {e}")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected validation error: {e}")
            print(f"❌ Unexpected error during validation: {e}")
            sys.exit(1)
        
        print("\nCSV Columns:")
        print("-" * 40)
        columns = read_csv_and_print_columns(csv_file, logger)
        
        if columns is None:
            logger.error("Failed to read CSV file")
            sys.exit(1)
        
        # Create backup before any modifications (skip for analyze mode)
        if config['mode'] != 'analyze':
            print("\n💾 Creating backup of original file...")
            backup_path = create_backup(csv_file, logger)
            if not backup_path:
                print("❌ Failed to create backup. Aborting for safety.")
                sys.exit(1)
        
        # Analysis phase
        print("\n" + "=" * 50)
        print("Checking for duplicate login_uri entries:")
        print("=" * 50)
        duplicate_list = find_duplicate_login_uris(csv_file, logger)
        
        if duplicate_list:
            logger.info(f"Found {len(duplicate_list)} duplicate URI entries")
            print(f"\nReturned {len(duplicate_list)} duplicate rows as a list for further filtering.")
        
        print("\n" + "=" * 70)
        print("Checking for duplicate login_uri AND login_username combinations:")
        print("=" * 70)
        duplicate_uri_username_list = find_duplicate_uri_and_username(csv_file, logger)
        
        if duplicate_uri_username_list:
            logger.info(f"Found {len(duplicate_uri_username_list)} duplicate URI+username entries")
            print(f"\nReturned {len(duplicate_uri_username_list)} rows with duplicate URI and username for further filtering.")
        
        # Handle different modes
        if config['mode'] == 'analyze':
            print("\nAnalysis complete. Use --mode to specify cleaning operation.")
            return
        
        if not duplicate_list:
            print("No duplicates found - nothing to clean.")
            return
        
        # Cleaning operations
        cleaned_df = None
        deleted_df = None
        
        if config['mode'] == 'interactive':
            if config['dry_run']:
                print("DRY RUN MODE: Cannot use dry-run with interactive mode")
                return
            print("\nStarting interactive deletion...")
            cleaned_df = interactive_delete_duplicates(csv_file, logger, config['show_passwords'])
        
        elif config['mode'] == 'auto':
            print("\nStarting automatic domain-based cleanup...")
            result = automatic_domain_cleanup(csv_file, logger, config['dry_run'])
            if result and len(result) == 2:
                cleaned_df, deleted_df = result
        
        # Save results (skip in dry run mode)
        if cleaned_df is not None and not config['dry_run']:
            if deleted_df is not None and not deleted_df.empty:
                save_deleted_entries(deleted_df, csv_file)
            
            if config['output']:
                output_path = config['output']
                cleaned_df.to_csv(output_path, index=False)
                logger.info(f"Cleaned data saved to: {output_path}")
                print(f"\nCleaned CSV saved as: {output_path}")
            else:
                output_path = save_cleaned_csv(cleaned_df, csv_file, logger)
                if output_path:
                    logger.info(f"Cleaned data saved to: {output_path}")
        elif config['dry_run']:
            print("🔍 DRY RUN: No files were saved.")
        
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        print("\nOperation cancelled.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
