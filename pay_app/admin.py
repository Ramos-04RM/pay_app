from django.contrib import admin
from .models import Pay, Cabinet, Tag, CabinetTag


class PayAdmin(admin.ModelAdmin):
    """Admin configuration for pay records."""

    list_display = ("id", "cabinet", "groups", "create_date", "service", "type_source", "pay_sys", "paid_up_to")


class CabinetTagInline(admin.TabularInline):
    """Inline tag relation editor inside cabinet admin."""

    model = CabinetTag
    extra = 0
    autocomplete_fields = ('tag',)


@admin.register(Cabinet)
class CabinetAdmin(admin.ModelAdmin):
    """Admin configuration for cabinets and their tags."""

    inlines = [CabinetTagInline]
    list_display = ('id', 'login', 'link', 'email_login', 'balance', 'currency')
    list_filter = ('currency',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Admin configuration for reusable tags."""

    list_display = ('id', 'name', 'note')
    search_fields = ('name',)


@admin.register(CabinetTag)
class CabinetTagAdmin(admin.ModelAdmin):
    """Admin configuration for explicit cabinet-tag relations."""

    list_display = ('id', 'cabinet', 'tag', 'created_at')
    list_filter = ('tag',)
    search_fields = ('cabinet__login', 'tag__name')


admin.site.register(Pay, PayAdmin)