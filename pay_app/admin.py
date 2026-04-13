from django.contrib import admin
from .models import Pay, Cabinet, Tag, CabinetTag


class PayAdmin(admin.ModelAdmin):
    list_display = ("id", "cabinet", "groups", "create_date", "service", "type_source", "pay_sys", "paid_up_to")


class CabinetTagInline(admin.TabularInline):
    model = CabinetTag
    extra = 0
    autocomplete_fields = ('tag',)


@admin.register(Cabinet)
class CabinetAdmin(admin.ModelAdmin):
    inlines = [CabinetTagInline]
    list_display = ('id', 'login', 'link', 'email_login')


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'note')
    search_fields = ('name',)


@admin.register(CabinetTag)
class CabinetTagAdmin(admin.ModelAdmin):
    list_display = ('id', 'cabinet', 'tag', 'created_at')
    list_filter = ('tag',)
    search_fields = ('cabinet__login', 'tag__name')


admin.site.register(Pay, PayAdmin)