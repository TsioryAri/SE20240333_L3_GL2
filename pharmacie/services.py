from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import LotStock, MouvementStock, Vente, LigneVente, JournalAudit, Achat, LigneAchat, RetourVente

@transaction.atomic
def enregistrer_vente(*, utilisateur, lignes, client=None, mode_paiement="ESPECES"):
    if not lignes:
        raise ValidationError("Le panier est vide.")
    if mode_paiement not in dict(Vente.MODES):
        raise ValidationError("Mode de paiement invalide.")
    vente = Vente.objects.create(
        reference=f"V-{timezone.now():%Y%m%d%H%M%S%f}",
        client=client, mode_paiement=mode_paiement, utilisateur=utilisateur
    )
    total = Decimal("0.00")
    for item in lignes:
        medicament, restant = item["medicament"], int(item["quantite"])
        if restant < 1:
            raise ValidationError("La quantité doit être positive.")
        lots = list(LotStock.objects.select_for_update().filter(
            medicament=medicament, quantite__gt=0,
            date_peremption__gte=timezone.localdate()
        ).order_by("date_peremption", "id"))
        disponible = sum(l.quantite for l in lots)
        if disponible < restant:
            raise ValidationError(f"Stock insuffisant pour {medicament.nom}. Disponible : {disponible}.")
        for lot in lots:
            if not restant:
                break
            pris = min(lot.quantite, restant)
            lot.quantite -= pris
            lot.save(update_fields=["quantite"])
            LigneVente.objects.create(
                vente=vente, medicament=medicament, lot=lot,
                quantite=pris, prix_unitaire=medicament.prix_vente
            )
            MouvementStock.objects.create(
                medicament=medicament, lot=lot, type_mouvement="SORTIE",
                quantite=-pris, reference=vente.reference, utilisateur=utilisateur
            )
            total += medicament.prix_vente * pris
            restant -= pris
    vente.total = total
    vente.save(update_fields=["total"])
    JournalAudit.objects.create(
        utilisateur=utilisateur, action="VENTE_VALIDEE",
        objet=vente.reference, details=f"Total : {total}"
    )
    return vente

@transaction.atomic
def recevoir_achat(*, utilisateur, fournisseur, reference, lignes, notes=""):
    if not lignes:
        raise ValidationError("Ajoutez au moins une ligne d'achat.")
    achat = Achat.objects.create(
        fournisseur=fournisseur, reference=reference, statut="RECU",
        cree_par=utilisateur, notes=notes
    )
    for item in lignes:
        med, qty = item["medicament"], int(item["quantite"])
        if qty < 1:
            raise ValidationError("La quantité reçue doit être positive.")
        if item["date_peremption"] <= timezone.localdate():
            raise ValidationError(f"Le lot {item['numero_lot']} est déjà périmé ou expire aujourd'hui.")
        if item["prix_unitaire"] < 0:
            raise ValidationError("Le prix d'achat ne peut pas être négatif.")
        ligne = LigneAchat.objects.create(
            achat=achat, medicament=med, numero_lot=item["numero_lot"],
            date_peremption=item["date_peremption"], quantite=qty,
            prix_unitaire=item["prix_unitaire"]
        )
        lot, created = LotStock.objects.get_or_create(
            medicament=med, numero_lot=ligne.numero_lot,
            defaults={
                "date_peremption": ligne.date_peremption, "quantite": 0,
                "cout_unitaire": ligne.prix_unitaire, "fournisseur": fournisseur
            }
        )
        if not created and lot.date_peremption != ligne.date_peremption:
            raise ValidationError("La date de péremption du lot existant ne correspond pas.")
        lot.quantite += qty
        lot.cout_unitaire = ligne.prix_unitaire
        lot.fournisseur = fournisseur
        lot.save()
        MouvementStock.objects.create(
            medicament=med, lot=lot, type_mouvement="ENTREE",
            quantite=qty, reference=reference, utilisateur=utilisateur
        )
    JournalAudit.objects.create(utilisateur=utilisateur, action="ACHAT_RECU", objet=reference)
    return achat

@transaction.atomic
def enregistrer_retour(*, utilisateur, ligne, quantite, motif, reintegrer=False):
    ligne = LigneVente.objects.select_for_update().select_related("vente", "lot", "medicament").get(pk=ligne.pk)
    if ligne.vente.statut != "VALIDEE":
        raise ValidationError("Impossible de retourner une vente non validée.")
    quantite = int(quantite)
    deja = sum(r.quantite for r in ligne.vente.retours.filter(ligne=ligne))
    if quantite < 1 or deja + quantite > ligne.quantite:
        raise ValidationError("La quantité retournée dépasse la quantité vendue.")
    if reintegrer and ligne.lot.date_peremption < timezone.localdate():
        raise ValidationError("Un produit périmé ne peut pas être réintégré au stock vendable.")
    retour = RetourVente.objects.create(
        vente=ligne.vente, ligne=ligne, quantite=quantite,
        motif=motif, traite_par=utilisateur, stock_reintegre=reintegrer
    )
    if reintegrer:
        lot = LotStock.objects.select_for_update().get(pk=ligne.lot_id)
        lot.quantite += quantite
        lot.save(update_fields=["quantite"])
        MouvementStock.objects.create(
            medicament=ligne.medicament, lot=lot, type_mouvement="RETOUR",
            quantite=quantite, reference=ligne.vente.reference,
            commentaire=motif, utilisateur=utilisateur
        )
    JournalAudit.objects.create(
        utilisateur=utilisateur, action="RETOUR_ENREGISTRE",
        objet=ligne.vente.reference, details=f"{quantite} unité(s) — {motif}"
    )
    return retour

@transaction.atomic
def ajuster_stock(*, utilisateur, lot, quantite_reelle, commentaire):
    lot = LotStock.objects.select_for_update().select_related("medicament").get(pk=lot.pk)
    quantite_reelle = int(quantite_reelle)
    if quantite_reelle < 0:
        raise ValidationError("La quantité réelle ne peut pas être négative.")
    delta = quantite_reelle - lot.quantite
    if delta == 0:
        raise ValidationError("Aucun ajustement : la quantité est déjà correcte.")
    lot.quantite = quantite_reelle
    lot.save(update_fields=["quantite"])
    MouvementStock.objects.create(
        medicament=lot.medicament, lot=lot, type_mouvement="AJUSTEMENT",
        quantite=delta, reference=f"INV-{timezone.now():%Y%m%d%H%M%S%f}",
        commentaire=commentaire, utilisateur=utilisateur
    )
    JournalAudit.objects.create(
        utilisateur=utilisateur, action="STOCK_AJUSTE", objet=str(lot),
        details=f"Variation {delta:+d} ; quantité finale {quantite_reelle}. {commentaire}"
    )
    return lot
