from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from .models import SMSProviderSettings, SMSBlacklistedPhone, SMSAccessCode


# Register your models here.
@admin.register(SMSProviderSettings)
class SMSProviderSettingsAdmin(admin.ModelAdmin):
    list_display = ("name", "provider", "status_badge", "login", "code_ttl_minutes", "max_sends_per_day", "updated_at")
    list_filter = ("is_active", "provider")
    search_fields = ("name", "login", "sender_id")
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Основное", {
            "fields": ("name", "provider", "login", "password", "sender_id", "is_active", ),
        }),
        ("Политика кодов", {
            "fields": ("code_ttl_minutes", "code_length", "max_verify_attempts"),
        }),
        ("Rate Limit / Daily Limit", {
            "fields": ("resend_cooldown_seconds", "max_sends_per_day", "ban_minutes_after_daily_limit"),
        }),
        ("Blacklist", {
            "fields": ("blacklist_after_expired", "blacklist_duration_minutes"),
        }),
        ("Служебное", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at"),
        }),
    )

    @admin.display(description="Статус", ordering="is_active")
    def status_badge(self, obj):
        if obj.is_active:
            return format_html('<span style="color:#fff;background:#28a745;padding:2px 10px;border-radius:12px;font-size:12px;">✔ Активен</span>')
        return format_html('<span style="color:#fff;background:#6c757d;padding:2px 10px;border-radius:12px;font-size:12px;">Неактивен</span>')


@admin.register(SMSBlacklistedPhone)
class SMSBlacklistedPhoneAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "reason_badge", "status_badge", "banned_at", "banned_until_display")
    list_filter = ("is_active", "reason")
    search_fields = ("phone_number",)
    readonly_fields = ("banned_at",)
    actions = ["unban_selected"]

    fieldsets = (
        ("Телефон", {
            "fields": ("phone_number", "reason", "is_active"),
        }),
        ("Бан", {
            "fields": ("banned_at", "banned_until"),
        }),
    )

    @admin.display(description="Причина", ordering="reason")
    def reason_badge(self, obj):
        colors = {
            "expired_code": "#fd7e14",
            "daily_limit": "#dc3545",
            "manual": "#6f42c1",
        }
        color = colors.get(obj.reason, "#6c757d")
        return format_html(
            '<span style="color:#fff;background:{};padding:2px 8px;border-radius:10px;font-size:12px;">{}</span>',
            color, obj.get_reason_display()
        )

    @admin.display(description="Активен", boolean=False, ordering="is_active")
    def status_badge(self, obj):
        if obj.is_banned_now():
            return format_html('<span style="color:#fff;background:#dc3545;padding:2px 10px;border-radius:12px;font-size:12px;">🚫 Забанен</span>')
        return format_html('<span style="color:#fff;background:#28a745;padding:2px 10px;border-radius:12px;font-size:12px;">✔ Снят</span>')

    @admin.display(description="Забанен до")
    def banned_until_display(self, obj):
        if obj.banned_until is None:
            return format_html('<span style="color:#dc3545;font-weight:bold;">Навсегда</span>')
        if obj.banned_until < timezone.now():
            return format_html('<span style="color:#6c757d;">{} (истёк)</span>', obj.banned_until.strftime("%d.%m.%Y %H:%M"))
        return obj.banned_until.strftime("%d.%m.%Y %H:%M")

    @admin.action(description="Снять бан с выбранных номеров")
    def unban_selected(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Снят бан с {updated} номеров.")


@admin.register(SMSAccessCode)
class SMSAccessCodeAdmin(admin.ModelAdmin):
    list_display = ("phone_number", "status_badge", "attempts_display", "created_at", "expires_at_display", "provider")
    list_filter = ("status", "provider")
    search_fields = ("phone_number",)
    readonly_fields = ("phone_number", "code_hash", "status", "created_at", "expires_at", "verify_attempts", "max_attempts", "used_at", "provider", "meta")
    ordering = ("-created_at",)

    fieldsets = (
        ("Телефон & Код", {
            "fields": ("phone_number", "code_hash", "status"),
        }),
        ("Попытки", {
            "fields": ("verify_attempts", "max_attempts"),
        }),
        ("Время", {
            "fields": ("created_at", "expires_at", "used_at"),
        }),
        ("Провайдер & Мета", {
            "classes": ("collapse",),
            "fields": ("provider", "meta"),
        }),
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="Статус", ordering="status")
    def status_badge(self, obj):
        colors = {
            "active": "#28a745",
            "used": "#007bff",
            "expired": "#6c757d",
            "blocked": "#dc3545",
        }
        color = colors.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color:#fff;background:{};padding:2px 10px;border-radius:12px;font-size:12px;">{}</span>',
            color, obj.get_status_display()
        )

    @admin.display(description="Попытки")
    def attempts_display(self, obj):
        ratio = obj.verify_attempts / obj.max_attempts if obj.max_attempts else 0
        color = "#dc3545" if ratio >= 1 else "#fd7e14" if ratio >= 0.6 else "#28a745"
        return format_html(
            '<span style="color:{};">{} / {}</span>',
            color, obj.verify_attempts, obj.max_attempts
        )

    @admin.display(description="Истекает", ordering="expires_at")
    def expires_at_display(self, obj):
        if obj.is_expired():
            return format_html('<span style="color:#6c757d;">{} (истёк)</span>', obj.expires_at.strftime("%d.%m.%Y %H:%M"))
        return format_html('<span style="color:#28a745;">{}</span>', obj.expires_at.strftime("%d.%m.%Y %H:%M"))