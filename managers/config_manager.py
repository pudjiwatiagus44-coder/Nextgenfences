import json
import os
import shutil
import sys

CONFIG_FILE = "nextgen_config.json"

class ConfigManager:
    def __init__(self):
        # Determine base directory
        if getattr(sys, 'frozen', False):
            # If running as compiled exe
            base_dir = os.path.dirname(sys.executable)
        else:
            # If running from source
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            
        self.config_path = os.path.join(base_dir, CONFIG_FILE)
        self.data = self.load_config()
        
        # Initialize root_dir from config or default
        default_root = os.path.join(os.path.expanduser("~"), "Documents", "MyFences")
        self.root_dir = self.data.get("root_dir", default_root)
        
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8-sig') as f:
                    data = json.load(f)
                    
                    # Ensure root_dir is in data if present, otherwise we handle it in __init__
                    # But fences paths might need adjustment if they are relative? 
                    # For now, we assume absolute paths in config, but we want to support moving.
                    
                    return data
            except Exception as e:
                print(f"Error loading config: {e}")
                return self.default_config()
        else:
            return self.default_config()

    def default_config(self):
        # Default with just one fence to start
        return {
            "root_dir": os.path.join(os.path.expanduser("~"), "Documents", "MyFences"),
            "fences": [],
            "file_mapping": {},
            "rules": {}
        }

    def save_config(self):
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get_fence_by_id(self, fence_id):
        for fence in self.data["fences"]:
            if fence["id"] == fence_id:
                return fence
        return None

    def update_fence_property(self, fence_id, key, value):
        for fence in self.data["fences"]:
            if fence["id"] == fence_id:
                fence[key] = value
                self.save_config()
                return

    def add_fence(self, title, path=None):
        import uuid
        new_id = str(uuid.uuid4())[:8]
        
        if path:
            new_path = path
        else:
            new_path = os.path.join(self.root_dir, title)
            if not os.path.exists(new_path):
                os.makedirs(new_path)
            
        self.data["fences"].append({
            "id": new_id,
            "title": title,
            "geometry": [200, 200, 300, 200],
            "opacity": 0.1,
            "view_mode": "icon_medium",
            "sort_by": "name",
            "sort_order": "asc",
            "path": new_path
        })
        self.save_config()
        return new_id
    
    def remove_fence(self, fence_id):
        self.data["fences"] = [f for f in self.data["fences"] if f["id"] != fence_id]
        self.save_config()

    def update_root_dir(self, new_root_dir):
        if not new_root_dir or new_root_dir == self.root_dir:
            return

        try:
            # 1. Create new root if not exists
            if not os.path.exists(new_root_dir):
                os.makedirs(new_root_dir)

            # 2. Move existing fences (ONLY if they are in the old root_dir)
            for fence in self.data["fences"]:
                old_path = fence["path"]
                
                # Check if this fence is inside the current root_dir
                # Use os.path.commonpath to check parentage safely
                try:
                    # Normalize paths for comparison
                    abs_old_path = os.path.abspath(old_path)
                    abs_root_dir = os.path.abspath(self.root_dir)
                    
                    if os.path.commonpath([abs_root_dir, abs_old_path]) == abs_root_dir:
                        # It IS inside the old root. Move it.
                        folder_name = os.path.basename(old_path)
                        new_path = os.path.join(new_root_dir, folder_name)

                        if os.path.exists(old_path):
                            if not os.path.exists(new_path):
                                shutil.move(old_path, new_path)
                            else:
                                # Merge contents
                                for item in os.listdir(old_path):
                                    s = os.path.join(old_path, item)
                                    d = os.path.join(new_path, item)
                                    if os.path.exists(d):
                                        continue 
                                    shutil.move(s, d)
                                try:
                                    os.rmdir(old_path)
                                except:
                                    pass
                        
                        # Update path in config
                        fence["path"] = new_path
                    else:
                        # It is OUTSIDE the root dir (Custom Fence). Do NOT move.
                        pass
                except Exception as ex:
                    print(f"Skipping fence move check for {old_path}: {ex}")

            # 3. Update root_dir in config
            self.root_dir = new_root_dir
            self.data["root_dir"] = new_root_dir
            self.save_config()
            
            return True
        except Exception as e:
            print(f"Error updating root dir: {e}")
            return False
