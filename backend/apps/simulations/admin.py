from django.contrib import admin

from .models import Simulation


@admin.register(Simulation)
class SimulationAdmin(admin.ModelAdmin):
    list_display = ("title", "provider", "provider_id", "order")
    list_filter = ("provider", "subjects")
    search_fields = ("title", "topics", "provider_id")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("subjects",)
