import csv
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.views import LoginView as DjangoLoginView, LogoutView as DjangoLogoutView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView
from django.utils import timezone
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from .models import Categorie, Medicament, Fournisseur, Client, LotStock, Vente
from .forms import CategorieForm, MedicamentForm, FournisseurForm, ClientForm, PurchaseHeaderForm, PurchaseLineFormSet, ReturnForm, StaffUserCreateForm, StockAdjustmentForm
from .services import enregistrer_vente, recevoir_achat, enregistrer_retour, ajuster_stock
from .permissions import role_required, RoleRequiredMixin
from .models import Achat, LigneAchat
from django.contrib.auth import get_user_model

class LoginView(DjangoLoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

class LogoutView(DjangoLogoutView):
    pass

@login_required
@role_required("dashboard")
def dashboard(request):
    today = timezone.localdate()
    meds = Medicament.objects.filter(actif=True).prefetch_related("lots")
    low = [m for m in meds if m.stock_total <= m.seuil_alerte]
    sales = Vente.objects.filter(date_vente__date=today, statut="VALIDEE")
    return render(request, "pharmacie/dashboard.html", {
        "medicaments_count": meds.count(),
        "clients_count": Client.objects.count(),
        "fournisseurs_count": Fournisseur.objects.count(),
        "ventes_count": sales.count(),
        "ventes_total": sales.aggregate(v=Sum("total"))["v"] or 0,
        "low_stock": low[:8],
        "expired_count": LotStock.objects.filter(date_peremption__lt=today, quantite__gt=0).count(),
        "near_count": LotStock.objects.filter(
            date_peremption__range=(today, today + timedelta(days=90)), quantite__gt=0
        ).count(),
        "recent_sales": Vente.objects.order_by("-date_vente")[:8],
    })

class BaseList(RoleRequiredMixin, ListView):
    required_roles = ("catalogue",)
    template_name = "pharmacie/list.html"
    paginate_by = 15
    context_object_name = "objects"
    title = "Liste"
    create_url = None
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c.update({"page_title": self.title, "create_url": self.create_url})
        return c

class CategoryListView(BaseList):
    required_roles = ("catalogue",)
    model = Categorie
    title = "Catégories"
    create_url = "category_create"

class MedicineListView(BaseList):
    required_roles = ("catalogue",)
    model = Medicament
    title = "Médicaments"
    create_url = "medicine_create"
    def get_queryset(self):
        qs = super().get_queryset().select_related("categorie").prefetch_related("lots")
        q = self.request.GET.get("q")
        return (qs.filter(nom__icontains=q) | qs.filter(code__icontains=q)) if q else qs

class SupplierListView(BaseList):
    required_roles = ("fournisseurs",)
    model = Fournisseur
    title = "Fournisseurs"
    create_url = "supplier_create"

class CustomerListView(BaseList):
    required_roles = ("clients",)
    model = Client
    title = "Clients"
    create_url = "customer_create"

class LotListView(BaseList):
    required_roles = ("stock",)
    model = LotStock
    title = "Lots et stocks"
    def get_queryset(self):
        return super().get_queryset().select_related("medicament", "fournisseur")

class BaseCreate(RoleRequiredMixin, CreateView):
    required_roles = ("catalogue",)
    template_name = "pharmacie/form.html"
    success_url = reverse_lazy("dashboard")
    def form_valid(self, form):
        messages.success(self.request, "Enregistrement effectué.")
        return super().form_valid(form)

class CategoryCreateView(BaseCreate):
    required_roles = ("catalogue",)
    model = Categorie
    form_class = CategorieForm
    success_url = reverse_lazy("category_list")

class MedicineCreateView(BaseCreate):
    required_roles = ("catalogue",)
    model = Medicament
    form_class = MedicamentForm
    success_url = reverse_lazy("medicine_list")

class MedicineUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = ("catalogue",)
    model = Medicament
    form_class = MedicamentForm
    template_name = "pharmacie/form.html"
    success_url = reverse_lazy("medicine_list")

class CategoryUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = ("catalogue",)
    model = Categorie
    form_class = CategorieForm
    template_name = "pharmacie/form.html"
    success_url = reverse_lazy("category_list")

class SupplierUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = ("fournisseurs",)
    model = Fournisseur
    form_class = FournisseurForm
    template_name = "pharmacie/form.html"
    success_url = reverse_lazy("supplier_list")

class CustomerUpdateView(RoleRequiredMixin, UpdateView):
    required_roles = ("clients",)
    model = Client
    form_class = ClientForm
    template_name = "pharmacie/form.html"
    success_url = reverse_lazy("customer_list")

class SupplierCreateView(BaseCreate):
    required_roles = ("fournisseurs",)
    model = Fournisseur
    form_class = FournisseurForm
    success_url = reverse_lazy("supplier_list")

class CustomerCreateView(BaseCreate):
    required_roles = ("clients",)
    model = Client
    form_class = ClientForm
    success_url = reverse_lazy("customer_list")

class SaleListView(RoleRequiredMixin, ListView):
    required_roles = ("ventes",)
    model = Vente
    template_name = "pharmacie/sales.html"
    context_object_name = "ventes"
    paginate_by = 20

@login_required
@role_required("ventes")
def sale_create(request):
    medicaments = Medicament.objects.filter(actif=True).order_by("nom")
    if request.method == "POST":
        try:
            lignes = []
            for mid, qty in zip(request.POST.getlist("medicament"), request.POST.getlist("quantite")):
                med = get_object_or_404(Medicament, pk=mid)
                if int(qty) > 0:
                    lignes.append({"medicament": med, "quantite": int(qty)})
            vente = enregistrer_vente(
                utilisateur=request.user, lignes=lignes,
                mode_paiement=request.POST.get("mode_paiement", "ESPECES"),
                client=Client.objects.filter(pk=request.POST.get("client")).first() if request.POST.get("client") else None
            )
            messages.success(request, f"Vente {vente.reference} enregistrée.")
            return redirect("sale_receipt", pk=vente.pk)
        except (ValidationError, ValueError) as exc:
            messages.error(request, str(exc))
    return render(request, "pharmacie/sale_form.html", {"medicaments": medicaments, "clients": Client.objects.order_by("nom")})

@login_required
@role_required("achats")
def purchase_create(request):
    header = PurchaseHeaderForm(request.POST or None, prefix="header")
    lines = PurchaseLineFormSet(request.POST or None, prefix="lines")
    if request.method == "POST" and header.is_valid() and lines.is_valid():
        data = [f.cleaned_data for f in lines if f.cleaned_data and not f.cleaned_data.get("DELETE")]
        if not data:
            header.add_error(None, "Ajoutez au moins une ligne d'achat.")
        else:
            try:
                achat = recevoir_achat(utilisateur=request.user, fournisseur=header.cleaned_data["fournisseur"],
                    reference=header.cleaned_data["reference"], lignes=data, notes=header.cleaned_data["notes"])
                messages.success(request, f"Achat {achat.reference} réceptionné.")
                return redirect("purchase_list")
            except ValidationError as exc:
                header.add_error(None, exc)
    return render(request, "pharmacie/purchase_form.html", {"form": header, "formset": lines, "title": "Nouvel achat / réception"})

class PurchaseListView(RoleRequiredMixin, ListView):
    required_roles = ("achats",)
    model = Achat
    template_name = "pharmacie/purchases.html"
    context_object_name = "achats"
    paginate_by = 20
    def get_queryset(self):
        return Achat.objects.select_related("fournisseur", "cree_par").prefetch_related("lignes").order_by("-date_achat", "-id")

@login_required
@role_required("retours")
def return_create(request):
    form = ReturnForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            enregistrer_retour(
                utilisateur=request.user, ligne=d["ligne"], quantite=d["quantite"],
                motif=d["motif"], reintegrer=d["reintegrer"]
            )
            messages.success(request, "Retour enregistré.")
            return redirect("sale_list")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "pharmacie/form_generic.html", {"form": form, "title": "Enregistrer un retour"})

@login_required
@role_required("ventes")
def sale_receipt(request, pk):
    vente = get_object_or_404(Vente.objects.prefetch_related("lignes__medicament"), pk=pk)
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="recu-{vente.reference}.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    y = 790
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, y, "PHARMAGEST — Reçu de vente")
    y -= 35
    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Référence : {vente.reference}")
    y -= 18
    p.drawString(50, y, f"Date : {timezone.localtime(vente.date_vente):%d/%m/%Y %H:%M}")
    y -= 30
    for ligne in vente.lignes.all():
        p.drawString(50, y, f"{ligne.medicament.nom} x {ligne.quantite}")
        p.drawRightString(540, y, f"{ligne.sous_total:,.2f} Ar")
        y -= 18
        if y < 100:
            p.showPage()
            y = 790
    y -= 15
    p.setFont("Helvetica-Bold", 13)
    p.drawRightString(540, y, f"TOTAL : {vente.total:,.2f} Ar")
    p.showPage()
    p.save()
    return response

@login_required
@role_required("rapports")
def report_stock_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="rapport-stock-pharmagest.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Médicament", "Code", "Lot", "Péremption", "Quantité", "Fournisseur"])
    for lot in LotStock.objects.select_related("medicament", "fournisseur").order_by("medicament__nom", "date_peremption"):
        writer.writerow([lot.medicament.nom, lot.medicament.code, lot.numero_lot,
                         lot.date_peremption, lot.quantite, lot.fournisseur or ""])
    return response

@login_required
@role_required("rapports")
def report_sales_csv(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="rapport-ventes-pharmagest.csv"'
    response.write("\ufeff")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(["Référence", "Date", "Client", "Paiement", "Total", "Utilisateur"])
    for v in Vente.objects.filter(statut="VALIDEE").select_related("client", "utilisateur").order_by("-date_vente"):
        writer.writerow([v.reference, v.date_vente, v.client or "Comptoir",
                         v.get_mode_paiement_display(), v.total, v.utilisateur or ""])
    return response


@login_required
@role_required("all")
def user_list(request):
    users = get_user_model().objects.prefetch_related("groups").order_by("username")
    return render(request, "pharmacie/users.html", {"users": users})

@login_required
@role_required("all")
def user_create(request):
    form = StaffUserCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        messages.success(request, f"Le compte {user.username} a été créé.")
        return redirect("user_list")
    return render(request, "pharmacie/form.html", {"form": form, "page_title": "Créer un utilisateur"})


@login_required
@role_required("stock")
def stock_adjustment(request):
    form = StockAdjustmentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            lot = ajuster_stock(utilisateur=request.user, lot=form.cleaned_data["lot"],
                quantite_reelle=form.cleaned_data["quantite_reelle"], commentaire=form.cleaned_data["commentaire"])
            messages.success(request, f"Stock ajusté pour {lot.medicament} — lot {lot.numero_lot}.")
            return redirect("lot_list")
        except ValidationError as exc:
            form.add_error(None, exc)
    return render(request, "pharmacie/form_generic.html", {"form": form, "title": "Ajustement d'inventaire"})
