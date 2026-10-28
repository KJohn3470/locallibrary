# taskflow/api.py
from ninja import NinjaAPI

from accounts.auth import JWTAuth

api = NinjaAPI(title="TaskFlow API", urls_namespace="taskflow", auth=JWTAuth())

api.add_router("/auth", "accounts.api.router")
api.add_router("/projects", "projects.api.router")
api.add_router("/projects/{project_id}/tasks", "tasks.api.router")