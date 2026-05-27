import enum


class UserRole(str, enum.Enum):
    admin      = "admin"        # полный доступ
    manager    = "manager"      # снабженец — центральная роль
    master     = "master"       # мастер на объекте
    supervisor = "supervisor"   # руководитель проекта
    supplier   = "supplier"     # поставщик (внешний пользователь)


class RequestStatus(str, enum.Enum):
    draft              = "draft"               # черновик мастера
    submitted          = "submitted"           # отправлена снабженцу
    sent_to_supplier   = "sent_to_supplier"    # отправлена поставщикам
    invoice_received   = "invoice_received"    # счёт получен
    invoice_approved   = "invoice_approved"    # счёт согласован мастером
    confirmed          = "confirmed"           # утверждено РП
    delivery_scheduled = "delivery_scheduled"  # доставка назначена
    delivered          = "delivered"           # товар доставлен
    completed          = "completed"           # мастер принял, всё ок
    cancelled          = "cancelled"           # отменена


# Допустимые переходы статусов
REQUEST_STATUS_TRANSITIONS = {
    RequestStatus.draft:              [RequestStatus.submitted],
    RequestStatus.submitted:          [RequestStatus.sent_to_supplier, RequestStatus.draft],
    RequestStatus.sent_to_supplier:   [RequestStatus.invoice_received],
    RequestStatus.invoice_received:   [RequestStatus.invoice_approved, RequestStatus.sent_to_supplier],
    RequestStatus.invoice_approved:   [RequestStatus.confirmed, RequestStatus.invoice_received],
    RequestStatus.confirmed:          [RequestStatus.delivery_scheduled],
    RequestStatus.delivery_scheduled: [RequestStatus.delivered],
    RequestStatus.delivered:          [RequestStatus.completed],
    RequestStatus.completed:          [],
    RequestStatus.cancelled:          [],
}


class EventActionType(str, enum.Enum):
    # Заявка
    request_created        = "request_created"
    request_updated        = "request_updated"
    request_status_changed = "request_status_changed"

    # Поставщики
    sent_to_supplier       = "sent_to_supplier"
    invoice_received       = "invoice_received"
    invoice_approved       = "invoice_approved"
    invoice_rejected       = "invoice_rejected"

    # Доставка
    delivery_scheduled     = "delivery_scheduled"
    delivery_confirmed     = "delivery_confirmed"
    goods_received         = "goods_received"

    # Комментарии
    comment_added          = "comment_added"
    photo_uploaded         = "photo_uploaded"

    # Уведомления
    notification_sent      = "notification_sent"


class EventSource(str, enum.Enum):
    api      = "api"
    telegram = "telegram"
    system   = "system"