from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from decimal import Decimal

class Categorie(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    class Meta:
        ordering = ["nom"]
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
    def __str__(self): return self.nom

class Medicament(models.Model):
    nom = models.CharField(max_length=180)
    code = models.CharField(max_length=50, unique=True)
    code_barres = models.CharField(max_length=80, blank=True)
    categorie = models.ForeignKey(Categorie, on_delete=models.PROTECT, related_name="medicaments")
    dosage = models.CharField(max_length=100, blank=True)
    forme = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    prix_achat = models.DecimalField(max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    prix_vente = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(0)])
    seuil_alerte = models.PositiveIntegerField(default=5)
    photo = models.ImageField(upload_to="medicaments/", blank=True, null=True)
    actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["nom"]
    def __str__(self): return f"{self.nom} ({self.code})"
    @property
    def stock_total(self):
        return sum(l.quantite for l in self.lots.filter(date_peremption__gte=timezone.localdate()))

class Fournisseur(models.Model):
    nom = models.CharField(max_length=180)
    contact = models.CharField(max_length=120, blank=True)
    telephone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    adresse = models.TextField(blank=True)
    actif = models.BooleanField(default=True)
    def __str__(self): return self.nom
    class Meta: ordering = ["nom"]

class Client(models.Model):
    nom = models.CharField(max_length=180)
    telephone = models.CharField(max_length=40, blank=True)
    email = models.EmailField(blank=True)
    adresse = models.TextField(blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    def __str__(self): return self.nom
    class Meta: ordering = ["nom"]

class LotStock(models.Model):
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT, related_name="lots")
    numero_lot = models.CharField(max_length=100)
    date_peremption = models.DateField()
    quantite = models.PositiveIntegerField(default=0)
    cout_unitaire = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.PROTECT, null=True, blank=True)
    cree_le = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ["date_peremption", "id"]
        constraints = [models.UniqueConstraint(fields=["medicament", "numero_lot"], name="lot_unique_par_medicament")]
    def __str__(self): return f"{self.medicament} — {self.numero_lot}"

class MouvementStock(models.Model):
    TYPES = [("ENTREE", "Entrée"), ("SORTIE", "Sortie"), ("AJUSTEMENT", "Ajustement"), ("RETOUR", "Retour")]
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT)
    lot = models.ForeignKey(LotStock, on_delete=models.PROTECT, null=True, blank=True)
    type_mouvement = models.CharField(max_length=20, choices=TYPES)
    quantite = models.IntegerField()
    reference = models.CharField(max_length=100, blank=True)
    commentaire = models.TextField(blank=True)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    date_mouvement = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-date_mouvement"]

class Achat(models.Model):
    STATUTS = [("BROUILLON", "Brouillon"), ("RECU", "Reçu"), ("ANNULE", "Annulé")]
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.PROTECT)
    reference = models.CharField(max_length=50, unique=True)
    statut = models.CharField(max_length=20, choices=STATUTS, default="BROUILLON")
    date_achat = models.DateField(default=timezone.localdate)
    cree_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    def __str__(self): return self.reference
    @property
    def total(self): return sum((ligne.total for ligne in self.lignes.all()), Decimal("0.00"))

class LigneAchat(models.Model):
    achat = models.ForeignKey(Achat, on_delete=models.CASCADE, related_name="lignes")
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT)
    numero_lot = models.CharField(max_length=100)
    date_peremption = models.DateField()
    quantite = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2)
    @property
    def total(self): return self.quantite * self.prix_unitaire
    def __str__(self): return f"{self.medicament} × {self.quantite} — {self.achat.reference}"

class Vente(models.Model):
    MODES = [("ESPECES", "Espèces"), ("MVOLA", "Mobile Money"), ("AUTRE", "Autre")]
    STATUTS = [("VALIDEE", "Validée"), ("ANNULEE", "Annulée")]
    reference = models.CharField(max_length=50, unique=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, null=True, blank=True)
    date_vente = models.DateTimeField(default=timezone.now)
    mode_paiement = models.CharField(max_length=20, choices=MODES, default="ESPECES")
    statut = models.CharField(max_length=20, choices=STATUTS, default="VALIDEE")
    total = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    def __str__(self): return self.reference

class LigneVente(models.Model):
    vente = models.ForeignKey(Vente, on_delete=models.CASCADE, related_name="lignes")
    medicament = models.ForeignKey(Medicament, on_delete=models.PROTECT)
    lot = models.ForeignKey(LotStock, on_delete=models.PROTECT)
    quantite = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    prix_unitaire = models.DecimalField(max_digits=12, decimal_places=2)
    @property
    def sous_total(self): return self.quantite * self.prix_unitaire
    def __str__(self): return f"{self.medicament} × {self.quantite} — {self.vente.reference}"

class RetourVente(models.Model):
    vente = models.ForeignKey(Vente, on_delete=models.PROTECT, related_name="retours")
    ligne = models.ForeignKey(LigneVente, on_delete=models.PROTECT)
    quantite = models.PositiveIntegerField()
    motif = models.TextField()
    date_retour = models.DateTimeField(auto_now_add=True)
    traite_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    stock_reintegre = models.BooleanField(default=False)
    def __str__(self): return f"Retour {self.vente.reference} — {self.quantite} unité(s)"

class JournalAudit(models.Model):
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=120)
    objet = models.CharField(max_length=180, blank=True)
    details = models.TextField(blank=True)
    date_action = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-date_action"]
