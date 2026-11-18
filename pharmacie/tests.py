from datetime import date, timedelta
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from .models import Categorie, Medicament, LotStock, Fournisseur, LigneVente
from .services import enregistrer_vente, recevoir_achat, enregistrer_retour, ajuster_stock

class PharmaGestServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="test", password="testpass123")
        self.cat = Categorie.objects.create(nom="Antalgiques")
        self.med = Medicament.objects.create(nom="Paracetamol", code="PARA", categorie=self.cat, prix_achat=100, prix_vente=150)
        self.fournisseur = Fournisseur.objects.create(nom="Grossiste test")
        self.lot = LotStock.objects.create(medicament=self.med, numero_lot="LOT1", date_peremption=date.today()+timedelta(days=200), quantite=10, cout_unitaire=100)

    def test_vente_decremente_stock_et_calcule_total(self):
        vente = enregistrer_vente(utilisateur=self.user, lignes=[{"medicament": self.med, "quantite": 3}])
        self.assertEqual(vente.total, Decimal("450.00"))
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 7)

    def test_vente_superieure_au_stock_refusee_sans_effet_partiel(self):
        with self.assertRaises(ValidationError):
            enregistrer_vente(utilisateur=self.user, lignes=[{"medicament": self.med, "quantite": 99}])
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 10)

    def test_vente_utilise_dabord_le_lot_qui_perime_le_plus_tot(self):
        lot2 = LotStock.objects.create(medicament=self.med, numero_lot="LOT2", date_peremption=date.today()+timedelta(days=300), quantite=10, cout_unitaire=90)
        vente = enregistrer_vente(utilisateur=self.user, lignes=[{"medicament": self.med, "quantite": 12}])
        self.lot.refresh_from_db(); lot2.refresh_from_db()
        self.assertEqual(self.lot.quantite, 0)
        self.assertEqual(lot2.quantite, 8)

    def test_reception_achat_ajoute_au_stock(self):
        achat = recevoir_achat(utilisateur=self.user, fournisseur=self.fournisseur, reference="ACH-TEST-1", lignes=[{
            "medicament": self.med, "numero_lot": "LOT-ACHAT", "date_peremption": date.today()+timedelta(days=400),
            "quantite": 5, "prix_unitaire": Decimal("80.00")
        }])
        self.assertEqual(achat.lignes.count(), 1)
        lot = LotStock.objects.get(medicament=self.med, numero_lot="LOT-ACHAT")
        self.assertEqual(lot.quantite, 5)

    def test_retour_reintegre_stock_et_bloque_surretour(self):
        vente = enregistrer_vente(utilisateur=self.user, lignes=[{"medicament": self.med, "quantite": 4}])
        ligne = vente.lignes.get()
        enregistrer_retour(utilisateur=self.user, ligne=ligne, quantite=2, motif="Boîte intacte", reintegrer=True)
        self.lot.refresh_from_db()
        self.assertEqual(self.lot.quantite, 8)
        with self.assertRaises(ValidationError):
            enregistrer_retour(utilisateur=self.user, ligne=ligne, quantite=3, motif="Sur-retour", reintegrer=False)

    def test_ajustement_inventaire_trace_la_variation(self):
        lot = ajuster_stock(utilisateur=self.user, lot=self.lot, quantite_reelle=8, commentaire="Comptage physique")
        self.assertEqual(lot.quantite, 8)
        self.assertEqual(lot.mouvementstock_set.latest("date_mouvement").quantite, -2)

    def test_vente_ne_prend_pas_un_lot_perime(self):
        self.lot.date_peremption = date.today() - timedelta(days=1)
        self.lot.save(update_fields=["date_peremption"])
        with self.assertRaises(ValidationError):
            enregistrer_vente(utilisateur=self.user, lignes=[{"medicament": self.med, "quantite": 1}])
