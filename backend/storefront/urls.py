from django.urls import path

from storefront.views import account, auth, cart, catalog, checkout

app_name = "storefront"

urlpatterns = [
    path("", catalog.home, name="home"),
    path("c/<slug:slug>/", catalog.category, name="category"),
    path("search/", catalog.search, name="search"),
    path("p/<slug:slug>/", catalog.product_detail, name="product"),
    path("cart/", cart.detail, name="cart"),
    path("cart/add/", cart.add, name="cart_add"),
    path("cart/update/", cart.update, name="cart_update"),
    path("cart/remove/", cart.remove, name="cart_remove"),
    path("register/", auth.register, name="register"),
    path("login/", auth.StorefrontLoginView.as_view(), name="login"),
    path("logout/", auth.logout_view, name="logout"),
    path("checkout/", checkout.checkout, name="checkout"),
    path("checkout/payment/", checkout.payment, name="payment"),
    path("orders/<str:order_number>/", checkout.order_confirmation, name="order_confirmation"),
    path("account/", account.index, name="account"),
    path("account/orders/", account.orders, name="account_orders"),
    path("account/orders/<str:order_number>/", account.order_detail, name="account_order"),
    path("account/orders/<str:order_number>/cancel/", account.order_cancel, name="account_order_cancel"),
    path("account/addresses/", account.addresses, name="addresses"),
    path("account/addresses/add/", account.address_add, name="address_add"),
    path("account/addresses/<int:pk>/edit/", account.address_edit, name="address_edit"),
    path("account/addresses/<int:pk>/delete/", account.address_delete, name="address_delete"),
    path("account/addresses/<int:pk>/set-default/", account.address_set_default, name="address_set_default"),
]
