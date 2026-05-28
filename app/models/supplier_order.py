from sqlalchemy import String, Text, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from decimal import Decimal

from app.core.database import Base


class SupplierOrder(Base):
    """
    Заявка конкретному поставщику — часть общей SupplyRequest.

    Одна заявка мастера может быть разбита
    на несколько SupplierOrder (разным поставщикам).
    """
    __tablename__ = "supplier_orders"

    id:         Mapped[int] = mapped_column(primary_key=True, index=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("supply_requests.id"), nullable=False, index=True)
    supplier_id:Mapped[int] = mapped_column(ForeignKey("suppliers.id"),       nullable=False, index=True)

    # Статус этого конкретного заказа
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)

    # Счёт от поставщика
    invoice_number:  Mapped[str|None]     = mapped_column(String(100),    nullable=True)
    invoice_amount:  Mapped[Decimal|None] = mapped_column(Numeric(12, 2), nullable=True)
    invoice_approved:Mapped[bool]         = mapped_column(Boolean, default=False, nullable=False)

    notes: Mapped[str|None] = mapped_column(Text, nullable=True)

    # Relationships
    request:  Mapped["SupplyRequest"] = relationship("SupplyRequest", back_populates="orders")   # noqa: F821
    supplier: Mapped["Supplier"]      = relationship("Supplier")                                  # noqa: F821

    def __repr__(self) -> str:
        return f"<SupplierOrder id={self.id} supplier_id={self.supplier_id} status={self.status}>"