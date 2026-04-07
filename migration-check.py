import re
import difflib
from pathlib import Path

def extract_core_text(text):
    """Aggressively strips Logseq/Hugo metadata and formatting for a pure content comparison."""
    # 1. Strip Hugo front matter (YAML/TOML)
    text = re.sub(r'^---.*?^---', '', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'^\+\+\+.*?^\+\+\+', '', text, flags=re.MULTILINE | re.DOTALL)
    
    # 2. Strip Logseq block/page properties (e.g., id:: 1234, tags:: x)
    text = re.sub(r'^[ \t]*\w+::.*$', '', text, flags=re.MULTILINE)
    
    # 3. Strip Logseq task markers and timestamps
    text = re.sub(r'^(?:TODO|DONE|DOING|LATER|NOW)\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'(?:SCHEDULED|DEADLINE): <[^>]+>', '', text)
    
    # 4. Strip Hugo shortcodes
    text = re.sub(r'\{\{.*?\}\}', '', text)
    
    # 5. Strip raw UUIDs AND Logseq block references ((uuid))
    text = re.sub(r'\(\([0-9a-fA-F\-]{36}\)\)', '', text)
    text = re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '', text)

    # 6. NEW: Strip LaTeX commands (like \rarr, \rightarrow) to prevent false mismatches
    text = re.sub(r'\\[a-zA-Z]+', '', text)

    # 7. Normalize: remove all non-alphanumeric characters, convert to lowercase
    return re.sub(r'[\W_]+', '', text).lower()

def find_unmigrated_content(src_dir, dest_dir, similarity_threshold=0.90, min_char_length=50):
    src_path = Path(src_dir)
    dest_path = Path(dest_dir)

    print(f"Step 1: Reading and cleaning destination files...\n-> {dest_path}")
    
    dest_files = {} 
    
    # Index Destination (Hugo) Files
    for file_path in dest_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in {'.md', '.txt', '.html'}:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    cleaned = extract_core_text(f.read())
                    if cleaned:
                        dest_files[cleaned] = file_path.relative_to(dest_path)
            except Exception:
                pass

    print(f"Indexed {len(dest_files)} files in destination.")
    print(f"\nStep 2: Scanning source for unmigrated content...\n-> {src_path}")

    truly_unmigrated = []
    fuzzy_matches = []
    skipped_blank = 0
    exact_matches = 0
    
    # Scan Source (Logseq) Files
    for file_path in src_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in {'.md', '.txt'}:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    src_cleaned = extract_core_text(f.read())
                    
                # Ignore empty files OR files with barely any text (like _index.md)
                if len(src_cleaned) < min_char_length:
                    skipped_blank += 1
                    continue

                # --- 1. Fast Pass: Exact match on cleaned text ---
                if src_cleaned in dest_files:
                    exact_matches += 1
                    continue # Fully migrated, ignore it.
                
                # --- 2. Precision Percentage Pass: Find the most similar file ---
                best_ratio = 0
                best_match_path = None
                
                for dest_cleaned, dest_rel_path in dest_files.items():
                    # Size check optimization
                    length_ratio = min(len(src_cleaned), len(dest_cleaned)) / max(len(src_cleaned), len(dest_cleaned))
                    if length_ratio < similarity_threshold:
                        continue
                        
                    matcher = difflib.SequenceMatcher(None, src_cleaned, dest_cleaned)
                    
                    if matcher.quick_ratio() >= similarity_threshold:
                        exact_ratio = matcher.ratio()
                        
                        if exact_ratio > best_ratio:
                            best_ratio = exact_ratio
                            best_match_path = dest_rel_path
                            if best_ratio > 0.99: 
                                break 
                
                # Route based on score
                if best_ratio >= similarity_threshold:
                    fuzzy_matches.append((file_path.relative_to(src_path), best_match_path, best_ratio))
                else:
                    truly_unmigrated.append((file_path.relative_to(src_path), best_match_path, best_ratio))
                    
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    # --- Print Output ---
    print("\n" + "="*60)
    print("📊 MIGRATION SUMMARY:")
    print("="*60)
    print(f"Total Perfect Matches:  {exact_matches}")
    print(f"Total Skipped (Blank):  {skipped_blank}")
    print(f"Total Fuzzy Matches:    {len(fuzzy_matches)}")
    print(f"Total Unmigrated:       {len(truly_unmigrated)}")

    if fuzzy_matches:
        print("\n" + "="*60)
        print(f"✅ MIGRATED WITH EDITS (Match over {similarity_threshold*100}%):")
        print("="*60)
        for src, dest, ratio in fuzzy_matches:
            print(f"[Match {ratio:.1%}] {src}  -->  {dest}")

    print("\n" + "="*60)
    print(f"❌ UNMIGRATED ({len(truly_unmigrated)} files requiring attention):")
    print("="*60)
    
    if not truly_unmigrated:
        print("All files successfully migrated! No action required.")
    else:
        for src, best_dest, ratio in truly_unmigrated:
            if best_dest and ratio > 0.4:
                print(f"{src}\n   └─ Closest Dest: {best_dest} (at {ratio:.1%})\n")
            else:
                print(f"{src}\n   └─ No similar file found in destination\n")

if __name__ == "__main__":
    # Point these to your actual Logseq and Hugo directories
    source = r"C:\Users\jackr\Documents\UAH\UAH-Notes\pages" 
    destination = r"C:\Users\jackr\Documents\UAH\UAH-Notes-md\uahnotes-md\content\notes" 
    
    # Runs the check
    find_unmigrated_content(source, destination, similarity_threshold=0.50, min_char_length=50)