class OrdersError(Exception):
    """Base class for orders domain errors."""


class EmptyCartError(OrdersError):
    pass


class InsufficientStockError(OrdersError):
    """Carries a list of {'variant', 'requested', 'available'} dicts."""

    def __init__(self, shortfalls):
        self.shortfalls = shortfalls
        super().__init__(f"{len(shortfalls)} line(s) exceed available stock")


class AddressOwnershipError(OrdersError):
    pass


class PaymentSimulatedFailure(OrdersError):
    pass


class OrderNotCancellable(OrdersError):
    pass
