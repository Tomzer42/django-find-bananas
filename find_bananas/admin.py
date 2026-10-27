from django.contrib import admin
from django.utils.html import format_html

from .models import Edition, EditionRound, Play


class EditionRoundInline(admin.TabularInline):
    model = EditionRound
    fields = ["index", "count", "width", "height", "image_size"]
    readonly_fields = fields
    extra = 0
    can_delete = False

    @admin.display(description="Image size")
    def image_size(self, obj):
        return f"{len(obj.image) // 1024} KB" if obj.image else "-"


@admin.register(Edition)
class EditionAdmin(admin.ModelAdmin):
    list_display = ["number", "date", "market", "theme", "starts_at", "players"]
    list_filter = ["market", "theme"]
    readonly_fields = ["number", "starts_at", "ends_at", "created_at"]
    inlines = [EditionRoundInline]

    @admin.display(description="Completed plays")
    def players(self, obj):
        return obj.plays.filter(status=Play.Status.COMPLETED).count()


@admin.register(Play)
class PlayAdmin(admin.ModelAdmin):
    list_display = ["edition", "who", "status", "score", "ranked", "created_at"]
    list_filter = ["status", "ranked", "edition"]
    search_fields = ["user__email", "guest_key"]
    raw_id_fields = ["user", "edition"]
    readonly_fields = ["guest_key", "ip_hash", "rounds", "created_at", "completed_at"]

    @admin.display(description="Player")
    def who(self, obj):
        return obj.user.email if obj.user else format_html("<i>guest {}</i>", str(obj.guest_key)[:8])
