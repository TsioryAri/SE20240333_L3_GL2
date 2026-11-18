from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from pharmacie import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("utilisateurs/", views.user_list, name="user_list"),
    path("utilisateurs/ajouter/", views.user_create, name="user_create"),
    path("accounts/login/", views.LoginView.as_view(), name="login"),
    path("accounts/logout/", views.LogoutView.as_view(), name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("categories/", views.CategoryListView.as_view(), name="category_list"),
    path("categories/ajouter/", views.CategoryCreateView.as_view(), name="category_create"),
    path("categories/<int:pk>/modifier/", views.CategoryUpdateView.as_view(), name="category_update"),
    path("medicaments/", views.MedicineListView.as_view(), name="medicine_list"),
    path("medicaments/ajouter/", views.MedicineCreateView.as_view(), name="medicine_create"),
    path("medicaments/<int:pk>/modifier/", views.MedicineUpdateView.as_view(), name="medicine_update"),
    path("fournisseurs/", views.SupplierListView.as_view(), name="supplier_list"),
    path("fournisseurs/ajouter/", views.SupplierCreateView.as_view(), name="supplier_create"),
    path("fournisseurs/<int:pk>/modifier/", views.SupplierUpdateView.as_view(), name="supplier_update"),
    path("clients/", views.CustomerListView.as_view(), name="customer_list"),
    path("clients/ajouter/", views.CustomerCreateView.as_view(), name="customer_create"),
    path("clients/<int:pk>/modifier/", views.CustomerUpdateView.as_view(), name="customer_update"),
    path("lots/", views.LotListView.as_view(), name="lot_list"),
    path("lots/ajustement/", views.stock_adjustment, name="stock_adjustment"),
    path("achats/", views.PurchaseListView.as_view(), name="purchase_list"),
    path("achats/nouvelle-reception/", views.purchase_create, name="purchase_create"),
    path("ventes/", views.SaleListView.as_view(), name="sale_list"),
    path("ventes/nouvelle/", views.sale_create, name="sale_create"),
    path("ventes/<int:pk>/recu/", views.sale_receipt, name="sale_receipt"),
    path("retours/nouveau/", views.return_create, name="return_create"),
    path("rapports/stock.csv", views.report_stock_csv, name="report_stock_csv"),
    path("rapports/ventes.csv", views.report_sales_csv, name="report_sales_csv"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
