# Gemini generated
import shutil
import filecmp
from pathlib import Path

def sync_changed_images(src_dir, dst_dir):
    # Define paths using pathlib for robust cross-platform handling
    src_path = Path(src_dir)
    dst_path = Path(dst_dir)

    # Ensure the destination directory exists
    dst_path.mkdir(parents=True, exist_ok=True)

    # Set of typical image extensions to filter by
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.webp', '.ico'}

    files_checked = 0
    files_copied = 0

    print(f"Scanning source: {src_path}")
    
    # rglob('*') recursively finds all files in the source directory
    for file_path in src_path.rglob('*'):
        # Filter for files with image extensions
        if file_path.is_file() and file_path.suffix.lower() in image_extensions:
            files_checked += 1
            
            # Maintain any subdirectory structures
            rel_path = file_path.relative_to(src_path)
            target_path = dst_path / rel_path
            
            # Ensure the specific target subfolder exists
            target_path.parent.mkdir(parents=True, exist_ok=True)

            needs_copy = False
            
            # If the file doesn't exist at the destination, it's new
            if not target_path.exists():
                needs_copy = True
            else:
                # Compare files. shallow=False reads file contents to guarantee accuracy 
                # instead of just checking size and modification time.
                if not filecmp.cmp(file_path, target_path, shallow=False):
                    needs_copy = True

            # Perform the copy if it's new or changed
            if needs_copy:
                print(f"Transferring: {rel_path}")
                # copy2 preserves file metadata like creation and modification times
                shutil.copy2(file_path, target_path)
                files_copied += 1

    print(f"\n--- Sync Complete ---")
    print(f"Images checked: {files_checked}")
    print(f"Images updated: {files_copied}")

if __name__ == "__main__":
    # Using 'r' before the string treats it as a raw string, 
    # preventing Windows backslashes from acting as escape characters.
    source = r"C:\Users\jackr\Documents\UAH\UAH-Notes\assets"
    destination = r"C:\Users\jackr\Documents\UAH\UAH-Notes-md\uahnotes-md\static\assets"
    
    sync_changed_images(source, destination)