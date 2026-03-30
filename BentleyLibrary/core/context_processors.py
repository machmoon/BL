from django.conf import settings

from .models import LibraryRole
from .presenters.books import ROLE_MANAGE_LOANS


def library_shell(request):
    user = getattr(request, "user", None)
    can_manage_loans = False
    if user and user.is_authenticated:
        role = getattr(getattr(user, "library_profile", None), "role", LibraryRole.PATRON)
        can_manage_loans = role in ROLE_MANAGE_LOANS or user.has_perm("core.manage_loans")

    return {
        "can_manage_loans": can_manage_loans,
        "auth0_enabled": getattr(settings, "AUTH0_ENABLED", False),
    }
