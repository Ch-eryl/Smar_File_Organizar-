#!/usr/bin/env python3
"""
Flask web server for Smart File Organizer
Provides web interface to organize Downloads folder
"""

from flask import Flask, render_template, jsonify, request
from pathlib import Path
import json
import os
import threading
import time
from main import SmartFileOrganizer

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

# Global organizer instance
organizer = SmartFileOrganizer()
watch_thread = None
is_watching = False

@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    return jsonify(organizer.config)

@app.route('/api/config', methods=['POST'])
def save_config():
    """Save configuration"""
    try:
        config_data = request.json
        organizer.config.update(config_data)
        organizer.save_config()
        return jsonify({'success': True, 'message': 'Configuration saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/organize', methods=['POST'])
def organize_files():
    """Organize files in Downloads folder"""
    try:
        dry_run = request.json.get('dry_run', False)
        original_dry_run = organizer.config['dry_run']
        
        # Set dry run mode if requested
        organizer.config['dry_run'] = dry_run
        
        # Get file list before organizing
        files_before = list(organizer.downloads_path.glob('*'))
        files_to_organize = [f for f in files_before if f.is_file() and organizer.should_organize_file(f)]
        
        # Organize files
        organizer.organize_downloads()
        
        # Restore original dry run setting
        organizer.config['dry_run'] = original_dry_run
        
        return jsonify({
            'success': True, 
            'message': f'{"Preview complete" if dry_run else "Organization complete"}',
            'files_processed': len(files_to_organize)
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics about Downloads folder"""
    try:
        stats = organizer.get_statistics()
        
        # Format file sizes
        if 'total_size' in stats:
            stats['total_size_mb'] = round(stats['total_size'] / (1024 * 1024), 2)
        
        # Format largest files
        if 'largest_files' in stats:
            formatted_files = []
            for name, size, category in stats['largest_files']:
                formatted_files.append({
                    'name': name,
                    'size': size,
                    'size_mb': round(size / (1024 * 1024), 2),
                    'category': category
                })
            stats['largest_files'] = formatted_files
        
        return jsonify(stats)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/watch/start', methods=['POST'])
def start_watching():
    """Start watching Downloads folder"""
    global watch_thread, is_watching
    
    if is_watching:
        return jsonify({'success': False, 'message': 'Already watching'})
    
    try:
        is_watching = True
        watch_thread = threading.Thread(target=watch_downloads_thread, daemon=True)
        watch_thread.start()
        return jsonify({'success': True, 'message': 'Started watching Downloads folder'})
    
    except Exception as e:
        is_watching = False
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/watch/stop', methods=['POST'])
def stop_watching():
    """Stop watching Downloads folder"""
    global is_watching
    
    is_watching = False
    return jsonify({'success': True, 'message': 'Stopped watching Downloads folder'})

@app.route('/api/watch/status', methods=['GET'])
def watch_status():
    """Get watch status"""
    return jsonify({'watching': is_watching})

def watch_downloads_thread():
    """Background thread for watching Downloads folder"""
    global is_watching
    
    print(f"Started watching {organizer.downloads_path}")
    known_files = set(organizer.downloads_path.iterdir() if organizer.downloads_path.exists() else [])
    
    while is_watching:
        try:
            if not organizer.downloads_path.exists():
                time.sleep(2)
                continue
                
            current_files = set(organizer.downloads_path.iterdir())
            new_files = current_files - known_files
            
            for new_file in new_files:
                if new_file.is_file() and organizer.should_organize_file(new_file):
                    # Wait a moment for file to finish downloading
                    time.sleep(1)
                    dest_dir = organizer.create_destination_path(new_file)
                    if organizer.organize_file(new_file, dest_dir):
                        print(f"Auto-organized: {new_file.name}")
            
            known_files = current_files
            time.sleep(2)  # Check every 2 seconds
            
        except Exception as e:
            print(f"Error in watch thread: {e}")
            time.sleep(5)
    
    print("Stopped watching Downloads folder")

@app.route('/api/custom-rules', methods=['GET'])
def get_custom_rules():
    """Get custom organization rules"""
    return jsonify(organizer.config.get('custom_rules', {}))

@app.route('/api/custom-rules', methods=['POST'])
def save_custom_rules():
    """Save custom organization rules"""
    try:
        rules = request.json
        organizer.config['custom_rules'] = rules
        organizer.save_config()
        return jsonify({'success': True, 'message': 'Custom rules saved successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/preview', methods=['POST'])
def preview_organization():
    """Preview what files would be organized and where"""
    try:
        if not organizer.downloads_path.exists():
            return jsonify({'files': []})
        
        preview_files = []
        
        for item in organizer.downloads_path.iterdir():
            if item.is_file() and organizer.should_organize_file(item):
                dest_dir = organizer.create_destination_path(item)
                category = organizer.get_file_category(item)
                
                preview_files.append({
                    'name': item.name,
                    'size': item.stat().st_size,
                    'size_mb': round(item.stat().st_size / (1024 * 1024), 2),
                    'category': category,
                    'destination': str(dest_dir.relative_to(organizer.downloads_path))
                })
        
        return jsonify({'files': preview_files})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create templates directory if it doesn't exist
    templates_dir = Path('templates')
    templates_dir.mkdir(exist_ok=True)
    
    print("Smart File Organizer Web Interface")
    print("Open your browser to: http://localhost:5000")
    print("Press Ctrl+C to stop")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
