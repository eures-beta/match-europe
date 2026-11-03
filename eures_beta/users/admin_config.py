from django.contrib.admin.apps import AdminConfig


class VersionedPermissionsAdminConfig(AdminConfig):
    def ready(self):
        super().ready()
        # Run after all admin modules, including Django auth, are registered.
        from django.contrib import admin
        from .admin import register_framework_models

        register_framework_models(admin.site)
