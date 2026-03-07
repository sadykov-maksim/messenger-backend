from django.contrib import admin

from .consumers import RoomConsumer
from .models import *

# Register your models here.
class RoomMemberInline(admin.TabularInline):
    model = RoomMember
    extra = 0
    readonly_fields = ('joined_at', 'last_read_at')


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ('created_at', 'updated_at')
    fields = ('user', 'text', 'type', 'is_edited', 'created_at')


class AttachmentInline(admin.TabularInline):
    model = Attachment
    extra = 0


class MessageStatusInline(admin.TabularInline):
    model = MessageStatus
    extra = 0
    readonly_fields = ('updated_at',)


class ReactionInline(admin.TabularInline):
    model = Reaction
    extra = 0


# ───────────────────────── ModelAdmin ─────────────────────────

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'type', 'host', 'created_at', 'members_count')
    list_filter = ('type', 'created_at')
    search_fields = ('name', 'host__username')
    readonly_fields = ('created_at',)
    inlines = (RoomMemberInline, MessageInline)

    def members_count(self, obj):
        return obj.members.count()
    members_count.short_description = 'Участников'


@admin.register(RoomMember)
class RoomMemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'user', 'role', 'joined_at', 'last_read_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('room__name', 'user__username')
    readonly_fields = ('joined_at',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'user', 'type', 'short_text', 'is_edited', 'created_at')
    list_filter = ('type', 'is_edited', 'created_at')
    search_fields = ('text', 'user__username', 'room__name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = (AttachmentInline, MessageStatusInline, ReactionInline)

    def short_text(self, obj):
        return obj.text[:50] + '...' if obj.text and len(obj.text) > 50 else obj.text
    short_text.short_description = 'Текст'


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'type', 'name', 'size_kb')
    list_filter = ('type',)
    search_fields = ('name', 'message__user__username')

    def size_kb(self, obj):
        return f"{round(obj.size / 1024, 1)} KB"
    size_kb.short_description = 'Размер'


@admin.register(MessageStatus)
class MessageStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'user', 'status', 'updated_at')
    list_filter = ('status', 'updated_at')
    search_fields = ('user__username',)
    readonly_fields = ('updated_at',)


@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ('id', 'message', 'user', 'emoji')
    search_fields = ('user__username', 'emoji')


@admin.register(Draft)
class DraftAdmin(admin.ModelAdmin):
    list_display = ('id', 'room', 'user', 'short_text', 'updated_at')
    search_fields = ('user__username', 'room__name')
    readonly_fields = ('updated_at',)

    def short_text(self, obj):
        return obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
    short_text.short_description = 'Черновик'