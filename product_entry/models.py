
from django.db import models


class Brand(models.Model):
    name = models.CharField(
        max_length=150,
        unique=True,
    )
    code = models.SlugField(
        max_length=100,
        unique=True,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Brand"
        verbose_name_plural = "Brands"

    def __str__(self):
        return self.name


class ProductType(models.Model):
    name = models.CharField(
        max_length=100,
        unique=True,
    )
    code = models.SlugField(
        max_length=100,
        unique=True,
    )
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Product Type"
        verbose_name_plural = "Product Types"

    def __str__(self):
        return self.name


class ProductCategory(models.Model):
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=100)

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )

    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["name", "parent"],
                name="unique_category_name_per_parent",
            ),
            models.UniqueConstraint(
                fields=["code", "parent"],
                name="unique_category_code_per_parent",
            ),
        ]
        verbose_name = "Product Category"
        verbose_name_plural = "Product Categories"

    def __str__(self):
        return self.name


class ProductAttribute(models.Model):

    DATA_TYPE_CHOICES = [
        ("text", "Text"),
        ("number", "Whole Number"),
        ("decimal", "Decimal"),
        ("boolean", "Yes / No"),
        ("date", "Date"),
        ("choice", "Single Choice"),
        ("multi_choice", "Multiple Choice"),
    ]

    name = models.CharField(max_length=150)

    code = models.SlugField(
        max_length=150,
        unique=True,
    )

    data_type = models.CharField(
        max_length=20,
        choices=DATA_TYPE_CHOICES,
    )

    group_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Example: Fabric, Construction, or Design.",
    )

    description = models.TextField(blank=True)

    help_text = models.TextField(blank=True)

    configuration = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional validation and display configuration.",
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Product Attribute"
        verbose_name_plural = "Product Attributes"

    def __str__(self):
        return self.name


class ProductAttributeOption(models.Model):

    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.CASCADE,
        related_name="options",
    )

    label = models.CharField(max_length=150)
    value = models.SlugField(max_length=150)

    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["display_order", "label"]
        constraints = [
            models.UniqueConstraint(
                fields=["attribute", "value"],
                name="unique_attribute_option_value",
            ),
        ]
        verbose_name = "Product Attribute Option"
        verbose_name_plural = "Product Attribute Options"

    def __str__(self):
        return f"{self.attribute.name} - {self.label}"


class ProductTypeAttribute(models.Model):

    product_type = models.ForeignKey(
        ProductType,
        on_delete=models.CASCADE,
        related_name="attribute_assignments",
    )

    attribute = models.ForeignKey(
        ProductAttribute,
        on_delete=models.PROTECT,
        related_name="product_type_assignments",
    )

    is_required = models.BooleanField(default=False)

    display_order = models.PositiveIntegerField(default=0)

    section = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional section override for this product type.",
    )

    class Meta:
        ordering = ["display_order", "attribute__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["product_type", "attribute"],
                name="unique_attribute_per_product_type",
            ),
        ]
        verbose_name = "Product Type Attribute"
        verbose_name_plural = "Product Type Attributes"

    def __str__(self):
        return f"{self.product_type.name} - {self.attribute.name}"
