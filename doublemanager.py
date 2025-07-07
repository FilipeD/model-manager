#!/usr/bin/env python3
"""
Ollama Model Manager - Dual Pane File Manager
A DoubleCMD-like application for managing Ollama models across different locations
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import json
import hashlib
import shutil
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
import threading
from datetime import datetime

class OllamaModelManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Ollama Model Manager - Dual Pane File Manager")
        self.root.geometry("1400x800")
        
        # Current paths for left and right panes
        self.left_path = tk.StringVar()
        self.right_path = tk.StringVar()
        
        # Model data storage
        self.left_models = {}
        self.right_models = {}
        
        self.setup_ui()
        self.setup_default_paths()
        
    def setup_ui(self):
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Toolbar
        toolbar = ttk.Frame(main_frame)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(toolbar, text="Refresh Both", command=self.refresh_both).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Copy Left→Right", command=self.copy_left_to_right).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Copy Right→Left", command=self.copy_right_to_left).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Delete Selected", command=self.delete_selected).pack(side=tk.LEFT, padx=2)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(toolbar, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.pack(side=tk.RIGHT, padx=2)
        
        # Dual pane container
        pane_container = ttk.Frame(main_frame)
        pane_container.pack(fill=tk.BOTH, expand=True)
        
        # Left pane
        left_frame = ttk.LabelFrame(pane_container, text="Left Pane", padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 2))
        
        # Left navigation
        left_nav = ttk.Frame(left_frame)
        left_nav.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(left_nav, text="Browse", command=lambda: self.browse_folder('left')).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_nav, text="Home", command=lambda: self.go_home('left')).pack(side=tk.LEFT, padx=2)
        ttk.Button(left_nav, text="Refresh", command=lambda: self.refresh_pane('left')).pack(side=tk.LEFT, padx=2)
        
        # Left path entry
        ttk.Label(left_nav, text="Path:").pack(side=tk.LEFT, padx=(10, 2))
        left_path_entry = ttk.Entry(left_nav, textvariable=self.left_path, width=40)
        left_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        left_path_entry.bind('<Return>', lambda e: self.refresh_pane('left'))
        
        # Left tree
        left_tree_frame = ttk.Frame(left_frame)
        left_tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.left_tree = ttk.Treeview(left_tree_frame, columns=("size", "status"), show="tree headings")
        self.left_tree.heading("#0", text="Model/Blob")
        self.left_tree.heading("size", text="Size")
        self.left_tree.heading("status", text="Status")
        self.left_tree.column("#0", width=300)
        self.left_tree.column("size", width=100)
        self.left_tree.column("status", width=100)
        
        left_scrollbar = ttk.Scrollbar(left_tree_frame, orient=tk.VERTICAL, command=self.left_tree.yview)
        self.left_tree.configure(yscrollcommand=left_scrollbar.set)
        
        self.left_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Right pane (similar structure)
        right_frame = ttk.LabelFrame(pane_container, text="Right Pane", padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(2, 0))
        
        # Right navigation
        right_nav = ttk.Frame(right_frame)
        right_nav.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(right_nav, text="Browse", command=lambda: self.browse_folder('right')).pack(side=tk.LEFT, padx=2)
        ttk.Button(right_nav, text="Home", command=lambda: self.go_home('right')).pack(side=tk.LEFT, padx=2)
        ttk.Button(right_nav, text="Refresh", command=lambda: self.refresh_pane('right')).pack(side=tk.LEFT, padx=2)
        
        # Right path entry
        ttk.Label(right_nav, text="Path:").pack(side=tk.LEFT, padx=(10, 2))
        right_path_entry = ttk.Entry(right_nav, textvariable=self.right_path, width=40)
        right_path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        right_path_entry.bind('<Return>', lambda e: self.refresh_pane('right'))
        
        # Right tree
        right_tree_frame = ttk.Frame(right_frame)
        right_tree_frame.pack(fill=tk.BOTH, expand=True)
        
        self.right_tree = ttk.Treeview(right_tree_frame, columns=("size", "status"), show="tree headings")
        self.right_tree.heading("#0", text="Model/Blob")
        self.right_tree.heading("size", text="Size")
        self.right_tree.heading("status", text="Status")
        self.right_tree.column("#0", width=300)
        self.right_tree.column("size", width=100)
        self.right_tree.column("status", width=100)
        
        right_scrollbar = ttk.Scrollbar(right_tree_frame, orient=tk.VERTICAL, command=self.right_tree.yview)
        self.right_tree.configure(yscrollcommand=right_scrollbar.set)
        
        self.right_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Context menus
        self.setup_context_menus()
        
    def setup_context_menus(self):
        # Left tree context menu
        self.left_context_menu = tk.Menu(self.root, tearoff=0)
        self.left_context_menu.add_command(label="Copy to Right", command=lambda: self.copy_selected('left'))
        self.left_context_menu.add_command(label="Delete", command=lambda: self.delete_selected('left'))
        self.left_context_menu.add_separator()
        self.left_context_menu.add_command(label="Properties", command=lambda: self.show_properties('left'))
        
        # Right tree context menu
        self.right_context_menu = tk.Menu(self.root, tearoff=0)
        self.right_context_menu.add_command(label="Copy to Left", command=lambda: self.copy_selected('right'))
        self.right_context_menu.add_command(label="Delete", command=lambda: self.delete_selected('right'))
        self.right_context_menu.add_separator()
        self.right_context_menu.add_command(label="Properties", command=lambda: self.show_properties('right'))
        
        # Bind context menus
        self.left_tree.bind("<Button-3>", lambda e: self.show_context_menu(e, 'left'))
        self.right_tree.bind("<Button-3>", lambda e: self.show_context_menu(e, 'right'))
        
    def setup_default_paths(self):
        # Set default paths based on OS
        if os.name == 'nt':  # Windows
            default_path = os.path.expanduser("~\\.ollama\\models")
        else:  # Linux/Mac
            default_path = os.path.expanduser("~/.ollama/models")
        
        self.left_path.set(default_path)
        self.right_path.set(default_path)
        
        # Initial refresh
        self.refresh_both()
        
    def browse_folder(self, pane):
        folder = filedialog.askdirectory(title=f"Select {pane.capitalize()} Folder")
        if folder:
            if pane == 'left':
                self.left_path.set(folder)
            else:
                self.right_path.set(folder)
            self.refresh_pane(pane)
            
    def go_home(self, pane):
        if os.name == 'nt':  # Windows
            home_path = os.path.expanduser("~\\.ollama\\models")
        else:  # Linux/Mac
            home_path = os.path.expanduser("~/.ollama/models")
        
        if pane == 'left':
            self.left_path.set(home_path)
        else:
            self.right_path.set(home_path)
        self.refresh_pane(pane)
        
    def refresh_both(self):
        self.refresh_pane('left')
        self.refresh_pane('right')
        
    def refresh_pane(self, pane):
        self.status_var.set(f"Refreshing {pane} pane...")
        self.root.update()
        
        # Run in thread to prevent UI freezing
        thread = threading.Thread(target=self._refresh_pane_thread, args=(pane,))
        thread.daemon = True
        thread.start()
        
    def _refresh_pane_thread(self, pane):
        try:
            path = self.left_path.get() if pane == 'left' else self.right_path.get()
            models = self.scan_ollama_models(path)
            
            if pane == 'left':
                self.left_models = models
                tree = self.left_tree
            else:
                self.right_models = models
                tree = self.right_tree
            
            # Update UI in main thread
            self.root.after(0, self._update_tree_display, tree, models, pane)
            
        except Exception as e:
            self.root.after(0, lambda: self.status_var.set(f"Error refreshing {pane}: {str(e)}"))
            
    def _update_tree_display(self, tree, models, pane):
        # Clear existing items
        for item in tree.get_children():
            tree.delete(item)
            
        # Add models and blobs
        for model_name, model_data in models.items():
            # Add model root node
            model_item = tree.insert("", "end", text=model_name, values=("", "Model"))
            
            # Add versions
            for version, version_data in model_data.get('versions', {}).items():
                version_item = tree.insert(model_item, "end", text=f"{version}", values=("", "Version"))
                
                # Add blobs
                for blob_info in version_data.get('blobs', []):
                    blob_name = blob_info['name']
                    blob_size = self.format_size(blob_info['size'])
                    blob_status = "✓" if blob_info['exists'] else "✗"
                    tree.insert(version_item, "end", text=blob_name, values=(blob_size, blob_status))
                    
        self.status_var.set(f"Refreshed {pane} pane - {len(models)} models found")
        
    def scan_ollama_models(self, base_path: str) -> Dict:
        """Scan for Ollama models in the given path"""
        models = {}
        
        if not os.path.exists(base_path):
            return models
            
        # Look for manifests
        manifests_path = os.path.join(base_path, "manifests", "registry.ollama.ai", "library")
        blobs_path = os.path.join(base_path, "blobs")
        
        if not os.path.exists(manifests_path):
            return models
            
        # Get all blob files for quick lookup
        existing_blobs = set()
        if os.path.exists(blobs_path):
            existing_blobs = set(os.listdir(blobs_path))
            
        # Scan model directories
        for model_name in os.listdir(manifests_path):
            model_dir = os.path.join(manifests_path, model_name)
            if not os.path.isdir(model_dir):
                continue
                
            models[model_name] = {'versions': {}}
            
            # Scan version files
            for version_file in os.listdir(model_dir):
                version_path = os.path.join(model_dir, version_file)
                if not os.path.isfile(version_path):
                    continue
                    
                try:
                    with open(version_path, 'r', encoding='utf-8') as f:
                        manifest = json.load(f)
                        
                    # Parse manifest for blobs
                    blobs = []
                    
                    # Check config blob
                    if 'config' in manifest:
                        config_digest = manifest['config']['digest']
                        blob_name = f"sha256-{config_digest.split(':')[1]}"
                        blob_size = manifest['config'].get('size', 0)
                        blobs.append({
                            'name': blob_name,
                            'size': blob_size,
                            'exists': blob_name in existing_blobs,
                            'type': 'config'
                        })
                        
                    # Check layer blobs
                    if 'layers' in manifest:
                        for layer in manifest['layers']:
                            layer_digest = layer['digest']
                            blob_name = f"sha256-{layer_digest.split(':')[1]}"
                            blob_size = layer.get('size', 0)
                            blobs.append({
                                'name': blob_name,
                                'size': blob_size,
                                'exists': blob_name in existing_blobs,
                                'type': layer.get('mediaType', 'layer')
                            })
                            
                    models[model_name]['versions'][version_file] = {
                        'blobs': blobs,
                        'manifest_path': version_path
                    }
                    
                except (json.JSONDecodeError, KeyError, Exception) as e:
                    print(f"Error parsing {version_path}: {e}")
                    continue
                    
        return models
        
    def format_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        i = 0
        while size_bytes >= 1024 and i < len(units) - 1:
            size_bytes /= 1024
            i += 1
            
        return f"{size_bytes:.1f} {units[i]}"
        
    def show_context_menu(self, event, pane):
        tree = self.left_tree if pane == 'left' else self.right_tree
        context_menu = self.left_context_menu if pane == 'left' else self.right_context_menu
        
        # Select item under cursor
        item = tree.identify_row(event.y)
        if item:
            tree.selection_set(item)
            context_menu.post(event.x_root, event.y_root)
            
    def copy_left_to_right(self):
        self.copy_selected('left')
        
    def copy_right_to_left(self):
        self.copy_selected('right')
        
    def copy_selected(self, from_pane):
        # Get selected items
        tree = self.left_tree if from_pane == 'left' else self.right_tree
        selected = tree.selection()
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select items to copy")
            return
            
        # Get destination path
        dest_path = self.right_path.get() if from_pane == 'left' else self.left_path.get()
        
        if not os.path.exists(dest_path):
            messagebox.showerror("Error", f"Destination path does not exist: {dest_path}")
            return
            
        self.status_var.set("Copying files...")
        self.root.update()
        
        # Run copy operation in thread
        thread = threading.Thread(target=self._copy_files_thread, args=(from_pane, selected, dest_path))
        thread.daemon = True
        thread.start()
        
    def _copy_files_thread(self, from_pane, selected_items, dest_path):
        try:
            src_path = self.left_path.get() if from_pane == 'left' else self.right_path.get()
            models = self.left_models if from_pane == 'left' else self.right_models
            tree = self.left_tree if from_pane == 'left' else self.right_tree
            
            copied_count = 0
            copied_models = set()
            
            for item in selected_items:
                item_text = tree.item(item, 'text')
                parent = tree.parent(item)
                grandparent = tree.parent(parent) if parent else None
                
                # Determine what level we're copying from
                if not parent:  # Root node - copy entire model
                    model_name = item_text
                    if model_name in models:
                        for version, version_data in models[model_name]['versions'].items():
                            copied_count += self._copy_model_version(src_path, dest_path, model_name, version, version_data)
                            copied_models.add(f"{model_name}:{version}")
                            
                elif not grandparent:  # Version node - copy specific version
                    model_name = tree.item(parent, 'text')
                    version = item_text
                    if model_name in models and version in models[model_name]['versions']:
                        version_data = models[model_name]['versions'][version]
                        copied_count += self._copy_model_version(src_path, dest_path, model_name, version, version_data)
                        copied_models.add(f"{model_name}:{version}")
                        
                else:  # Individual blob file
                    blob_name = item_text
                    src_blob_path = os.path.join(src_path, "blobs", blob_name)
                    dest_blob_path = os.path.join(dest_path, "blobs", blob_name)
                    
                    if os.path.exists(src_blob_path):
                        os.makedirs(os.path.dirname(dest_blob_path), exist_ok=True)
                        shutil.copy2(src_blob_path, dest_blob_path)
                        copied_count += 1
                        
            models_text = f" ({len(copied_models)} models)" if copied_models else ""
            self.root.after(0, lambda: self.status_var.set(f"Copied {copied_count} files{models_text}"))
            
            # Refresh destination pane
            dest_pane = 'right' if from_pane == 'left' else 'left'
            self.root.after(100, lambda: self.refresh_pane(dest_pane))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Copy Error", f"Error copying files: {str(e)}"))
            
    def _copy_model_version(self, src_path, dest_path, model_name, version, version_data):
        """Copy a complete model version including manifest and blobs"""
        copied_count = 0
        
        try:
            # Copy manifest file
            src_manifest = version_data['manifest_path']
            dest_manifest_dir = os.path.join(dest_path, "manifests", "registry.ollama.ai", "library", model_name)
            dest_manifest_path = os.path.join(dest_manifest_dir, version)
            
            os.makedirs(dest_manifest_dir, exist_ok=True)
            shutil.copy2(src_manifest, dest_manifest_path)
            
            # Copy all blobs for this version
            for blob_info in version_data['blobs']:
                blob_name = blob_info['name']
                src_blob_path = os.path.join(src_path, "blobs", blob_name)
                dest_blob_path = os.path.join(dest_path, "blobs", blob_name)
                
                if os.path.exists(src_blob_path):
                    os.makedirs(os.path.dirname(dest_blob_path), exist_ok=True)
                    shutil.copy2(src_blob_path, dest_blob_path)
                    copied_count += 1
                    
        except Exception as e:
            print(f"Error copying {model_name}:{version}: {e}")
            
        return copied_count
            
    def delete_selected(self, pane=None):
        if pane is None:
            # Called from toolbar - determine which pane has focus
            if self.left_tree.selection():
                pane = 'left'
            elif self.right_tree.selection():
                pane = 'right'
            else:
                messagebox.showwarning("No Selection", "Please select items to delete")
                return
                
        tree = self.left_tree if pane == 'left' else self.right_tree
        selected = tree.selection()
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select items to delete")
            return
            
        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete {len(selected)} selected items?"):
            return
            
        self.status_var.set("Deleting files...")
        self.root.update()
        
        # Run delete operation in thread
        thread = threading.Thread(target=self._delete_files_thread, args=(pane, selected))
        thread.daemon = True
        thread.start()
        
    def _delete_files_thread(self, pane, selected_items):
        try:
            src_path = self.left_path.get() if pane == 'left' else self.right_path.get()
            tree = self.left_tree if pane == 'left' else self.right_tree
            
            deleted_count = 0
            
            for item in selected_items:
                item_text = tree.item(item, 'text')
                parent = tree.parent(item)
                
                if parent:  # This is a blob file
                    blob_name = item_text
                    blob_path = os.path.join(src_path, "blobs", blob_name)
                    
                    if os.path.exists(blob_path):
                        os.remove(blob_path)
                        deleted_count += 1
                        
            self.root.after(0, lambda: self.status_var.set(f"Deleted {deleted_count} files"))
            
            # Refresh current pane
            self.root.after(100, lambda: self.refresh_pane(pane))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Delete Error", f"Error deleting files: {str(e)}"))
            
    def show_properties(self, pane):
        tree = self.left_tree if pane == 'left' else self.right_tree
        selected = tree.selection()
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select an item to view properties")
            return
            
        item = selected[0]
        item_text = tree.item(item, 'text')
        item_values = tree.item(item, 'values')
        
        # Create properties window
        props_window = tk.Toplevel(self.root)
        props_window.title(f"Properties - {item_text}")
        props_window.geometry("400x300")
        
        # Properties text widget
        props_text = tk.Text(props_window, wrap=tk.WORD)
        props_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Get detailed info
        props_info = f"Name: {item_text}\n"
        props_info += f"Size: {item_values[0] if item_values else 'N/A'}\n"
        props_info += f"Status: {item_values[1] if len(item_values) > 1 else 'N/A'}\n"
        props_info += f"Pane: {pane.capitalize()}\n"
        props_info += f"Path: {self.left_path.get() if pane == 'left' else self.right_path.get()}\n"
        
        props_text.insert(tk.END, props_info)
        props_text.config(state=tk.DISABLED)

def main():
    root = tk.Tk()
    app = OllamaModelManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()