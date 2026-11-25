
from django.contrib import admin

from .models import (
    Brand,
    ProductType,
    ProductCategory,
    ProductAttribute,
    ProductAttributeOption,
    ProductTypeAttribute,
)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_active",
        "created_at",
        "updated_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProductType)
class ProductTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "parent",
        "is_active",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "code", "parent__name")
    ordering = ("name",)
    list_select_related = ("parent",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProductAttribute)
class ProductAttributeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "data_type",
        "group_name",
        "is_active",
        "created_at",
    )
    list_filter = (
        "data_type",
        "group_name",
        "is_active",
    )
    search_fields = ("name", "code", "group_name")
    ordering = ("group_name", "name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ProductAttributeOption)
class ProductAttributeOptionAdmin(admin.ModelAdmin):
    list_display = (
        "label",
        "value",
        "attribute",
        "display_order",
        "is_active",
    )
    list_filter = (
        "attribute",
        "is_active",
    )
    search_fields = (
        "label",
        "value",
        "attribute__name",
    )
    ordering = (
        "attribute",
        "display_order",
        "label",
    )
    list_select_related = ("attribute",)


@admin.register(ProductTypeAttribute)
class ProductTypeAttributeAdmin(admin.ModelAdmin):
    list_display = (
        "product_type",
        "attribute",
        "is_required",
        "section",
        "display_order",
    )
    list_filter = (
        "product_type",
        "is_required",
        "section",
    )
    search_fields = (
        "product_type__name",
        "attribute__name",
    )
    ordering = (
        "product_type",
        "display_order",
    )
    list_select_related = (
        "product_type",
        "attribute",
    )
