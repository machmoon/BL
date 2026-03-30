from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db.models.signals import post_migrate, post_save
from django.dispatch import receiver

from .models import LibraryProfile, LibraryRole


ROLE_PERMISSION_MAP = {
    "Patron": [
        "view_bookinventory",
        "view_bookcopy",
        "view_loan",
        "view_holdrequest",
    ],
    "Librarian": [
        "view_bookinventory",
        "add_bookinventory",
        "change_bookinventory",
        "view_bookcopy",
        "add_bookcopy",
        "change_bookcopy",
        "manage_inventory",
        "view_loan",
        "add_loan",
        "change_loan",
        "manage_loans",
        "view_holdrequest",
        "change_holdrequest",
        "approve_holds",
    ],
    "Curator": [
        "view_bookinventory",
        "add_bookinventory",
        "change_bookinventory",
        "delete_bookinventory",
        "view_bookcopy",
        "add_bookcopy",
        "change_bookcopy",
        "delete_bookcopy",
        "manage_inventory",
        "view_holdrequest",
        "approve_holds",
    ],
    "Admin": [],
}


@receiver(post_save, sender=get_user_model())
def ensure_library_profile(sender, instance, created, **kwargs):
    if not created:
        return

    profile, was_created = LibraryProfile.objects.get_or_create(
        user=instance,
        defaults={
            "role": LibraryRole.PATRON,
            "card_number": f"CARD-{instance.pk:06d}",
        },
    )
    if not was_created and not profile.card_number:
        profile.card_number = f"CARD-{instance.pk:06d}"
        profile.save(update_fields=["card_number"])


@receiver(post_migrate)
def ensure_default_groups(sender, **kwargs):
    if sender.name != "core":
        return

    for group_name, permission_codenames in ROLE_PERMISSION_MAP.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        if group_name == "Admin":
            group.permissions.set(Permission.objects.all())
            continue

        permissions = Permission.objects.filter(codename__in=permission_codenames)
        group.permissions.set(permissions)
