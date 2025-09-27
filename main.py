#!/usr/bin/env python3
"""
Smart File Organizer
Automatically organize files in Downloads folder by type, date, or custom rules
"""

import os
import shutil
import json
from datetime import datetime, timedelta
from pathlib import Path
import mimetypes
from collections import defaultdict
import argparse
import time

class SmartFileOrganizer:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = self.load_config()
        self.downloads_path = Path.home() / "Downloads"
        
        # Default file type mappings
        self.default_categories = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff"],
            "Documents": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".pages"],
            "Spreadsheets": [".xls", ".xlsx", ".csv", ".numbers"],
            "Presentations": [".ppt", ".pptx", ".key"],
            "Videos": [".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm"],
            "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".dmg"],
            "Code": [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".php", ".rb"],
            "Executables": [".app", ".exe", ".deb", ".pkg", ".dmg"]
        }

    def load_config(self):
        """Load configuration from JSON file"""
        default_config = {
            "organize_by": "type",  # "type", "date", or "custom"
            "watch_mode": False,
            "create_year_folders": True,
            "create_month_folders": False,
            "min_file_age_hours": 0,
            "custom_rules": {},
            "excluded_files": [".DS_Store", "desktop.ini"],
            "excluded_extensions": [],
            "dry_run": False
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    # Merge with defaults
                    for key, value in default_config.items():
                        if key not in config:
                            config[key] = value
                    return config
            except json.JSONDecodeError:
                print("Warning: Invalid config file. Using defaults.")
        
        return default_config

    def save_config(self):
        """Save current configuration to JSON file"""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=2)

    def get_file_category(self, file_path):
        """Determine the category of a file based on its extension"""
        extension = file_path.suffix.lower()
        
        # Check custom rules first
        for category, extensions in self.config.get("custom_rules", {}).items():
            if extension in [ext.lower() for ext in extensions]:
                return category
        
        # Check default categories
        for category, extensions in self.default_categories.items():
            if extension in extensions:
                return category
        
        return "Others"

    def should_organize_file(self, file_path):
        """Check if a file should be organized based on configuration"""
        # Skip if file is in excluded list
        if file_path.name in self.config["excluded_files"]:
            return False
        
        # Skip if extension is excluded
        if file_path.suffix.lower() in self.config["excluded_extensions"]:
            return False
        
        # Skip if file is too new (based on min_file_age_hours)
        if self.config["min_file_age_hours"] > 0:
            file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_age < timedelta(hours=self.config["min_file_age_hours"]):
                return False
        
        return True

    def create_destination_path(self, file_path):
        """Create the destination path based on organization method"""
        base_path = self.downloads_path
        
        if self.config["organize_by"] == "type":
            category = self.get_file_category(file_path)
            dest_path = base_path / "Organized" / category
        
        elif self.config["organize_by"] == "date":
            file_date = datetime.fromtimestamp(file_path.stat().st_mtime)
            dest_path = base_path / "Organized"
            
            if self.config["create_year_folders"]:
                dest_path = dest_path / str(file_date.year)
            
            if self.config["create_month_folders"]:
                dest_path = dest_path / f"{file_date.month:02d}-{file_date.strftime('%B')}"
        
        else:  # custom organization
            # This would be extended based on specific custom rules
            dest_path = base_path / "Organized" / "Custom"
        
        return dest_path

    def organize_file(self, file_path, dest_dir):
        """Move a single file to its destination directory"""
        try:
            # Create destination directory if it doesn't exist
            dest_dir.mkdir(parents=True, exist_ok=True)
            
            # Handle file name conflicts
            dest_file = dest_dir / file_path.name
            counter = 1
            original_stem = file_path.stem
            original_suffix = file_path.suffix
            
            while dest_file.exists():
                new_name = f"{original_stem}_{counter}{original_suffix}"
                dest_file = dest_dir / new_name
                counter += 1
            
            if self.config["dry_run"]:
                print(f"[DRY RUN] Would move: {file_path} -> {dest_file}")
                return True
            else:
                shutil.move(str(file_path), str(dest_file))
                print(f"Moved: {file_path.name} -> {dest_file.parent.name}/")
                return True
        
        except Exception as e:
            print(f"Error moving {file_path.name}: {e}")
            return False

    def organize_downloads(self):
        """Organize all files in the Downloads folder"""
        if not self.downloads_path.exists():
            print(f"Downloads folder not found: {self.downloads_path}")
            return
        
        print(f"Organizing Downloads folder: {self.downloads_path}")
        print(f"Organization method: {self.config['organize_by']}")
        if self.config["dry_run"]:
            print("DRY RUN MODE - No files will be moved")
        print("-" * 50)
        
        files_processed = 0
        files_moved = 0
        
        # Get all files in Downloads (not directories)
        for item in self.downloads_path.iterdir():
            if item.is_file() and self.should_organize_file(item):
                files_processed += 1
                dest_dir = self.create_destination_path(item)
                
                if self.organize_file(item, dest_dir):
                    files_moved += 1
        
        print("-" * 50)
        print(f"Processed {files_processed} files, moved {files_moved} files")

    def watch_downloads(self):
        """Watch Downloads folder for new files and organize them automatically"""
        print(f"Watching {self.downloads_path} for new files...")
        print("Press Ctrl+C to stop watching")
        
        known_files = set(self.downloads_path.iterdir())
        
        try:
            while True:
                time.sleep(2)  # Check every 2 seconds
                current_files = set(self.downloads_path.iterdir())
                new_files = current_files - known_files
                
                for new_file in new_files:
                    if new_file.is_file() and self.should_organize_file(new_file):
                        # Wait a moment for file to finish downloading
                        time.sleep(1)
                        dest_dir = self.create_destination_path(new_file)
                        if self.organize_file(new_file, dest_dir):
                            print(f"Auto-organized: {new_file.name}")
                
                known_files = current_files
        
        except KeyboardInterrupt:
            print("\nStopped watching Downloads folder")

    def get_statistics(self):
        """Get statistics about the Downloads folder"""
        if not self.downloads_path.exists():
            return {}
        
        stats = {
            "total_files": 0,
            "categories": defaultdict(int),
            "total_size": 0,
            "largest_files": []
        }
        
        files_info = []
        
        for item in self.downloads_path.rglob("*"):
            if item.is_file():
                stats["total_files"] += 1
                file_size = item.stat().st_size
                stats["total_size"] += file_size
                
                category = self.get_file_category(item)
                stats["categories"][category] += 1
                
                files_info.append((item.name, file_size, category))
        
        # Get 5 largest files
        files_info.sort(key=lambda x: x[1], reverse=True)
        stats["largest_files"] = files_info[:5]
        
        return dict(stats)

def main():
    parser = argparse.ArgumentParser(description="Smart File Organizer for Downloads")
    parser.add_argument("--organize", action="store_true", help="Organize files now")
    parser.add_argument("--watch", action="store_true", help="Watch for new files")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be moved")
    parser.add_argument("--config", help="Path to config file", default="config.json")
    
    args = parser.parse_args()
    
    organizer = SmartFileOrganizer(args.config)
    
    if args.dry_run:
        organizer.config["dry_run"] = True
    
    if args.organize:
        organizer.organize_downloads()
    elif args.watch:
        organizer.watch_downloads()
    elif args.stats:
        stats = organizer.get_statistics()
        print("Downloads Folder Statistics:")
        print(f"Total files: {stats['total_files']}")
        print(f"Total size: {stats['total_size'] / (1024*1024):.2f} MB")
        print("\nFiles by category:")
        for category, count in stats['categories'].items():
            print(f"  {category}: {count}")
        if stats['largest_files']:
            print("\nLargest files:")
            for name, size, category in stats['largest_files']:
                print(f"  {name} ({size / (1024*1024):.2f} MB) - {category}")
    else:
        print("Smart File Organizer")
        print("Usage: python main.py [--organize|--watch|--stats] [--dry-run]")
        print("\nCommands:")
        print("  --organize  Organize files in Downloads folder now")
        print("  --watch     Watch Downloads folder and auto-organize new files")
        print("  --stats     Show statistics about Downloads folder")
        print("  --dry-run   Show what would be moved without actually moving files")

if __name__ == "__main__":
    main()
