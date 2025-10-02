# apps/plans/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.db import transaction
from decimal import Decimal

from .models import Plan

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'level', 'power', 'price_formatted', 'get_token_symbols', 'image_tag')
    list_filter = ('tokens', 'level')
    search_fields = ('name', 'tokens__symbol')
    ordering = ('level', 'name')
    list_per_page = 25

    def price_formatted(self, obj):
        return f"{obj.price:.2f}"
    price_formatted.short_description = 'Price'

    def get_token_symbols(self, obj):
        return ", ".join([t.symbol for t in obj.tokens.all()])
    get_token_symbols.short_description = 'Tokens'

    def image_tag(self, obj):
        if obj.image:
            return format_html('<img src="{}" width="50" style="border-radius:4px;" />', obj.image.url)
        return "No Image"
    image_tag.short_description = 'Image'

    def save_related(self, request, form, formsets, change):
        """
        بعد از ذخیره‌ی Plan و M2Mها اجرا می‌شه.
        اگر Plan جدید ایجاد شده (change == False) یک Miner متناظر بساز.
        """
        super().save_related(request, form, formsets, change)

        # فقط هنگام CREATE (نه هنگام UPDATE) یک Miner بساز
        if not change:
            plan = form.instance
            # import محلی برای جلوگیری از circular import
            from apps.miners.models import Miner

            # اگر قبلاً برای این پلن ماینری وجود نداشت، بساز
            if not Miner.objects.filter(plan=plan).exists():
                with transaction.atomic():
                    miner = Miner.objects.create(
                        plan=plan,
                        name=plan.name,
                        power=float(plan.power) if plan.power is not None else 0.0,
                        staked_amount=Decimal("0"),
                        is_online=False,
                    )
                    # کپی کردن توکن‌ها از Plan به Miner (M2M)
                    miner.tokens.set(plan.tokens.all())
