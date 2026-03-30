import os
import subprocess
import platform

class NetworkManager:
    @staticmethod
    def mount_share(share_path: str, username: str = "", password: str = ""):
        system = platform.system().lower()
        
        if system == "windows":
            # Sanitize path: Windows expects backslashes for UNC
            share_path = share_path.replace("/", "\\")
            if not share_path.startswith("\\\\"):
                # Handle cases like "192.168.1.1\share" missing the \\ prefix
                share_path = "\\\\" + share_path.lstrip("\\")

            # Windows natively binds via net use
            cmd = ["net", "use", share_path]
            if password:
                cmd.append(password)
            if username:
                cmd.extend(["/user:" + username])
                
            print(f"[Network] Executing: {' '.join(cmd[:3])} /user:{username} <PASS_HIDDEN>")
            result = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
            
            # Already mounted check: "already exists", "bereits vorhanden", "erfolgreich" (success)
            stdout_l = result.stdout.lower()
            stderr_l = result.stderr.lower()
            already_mounted = "available" in stdout_l or "vorhanden" in stdout_l or "exists" in stdout_l or "erfolgreich" in stdout_l
            
            if result.returncode != 0 and not already_mounted:
                error_msg = result.stderr or result.stdout
                print(f"[Network] Windows Mount Failed: {error_msg}")
                raise RuntimeError(f"Windows Mount Failed: {error_msg}")
            
            NetworkManager.cache_mount(share_path, username, password)
            return True
            
        elif system in ["linux", "darwin"]:
            # Linux requires an explicit local mount point. 
            # We map standard SMB/CIFS directly to /mnt/autosubs/share_hash
            import hashlib
            safe_hash = hashlib.md5(share_path.encode()).hexdigest()[:8]
            mount_point = f"/mnt/autosubs_{safe_hash}"
            
            os.makedirs(mount_point, exist_ok=True)
            
            # Use mount.cifs
            # Note: This requires the backend to be run under a user with mount permissions or root.
            cmd = ["mount", "-t", "cifs", share_path, mount_point]
            
            opts = []
            if username:
                opts.append(f"username={username}")
            if password:
                opts.append(f"password={password}")
            
            # Common options to prevent permission locked folders
            opts.append("file_mode=0777")
            opts.append("dir_mode=0777")
            
            if opts:
                cmd.extend(["-o", ",".join(opts)])
                
            # Execute with sudo if not root, hoping passwordless sudo is configured, otherwise assumes root
            if os.geteuid() != 0:
                cmd = ["sudo"] + cmd
                
            result = subprocess.run(cmd, capture_output=True, text=True, errors='replace')
            if result.returncode != 0:
                raise RuntimeError(f"Linux/Mac Mount Failed. AutoSubs may lack sudo/root privileges: {result.stderr or result.stdout}")
            
            NetworkManager.cache_mount(share_path, username, password)
            return mount_point
            
        else:
            raise RuntimeError(f"Unsupported OS: {system}")

    @staticmethod
    def _get_cache_path():
        b_dir = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(b_dir, "mount_cache.json")

    @staticmethod
    def cache_mount(share_path: str, username: str = "", password: str = ""):
        import json
        c_path = NetworkManager._get_cache_path()
        data = {}
        if os.path.exists(c_path):
            try:
                with open(c_path, "r") as f:
                    data = json.load(f)
            except:
                pass
        
        data[share_path] = {"username": username, "password": password}
        with open(c_path, "w") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def get_mounts() -> dict:
        import json
        c_path = NetworkManager._get_cache_path()
        if not os.path.exists(c_path):
            return {}
        try:
            with open(c_path, "r") as f:
                return json.load(f)
        except:
            return {}

    @staticmethod
    def unmount_share(share_path: str):
        system = platform.system().lower()
        import json
        
        # 1. Attempt OS-level unmount
        try:
            if system == "windows":
                # net use <path> /delete
                subprocess.run(["net", "use", share_path, "/delete", "/y"], capture_output=True)
            elif system in ["linux", "darwin"]:
                import hashlib
                safe_hash = hashlib.md5(share_path.encode()).hexdigest()[:8]
                mount_point = f"/mnt/autosubs_{safe_hash}"
                if os.path.ismount(mount_point):
                    cmd = ["umount", "-l", mount_point]
                    if os.getuid() != 0:
                        cmd = ["sudo"] + cmd
                    subprocess.run(cmd, capture_output=True)
        except Exception as e:
            print(f"[Network] OS Unmount Warning for {share_path}: {e}")

        # 2. Update Cache
        c_path = NetworkManager._get_cache_path()
        if os.path.exists(c_path):
            try:
                with open(c_path, "r") as f:
                    data = json.load(f)
                if share_path in data:
                    del data[share_path]
                    with open(c_path, "w") as f:
                        json.dump(data, f, indent=4)
            except Exception as e:
                print(f"[Network] Cache update failed for {share_path}: {e}")

    @staticmethod
    def restore_mounts():
        import json
        c_path = NetworkManager._get_cache_path()
        if not os.path.exists(c_path):
            return
            
        try:
            with open(c_path, "r") as f:
                data = json.load(f)
                
            for path, creds in data.items():
                print(f"[BOOT] Restoring Network Share: {path}")
                try:
                    NetworkManager.mount_share(path, creds.get("username", ""), creds.get("password", ""))
                except Exception as ex:
                    print(f"[BOOT] Warning: Could not remount {path}: {ex}")
        except Exception as e:
            print(f"[BOOT] Error restoring mount cache: {e}")

    @staticmethod
    def is_reachable(share_path: str) -> bool:
        """Check if a network share is currently reachable without hanging indefinitely."""
        system = platform.system().lower()
        try:
            if system == "windows":
                # Use 'net use' to check status, as it's faster than os.path.exists on remote SMB
                # Check for the specific share in the output
                result = subprocess.run(["net", "use"], capture_output=True, text=True, errors='replace', timeout=5)
                # If the share_path is found and doesn't say 'Disconnected' or similar failure
                if share_path.lower() in result.stdout.lower():
                    # Further check if we can actually list it (very fast if net use is OK)
                    return os.path.exists(share_path)
                return False
            else:
                import hashlib
                safe_hash = hashlib.md5(share_path.encode()).hexdigest()[:8]
                mount_point = f"/mnt/autosubs_{safe_hash}"
                if not os.path.exists(mount_point):
                    return False
                # Check if it's actually a mount point and readable
                return os.path.ismount(mount_point) and os.access(mount_point, os.R_OK)
        except Exception as e:
            print(f"[Network] Reachability check failed for {share_path}: {e}")
            return False

    @staticmethod
    def get_mount_statuses() -> dict:
        """Get all cached mounts with an added 'online' boolean status."""
        mounts = NetworkManager.get_mounts()
        statuses = {}
        for path, creds in mounts.items():
            # Robustness check to avoid TypeError: 'str' object is not a mapping
            if not isinstance(creds, dict):
                creds = {"username": str(creds), "password": ""}
                
            statuses[path] = {
                **creds,
                "online": NetworkManager.is_reachable(path)
            }
        return statuses

network_manager = NetworkManager()
