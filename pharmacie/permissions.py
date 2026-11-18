from functools import wraps
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

ROLE_PERMISSIONS = {
    "Administrateur": {"all"},
    "Pharmacien": {"dashboard", "catalogue", "clients", "fournisseurs", "achats", "stock", "ventes", "retours", "rapports"},
    "Gestionnaire de stock": {"dashboard", "catalogue", "fournisseurs", "achats", "stock", "rapports"},
    "Caissier": {"dashboard", "clients", "ventes", "retours"},
}

def role_required(*permissions):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if request.user.is_superuser or request.user.groups.filter(name="Administrateur").exists():
                return view_func(request, *args, **kwargs)
            allowed = set()
            for group in request.user.groups.values_list("name", flat=True):
                allowed.update(ROLE_PERMISSIONS.get(group, set()))
            if "all" not in allowed and not set(permissions).issubset(allowed):
                raise PermissionDenied("Votre rôle ne permet pas cette opération.")
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


from django.contrib.auth.mixins import AccessMixin

class RoleRequiredMixin(AccessMixin):
    required_roles = ()
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.is_superuser or request.user.groups.filter(name="Administrateur").exists():
            return super().dispatch(request, *args, **kwargs)
        allowed = set()
        for group in request.user.groups.values_list("name", flat=True):
            allowed.update(ROLE_PERMISSIONS.get(group, set()))
        if "all" not in allowed and not set(self.required_roles).issubset(allowed):
            raise PermissionDenied("Votre rôle ne permet pas cette opération.")
        return super().dispatch(request, *args, **kwargs)
