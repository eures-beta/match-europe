from django.contrib.admin.apps import AdminConfig


class VersionedPermissionsAdminConfig(AdminConfig):
    def ready(self):
        super().ready()
        # Run after all admin modules, including Django auth, are registered.
        from django.contrib import admin
        from django.contrib.auth.models import Group

        if admin.site.is_registered(Group):
            admin.site.unregister(Group)
