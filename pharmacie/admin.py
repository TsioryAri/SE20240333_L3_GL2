from django.contrib import admin
from .models import *
admin.site.site_header = "PharmaGest — Administration"
admin.site.site_title = "PharmaGest"
admin.site.index_title = "Gestion de la pharmacie"

@admin.register(Medicament)
class MedicamentAdmin(admin.ModelAdmin):
    list_display = ("nom", "code", "categorie", "prix_vente", "seuil_alerte", "actif")
    search_fields = ("nom", "code", "code_barres")
    list_filter = ("categorie", "actif")

@admin.register(LotStock)
class LotStockAdmin(admin.ModelAdmin):
    list_display = ("medicament", "numero_lot", "date_peremption", "quantite", "fournisseur")
    list_filter = ("date_peremption",)
    search_fields = ("medicament__nom", "numero_lot")

for model in [Categorie, Fournisseur, Client, MouvementStock, Achat, LigneAchat, Vente, LigneVente, RetourVente, JournalAudit]:
    try: admin.site.register(model)
    except admin.sites.AlreadyRegistered: pass
