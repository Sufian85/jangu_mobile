from orders.cart import SessionCart


def cart_summary(request):
    """Cart badge + subtotal for every template. One extra query when the
    cart is non-empty (SessionCart resolves live prices); zero when empty."""
    cart = SessionCart(request)
    return {"cart_count": len(cart), "cart_subtotal": cart.subtotal}
