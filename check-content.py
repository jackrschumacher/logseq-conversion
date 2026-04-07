import re
import difflib
from pathlib import Path

def extract_core_text(text):
    """Aggressively strips Logseq/Hugo metadata before cleaning."""
    # 1. Strip Hugo front matter (YAML/TOML)
    text = re.sub(r'^---.*?^---', '', text, flags=re.MULTILINE | re.DOTALL)
    text = re.sub(r'^\+\+\+.*?^\+\+\+', '', text, flags=re.MULTILINE | re.DOTALL)
    
    # 2. Strip Logseq block/page properties (e.g., id:: 1234, tags:: x)
    text = re.sub(r'^[ \t]*\w+::.*$', '', text, flags=re.MULTILINE)
    
    # 3. Strip Hugo shortcodes
    text = re.sub(r'\{\{.*?\}\}', '', text)
    
    # 4. Strip raw UUIDs that Logseq sometimes leaves behind
    text = re.sub(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', '', text)

    # 5. Normalize: remove all non-alphanumeric characters, convert to lowercase
    return re.sub(r'[\W_]+', '', text).lower()

def find_unmigrated_content(src_dir, dest_dir, similarity_threshold=0.90):
    src_path = Path(src_dir)
    dest_path = Path(dest_dir)

    print(f"Step 1: Reading and cleaning destination files...\n-> {dest_path}")
    
    # Store cleaned text for destination files
    # Dictionary format: { cleaned_text_string: destination_relative_path }
    dest_files = {} 
    
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
    
    for file_path in src_path.rglob('*'):
        if file_path.is_file() and file_path.suffix.lower() in {'.md', '.txt'}:
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    src_cleaned = extract_core_text(f.read())
                    
                if not src_cleaned:
                    continue

                # --- 1. Fast Pass: Exact match on cleaned text ---
                if src_cleaned in dest_files:
                    continue # Fully migrated, ignore it.
                
                # --- 2. Percentage Pass: Find the most similar file ---
                best_ratio = 0
                best_match_path = None
                
                # Compare the cleaned source against all cleaned dest texts
                for dest_cleaned, dest_rel_path in dest_files.items():
                    
                    # Optimization: Don't compare a 10-word file to a 10,000-word file
                    length_ratio = min(len(src_cleaned), len(dest_cleaned)) / max(len(src_cleaned), len(dest_cleaned))
                    if length_ratio < similarity_threshold:
                        continue
                        
                    # quick_ratio is a fast approximation of sequence similarity
                    ratio = difflib.SequenceMatcher(None, src_cleaned, dest_cleaned).quick_ratio()
                    
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_match_path = dest_rel_path
                        if best_ratio > 0.99: 
                            break # Break early if it's practically identical
                
                # Route the file based on the similarity score
                if best_ratio >= similarity_threshold:
                    fuzzy_matches.append((file_path.relative_to(src_path), best_match_path, best_ratio))
                else:
                    truly_unmigrated.append((file_path.relative_to(src_path), best_match_path, best_ratio))
                    
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    # --- Print Output ---
    print("\n" + "="*60)
    print(f"✅ MIGRATED:")
    print("="*60)
    for src, dest, ratio in fuzzy_matches:
        print(f"[Match {ratio:.1%}] {src}  -->  {dest}")

    print("\n" + "="*60)
    print(f"❌ UNMIGRATED ({len(truly_unmigrated)} files requiring attention):")
    print("="*60)
    for src, best_dest, ratio in truly_unmigrated:
        if best_dest and ratio > 0.5:
            # Tells you what it *almost* matched with, in case you merged files
            print(f"{src}\n   └─ Closest Dest: {best_dest} (at {ratio:.1%})\n")
        else:
            print(f"{src}\n   └─ No similar file found in destination\n")

if __name__ == "__main__":
    source = r"C:\Users\jackr\Documents\Programming\logseq-conversion\pages" # Update if needed
    destination = r"C:\Users\jackr\Documents\Programming\logseq-conversion\content\notes" # Update if needed
    
    # You can tweak the 0.90 (90%) threshold up or down if needed
    find_unmigrated_content(source, destination, similarity_threshold=0.90)