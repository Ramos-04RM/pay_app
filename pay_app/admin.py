from django.contrib import admin
from .models import Pay, Cabinet


class PayAdmin(admin.ModelAdmin):
    list_display = ("id", "cabinet", "groups", "create_date", "service", "type_source",
                    "pay_sys", "paid_up_to")


admin.site.register(Pay, PayAdmin)
admin.site.register(Cabinet)


