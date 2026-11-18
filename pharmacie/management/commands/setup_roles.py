from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from pharmacie.models import Categorie, Medicament, Fournisseur, Client, LotStock, Achat, Vente, RetourVente, MouvementStock, JournalAudit

class Command(BaseCommand):
    help = "Crée les groupes de rôles PharmaGest et leurs permissions Django de base."
    def handle(self, *args, **options):
        models = [Categorie, Medicament, Fournisseur, Client, LotStock, Achat, Vente, RetourVente, MouvementStock, JournalAudit]
        permissions = {}
        for model in models:
            ct = ContentType.objects.get_for_model(model)
            for p in Permission.objects.filter(content_type=ct):
                permissions[p.codename] = p
        role_map = {
            "Administrateur": list(permissions.values()),
            "Pharmacien": [p for p in permissions.values() if p.codename.startswith(("view_", "add_", "change_"))],
            "Gestionnaire de stock": [p for p in permissions.values() if p.codename.endswith(("medicament", "categorie", "fournisseur", "lotstock", "achat", "mouvementstock")) and p.codename.startswith(("view_", "add_", "change_"))],
            "Caissier": [p for p in permissions.values() if p.codename.startswith(("view_", "add_")) and any(x in p.codename for x in ("client", "vente", "lignevente", "retourvente"))],
        }
        for name, perms in role_map.items():
            group, _ = Group.objects.get_or_create(name=name)
            group.permissions.set(perms)
            self.stdout.write(self.style.SUCCESS(f"Rôle configuré : {name}"))
