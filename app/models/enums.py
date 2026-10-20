
import enum


class UserRole(str, enum.Enum):
    customer = "customer"
    merchant = "merchant"
    admin = "admin"


class StoreVerificationStatus(str, enum.Enum):
    pending = "pending"
    verified = "verified"
    rejected = "rejected"
    suspended = "suspended"


class OfferType(str, enum.Enum):
    percent = "percent"
    fixed = "fixed"


class OfferStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    active = "active"
    paused = "paused"
    expired = "expired"
    cancelled = "cancelled"


class VoucherStatus(str, enum.Enum):
    claimed = "claimed"
    redeemed = "redeemed"
    expired = "expired"
    cancelled = "cancelled"


class RedemptionSource(str, enum.Enum):
    merchant_entered = "merchant_entered"
    simulated = "simulated"


class SalesDataSource(str, enum.Enum):
    merchant_entered = "merchant_entered"
    simulated_demo = "simulated_demo"


class AnalyticsEventType(str, enum.Enum):
    impression = "impression"
    view = "view"
    claim = "claim"
