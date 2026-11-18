from django import forms
from django.forms import formset_factory
from .models import Categorie, Medicament, Fournisseur, Client, LigneVente

class BootstrapModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

class CategorieForm(BootstrapModelForm):
    class Meta:
        model = Categorie
        fields = ["nom", "description"]

class MedicamentForm(BootstrapModelForm):
    class Meta:
        model = Medicament
        fields = ["nom", "code", "code_barres", "categorie", "dosage", "forme", "description", "prix_achat", "prix_vente", "seuil_alerte", "photo", "actif"]

class FournisseurForm(BootstrapModelForm):
    class Meta:
        model = Fournisseur
        fields = ["nom", "contact", "telephone", "email", "adresse", "actif"]

class ClientForm(BootstrapModelForm):
    class Meta:
        model = Client
        fields = ["nom", "telephone", "email", "adresse"]

class PurchaseLineForm(forms.Form):
    medicament = forms.ModelChoiceField(queryset=Medicament.objects.none(), label="Médicament")
    numero_lot = forms.CharField(max_length=100, label="Numéro de lot")
    date_peremption = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), label="Date de péremption")
    quantite = forms.IntegerField(min_value=1, label="Quantité")
    prix_unitaire = forms.DecimalField(min_value=0, max_digits=12, decimal_places=2, label="Prix unitaire (Ar)")
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs.setdefault("class", "form-control")
        self.fields["medicament"].queryset = Medicament.objects.filter(actif=True)

PurchaseLineFormSet = formset_factory(PurchaseLineForm, extra=1, can_delete=True)

class PurchaseHeaderForm(forms.Form):
    fournisseur = forms.ModelChoiceField(queryset=Fournisseur.objects.none(), label="Fournisseur")
    reference = forms.CharField(max_length=50, label="Référence achat")
    notes = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}), label="Notes")
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs.setdefault("class", "form-control")
        self.fields["fournisseur"].queryset = Fournisseur.objects.filter(actif=True)
    def clean_reference(self):
        reference = self.cleaned_data["reference"].strip()
        from .models import Achat
        if Achat.objects.filter(reference=reference).exists():
            raise forms.ValidationError("Cette référence d'achat existe déjà.")
        return reference

class ReturnForm(forms.Form):
    ligne = forms.ModelChoiceField(queryset=LigneVente.objects.none(), label="Ligne de vente")
    quantite = forms.IntegerField(min_value=1, label="Quantité retournée")
    motif = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), label="Motif")
    reintegrer = forms.BooleanField(required=False, label="Réintégrer au stock après contrôle")
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs.setdefault("class", "form-control")
        self.fields["ligne"].queryset = LigneVente.objects.select_related("vente", "medicament").filter(vente__statut="VALIDEE").order_by("-vente__date_vente")

from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Group

class StaffUserCreateForm(UserCreationForm):
    role = forms.ModelChoiceField(queryset=Group.objects.none(), label="Rôle")
    class Meta:
        model = get_user_model()
        fields = ("username", "first_name", "last_name", "email")
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs.setdefault("class", "form-control")
        self.fields["role"].queryset = Group.objects.filter(name__in=["Administrateur", "Pharmacien", "Gestionnaire de stock", "Caissier"])
    def save(self, commit=True):
        user = super().save(commit=commit)
        if commit:
            user.groups.set([self.cleaned_data["role"]])
        return user

from .models import LotStock
class StockAdjustmentForm(forms.Form):
    lot = forms.ModelChoiceField(queryset=LotStock.objects.none(), label="Lot")
    quantite_reelle = forms.IntegerField(min_value=0, label="Quantité physique constatée")
    commentaire = forms.CharField(widget=forms.Textarea(attrs={"rows": 2}), label="Motif de l'ajustement")
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs.setdefault("class", "form-control")
        self.fields["lot"].queryset = LotStock.objects.select_related("medicament").order_by("medicament__nom", "date_peremption")
