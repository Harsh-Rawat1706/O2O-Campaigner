from pydantic import BaseModel


class CustomerVoucherDashboardResponse(BaseModel):
    vouchers_claimed: int
    vouchers_used: int
    vouchers_available: int
    vouchers_expired: int
    vouchers_cancelled: int
