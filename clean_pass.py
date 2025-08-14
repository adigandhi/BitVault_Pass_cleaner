import pandas as pd
from urllib.parse import urlparse
import argparse
import logging
import sys
from pathlib import Path

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

def validate_csv_file(csv_file_path):
    """Validate that the CSV file exists and is readable."""
    path = Path(csv_file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")
    if not path.is_file():
        raise ValueError(f"Path is not a file: {csv_file_path}")
    if path.stat().st_size == 0:
        raise ValueError(f"CSV file is empty: {csv_file_path}")
    return True

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

def remove_fully_duplicate_rows(df):
    """Remove rows that are completely identical across all columns, keeping only one copy."""
    original_count = len(df)
    
    # Remove fully duplicate rows (keep='first' keeps the first occurrence)
    df_no_full_dupes = df.drop_duplicates(keep='first')
    
    removed_count = original_count - len(df_no_full_dupes)
    
    if removed_count > 0:
        print(f"\nAutomatically removed {removed_count} fully duplicate rows (identical across all columns)")
        print(f"Rows remaining: {len(df_no_full_dupes)}")
    else:
        print("\nNo fully duplicate rows found.")
    
    return df_no_full_dupes, removed_count

def normalize_urls(df):
    """Normalize login_uri by removing trailing slashes and creating a normalized column for comparison."""
    # Memory efficient: modify in place instead of copying when possible
    if 'login_uri' in df.columns:
        # Create a normalized version for comparison (remove trailing slashes)
        df['login_uri_normalized'] = df['login_uri'].astype(str).str.rstrip('/')
        print("URLs normalized (trailing slashes removed for duplicate detection)")
    
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
    entries_with_parentheses = df['name'].str.contains(r'\([^)]*\)', na=False).sum()
    
    if entries_with_parentheses == 0:
        if logger:
            logger.info("No entries with parentheses found in name column")
        print("No parentheses found in name column to clean")
        return df
    
    # Clean the name column
    # Remove everything in parentheses including the parentheses themselves
    df['name'] = df['name'].str.replace(r'\s*\([^)]*\)\s*', '', regex=True)
    
    # Clean up any double spaces and strip whitespace
    df['name'] = df['name'].str.replace(r'\s+', ' ', regex=True).str.strip()
    
    message = f"Cleaned {entries_with_parentheses} entries in name column (removed parentheses content)"
    if logger:
        logger.info(message)
    print(f"✓ {message}")
    
    return df

def interactive_delete_duplicates(csv_file_path):
    try:
        df = pd.read_csv(csv_file_path)
        original_count = len(df)
        
        # First, automatically remove fully duplicate rows
        print("\n" + "=" * 50)
        print("STEP 1: Removing fully duplicate rows")
        print("=" * 50)
        df, fully_removed_count = remove_fully_duplicate_rows(df)
        
        # Normalize URLs for better duplicate detection
        print("\n" + "=" * 50)
        print("STEP 1.5: Normalizing URLs and cleaning names")
        print("=" * 50)
        df = normalize_urls(df)
        df = clean_name_column(df)
        
        required_columns = ['login_uri', 'login_username']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"Error: Missing columns: {missing_columns}")
            return None
        
        # Find rows with duplicate login_uri AND login_username combinations (using normalized URLs)
        duplicate_uri_username_rows = df[df.duplicated(subset=['login_uri_normalized', 'login_username'], keep=False)]
        
        if duplicate_uri_username_rows.empty:
            print("\nNo remaining duplicate login_uri + login_username combinations found after removing fully duplicate rows.")
            if fully_removed_count > 0:
                print(f"Total cleanup: {fully_removed_count} fully duplicate rows removed.")
            return df
        
        print("\n" + "=" * 50)
        print("STEP 2: Interactive partial duplicate cleanup")
        print("=" * 50)
        print(f"Found {len(duplicate_uri_username_rows)} rows with duplicate login_uri + login_username combinations (after removing full duplicates)")
        
        rows_to_delete = []
        # Group by both normalized login_uri and login_username
        unique_combinations = duplicate_uri_username_rows[['login_uri_normalized', 'login_username']].drop_duplicates()
        
        for _, combination in unique_combinations.iterrows():
            uri_normalized = combination['login_uri_normalized']
            username = combination['login_username']
            
            # Get all rows with this specific normalized login_uri + login_username combination
            combo_group = df[(df['login_uri_normalized'] == uri_normalized) & (df['login_username'] == username)].copy()
            # Store original indices before reset to avoid conflicts
            combo_group['original_index'] = combo_group.index
            combo_group.reset_index(drop=True, inplace=True)
            
            print(f"\n{'='*60}")
            print(f"Duplicate group for login_uri (normalized): {uri_normalized}")
            print(f"                         login_username: {username}")
            print(f"{'='*60}")
            
            for idx, row in combo_group.iterrows():
                print(f"\nRow {idx + 1}:")
                for col in df.columns:
                    if col != 'original_index':  # Don't show the temporary index column
                        if col == 'login_password':
                            print(f"  {col}: {'*' * len(str(row[col]))}")  # Mask password
                        else:
                            print(f"  {col}: {row[col]}")
            
            print(f"\nWhich rows would you like to DELETE for this combination?")
            print(f"Enter row numbers (1-{len(combo_group)}) separated by commas, or 'none' to keep all:")
            
            while True:
                try:
                    user_input = input("Rows to delete: ").strip().lower()
                    
                    if user_input == 'none':
                        break
                    
                    if user_input == '':
                        print("Please enter row numbers or 'none'")
                        continue
                    
                    selected_rows = [int(x.strip()) for x in user_input.split(',')]
                    
                    if all(1 <= row <= len(combo_group) for row in selected_rows):
                        for row_num in selected_rows:
                            original_index = combo_group.iloc[row_num - 1]['original_index']
                            rows_to_delete.append(original_index)
                        break
                    else:
                        print(f"Please enter numbers between 1 and {len(combo_group)}")
                        
                except ValueError:
                    print("Invalid input. Please enter numbers separated by commas or 'none'")
        
        if rows_to_delete:
            df_cleaned = df.drop(rows_to_delete)
            df_cleaned.reset_index(drop=True, inplace=True)
            
            # Remove the temporary columns from final output
            temp_columns = ['login_uri_normalized', 'original_index']
            df_cleaned = df_cleaned.drop(columns=[col for col in temp_columns if col in df_cleaned.columns], errors='ignore')
            
            print(f"\n{'='*50}")
            print(f"SUMMARY:")
            print(f"{'='*50}")
            print(f"Original rows: {original_count}")
            print(f"Fully duplicate rows removed: {fully_removed_count}")
            print(f"Partial duplicate rows deleted: {len(rows_to_delete)}")
            print(f"Total rows removed: {fully_removed_count + len(rows_to_delete)}")
            print(f"Remaining rows: {len(df_cleaned)}")
            
            return df_cleaned
        else:
            print("\nNo partial duplicate rows selected for deletion.")
            if fully_removed_count > 0:
                print(f"Total cleanup: {fully_removed_count} fully duplicate rows removed.")
            
            # Remove the temporary columns from final output
            temp_columns = ['login_uri_normalized', 'original_index']
            df = df.drop(columns=[col for col in temp_columns if col in df.columns], errors='ignore')
            
            return df
            
    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
        return None
    except Exception as e:
        print(f"Error processing CSV file: {e}")
        return None

def automatic_delete_duplicates(csv_file_path):
    """Automatically delete duplicate login_uri + login_username combinations, keeping only the first occurrence."""
    try:
        df = pd.read_csv(csv_file_path)
        original_count = len(df)
        
        # First, automatically remove fully duplicate rows
        print("\n" + "=" * 50)
        print("STEP 1: Removing fully duplicate rows")
        print("=" * 50)
        df, fully_removed_count = remove_fully_duplicate_rows(df)
        
        # Normalize URLs for better duplicate detection
        print("\n" + "=" * 50)
        print("STEP 1.5: Normalizing URLs and cleaning names")
        print("=" * 50)
        df = normalize_urls(df)
        df = clean_name_column(df)
        
        required_columns = ['login_uri', 'login_username']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"Error: Missing columns: {missing_columns}")
            return None, None
        
        # Find rows with duplicate login_uri AND login_username combinations (using normalized URLs)
        duplicate_uri_username_rows = df[df.duplicated(subset=['login_uri_normalized', 'login_username'], keep=False)]
        
        if duplicate_uri_username_rows.empty:
            print("\nNo remaining duplicate login_uri + login_username combinations found after removing fully duplicate rows.")
            if fully_removed_count > 0:
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
        df_cleaned = df.groupby(['login_uri_normalized', 'login_username'], group_keys=False).apply(keep_shortest_uri_auto).reset_index(drop=True)
        
        # Find the rows that were removed
        removed_indices = set(df.index) - set(df_cleaned.index)
        deleted_rows = df.loc[list(removed_indices)]
        
        partial_removed_count = len(deleted_rows)
        
        print(f"Automatically removed {partial_removed_count} duplicate login_uri + login_username entries (kept shortest URI)")
        
        # Remove the normalized column from final output (it was just for comparison)
        if 'login_uri_normalized' in df_cleaned.columns:
            df_cleaned = df_cleaned.drop('login_uri_normalized', axis=1)
        if 'login_uri_normalized' in deleted_rows.columns:
            deleted_rows = deleted_rows.drop('login_uri_normalized', axis=1)
        
        print(f"\n{'='*50}")
        print(f"SUMMARY:")
        print(f"{'='*50}")
        print(f"Original rows: {original_count}")
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

def save_deleted_entries(deleted_df, original_path):
    """Save deleted entries to a backup file."""
    if deleted_df is None or deleted_df.empty:
        print("No deleted entries to save.")
        return None
    
    base_name = original_path.rsplit('.', 1)[0]
    extension = original_path.rsplit('.', 1)[1] if '.' in original_path else 'csv'
    deleted_path = f"{base_name}_deleted_entries.{extension}"
    
    try:
        deleted_df.to_csv(deleted_path, index=False)
        print(f"Deleted entries saved to: {deleted_path}")
        return deleted_path
    except Exception as e:
        print(f"Error saving deleted entries: {e}")
        return None

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

def automatic_domain_cleanup(csv_file_path):
    """Automatically clean up entries with same domain + username, keeping only the first occurrence."""
    try:
        df = pd.read_csv(csv_file_path)
        original_count = len(df)
        
        # Normalize URLs and extract domains
        print("\n" + "=" * 60)
        print("DOMAIN-BASED DUPLICATE CLEANUP")
        print("=" * 60)
        
        df = normalize_urls(df)
        df = clean_name_column(df)
        df = add_domain_column(df)
        
        required_columns = ['login_uri', 'login_username', 'login_password']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            print(f"Error: Missing columns for domain cleanup: {missing_columns}")
            return None, None
        
        # Check if we have domain column
        if 'domain' not in df.columns:
            print("Error: Domain extraction failed.")
            return None, None
        
        print("Looking for entries with same domain + username + password combinations...")
        
        # Find duplicates based on domain + username + password
        domain_credentials_duplicates = df[df.duplicated(subset=['domain', 'login_username', 'login_password'], keep=False)]
        
        if domain_credentials_duplicates.empty:
            print("No duplicate domain + username + password combinations found.")
            # Clean up temporary columns
            df_cleaned = df.drop(['login_uri_normalized', 'domain'], axis=1, errors='ignore')
            return df_cleaned, pd.DataFrame()  # Return empty DataFrame for consistency
        
        print(f"Found {len(domain_credentials_duplicates)} rows with duplicate domain + username + password combinations")
        
        # Show summary of what will be cleaned
        unique_combinations = domain_credentials_duplicates[['domain', 'login_username', 'login_password']].drop_duplicates()
        print(f"\nWill clean {len(unique_combinations)} unique domain + username + password combinations:")
        
        total_to_remove = 0
        for _, combo in unique_combinations.iterrows():
            domain = combo['domain']
            username = combo['login_username']
            password_masked = '*' * len(str(combo['login_password']))  # Mask password for security
            count = len(df[(df['domain'] == domain) & (df['login_username'] == username) & (df['login_password'] == combo['login_password'])])
            total_to_remove += (count - 1)  # Will keep 1, remove others
            print(f"  - Domain: {domain}, Username: {username}, Password: {password_masked} ({count} entries → keep 1, remove {count-1})")
        
        print(f"\nSUMMARY: Will remove {total_to_remove} entries total, keeping shortest URI for each domain + username + password combination.")
        
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
        
        # Ask for user confirmation before proceeding
        print(f"\n{'='*60}")
        print("PROCEED WITH DELETION?")
        print(f"{'='*60}")
        print(f"This will delete {total_to_remove} entries and keep {len(df) - total_to_remove} entries.")
        confirmation = input("Type 'DELETE' to confirm, or 'n' to cancel: ").strip()
        
        if confirmation.upper() != 'DELETE':
            print("Domain cleanup cancelled by user.")
            # Clean up temporary columns
            df_cleaned = df.drop(['login_uri_normalized', 'domain'], axis=1, errors='ignore')
            return df_cleaned, pd.DataFrame()
        
        print("\nProceeding with domain cleanup...")
        
        # For each domain + username combination, keep the entry with the shortest URI
        def keep_shortest_uri(group):
            # Memory efficient: find shortest without creating extra columns
            min_length_idx = group['login_uri_normalized'].str.len().idxmin()
            return group.loc[[min_length_idx]]
        
        # Group by domain + username + password and apply the shortest URI selection
        df_cleaned = df.groupby(['domain', 'login_username', 'login_password'], group_keys=False).apply(keep_shortest_uri).reset_index(drop=True)
        
        # Find the rows that were removed
        removed_indices = set(df.index) - set(df_cleaned.index)
        deleted_rows = df.loc[list(removed_indices)]
        
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

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Clean and deduplicate Bitwarden CSV exports",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -f export.csv --mode interactive --verbose
  %(prog)s -f export.csv --mode auto --dry-run
  %(prog)s -f export.csv --mode analyze
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
    
    return parser.parse_args()

def main():
    """Main entry point for the script."""
    args = parse_arguments()
    logger = setup_logging(args.verbose)
    
    try:
        # Validate input file
        csv_file = args.file
        logger.info(f"Processing file: {csv_file}")
        
        print("CSV Columns:")
        print("-" * 40)
        columns = read_csv_and_print_columns(csv_file, logger)
        
        if columns is None:
            logger.error("Failed to read CSV file")
            sys.exit(1)
        
        # Required columns check
        required_columns = ['login_uri', 'login_username']
        missing_columns = [col for col in required_columns if col not in columns]
        
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            print(f"Error: Missing required columns: {missing_columns}")
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
        if args.mode == 'analyze':
            print("\nAnalysis complete. Use --mode to specify cleaning operation.")
            return
        
        if not duplicate_list:
            print("No duplicates found - nothing to clean.")
            return
        
        # Cleaning operations
        cleaned_df = None
        deleted_df = None
        
        if args.mode == 'interactive':
            if args.dry_run:
                print("DRY RUN MODE: Cannot use dry-run with interactive mode")
                return
            print("\nStarting interactive deletion...")
            cleaned_df = interactive_delete_duplicates(csv_file)
        
        elif args.mode == 'auto':
            print("\nStarting automatic domain-based cleanup...")
            if args.dry_run:
                print("DRY RUN MODE: No changes will be made")
                # TODO: Implement dry run logic
                return
            result = automatic_domain_cleanup(csv_file)
            if result and len(result) == 2:
                cleaned_df, deleted_df = result
        
        # Save results
        if cleaned_df is not None:
            if deleted_df is not None and not deleted_df.empty:
                save_deleted_entries(deleted_df, csv_file)
            
            if args.output:
                output_path = args.output
                cleaned_df.to_csv(output_path, index=False)
                logger.info(f"Cleaned data saved to: {output_path}")
                print(f"\nCleaned CSV saved as: {output_path}")
            else:
                output_path = save_cleaned_csv(cleaned_df, csv_file, logger)
                if output_path:
                    logger.info(f"Cleaned data saved to: {output_path}")
        
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
