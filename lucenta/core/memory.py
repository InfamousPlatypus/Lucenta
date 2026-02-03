import os
import logging
from typing import Optional

try:
    import grp
except ImportError:
    grp = None

class ProjectMemory:
    def __init__(self, base_path: str = "./lucenta-shared", group_name: str = "lucenta-shared"):
        self.base_path = os.path.abspath(base_path)
        self.group_name = group_name
        self._ensure_base_path()

    def _ensure_base_path(self):
        if not os.path.exists(self.base_path):
            try:
                os.makedirs(self.base_path, mode=0o775, exist_ok=True)
                self._apply_group_permissions(self.base_path)
            except Exception as e:
                logging.error(f"Failed to create base path {self.base_path}: {e}")

    def _apply_group_permissions(self, path: str):
        if grp is None:
            return
        try:
            gid = grp.getgrnam(self.group_name).gr_gid
            os.chown(path, -1, gid)
            # Ensure group write bit is set
            mode = os.stat(path).st_mode
            os.chmod(path, mode | 0o070)
        except KeyError:
            logging.warning(f"Group '{self.group_name}' does not exist. Skipping chown.")
        except Exception as e:
            logging.warning(f"Failed to apply group permissions to {path}: {e}")

    def create_project(self, project_name: str) -> str:
        project_path = os.path.join(self.base_path, project_name)
        if not os.path.exists(project_path):
            os.makedirs(project_path, mode=0o775, exist_ok=True)
            self._apply_group_permissions(project_path)
        return project_path

    def store_result(self, project_name: str, filename: str, content: str) -> str:
        project_path = self.create_project(project_name)
        file_path = os.path.join(project_path, filename)
        with open(file_path, 'w') as f:
            f.write(content)

        # Ensure group permissions
        try:
            os.chmod(file_path, 0o664)
            self._apply_group_permissions(file_path)
        except Exception as e:
            logging.warning(f"Failed to set permissions for {file_path}: {e}")

        return file_path

    def list_projects(self):
        if not os.path.exists(self.base_path):
            return []
        return [d for d in os.listdir(self.base_path) if os.path.isdir(os.path.join(self.base_path, d))]
