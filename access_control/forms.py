
from django import forms

from .models import Module, Menu, Action


class MenuForm(forms.ModelForm):

    class Meta:
        model = Menu
        fields = [
            "module",
            "parent",
            "name",
            "code",
            "url_name",
            "description",
            "is_active",
            "sort_order",
        ]

        widgets = {
            "module": forms.Select(attrs={
                "class": "form-control",
            }),
            "parent": forms.Select(attrs={
                "class": "form-control",
            }),
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter menu name",
            }),
            "code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter menu code",
            }),
            "url_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter Django URL name (optional)",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter description (optional)",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
            "sort_order": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 0,
            }),
        }

    def __init__(self, *args, module=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Sort order
        self.fields["sort_order"].required = False
        self.fields["sort_order"].empty_value = 0

        # Parent menu
        self.fields["parent"].required = False
        self.fields["parent"].empty_label = "No parent (Root menu)"

        if module is not None:

            # Restrict module to the selected active module.
            self.fields["module"].queryset = Module.objects.filter(
                pk=module.pk,
                is_active=True,
            )

            self.fields["module"].initial = module.pk
            self.fields["module"].disabled = True

            # Parent menus must belong to the same module.
            parent_queryset = Menu.objects.filter(
                module=module,
                is_active=True,
            )

            # Exclude this menu and all descendants during editing.
            if self.instance and self.instance.pk:

                excluded_ids = {self.instance.pk}
                frontier = {self.instance.pk}

                while frontier:

                    child_ids = set(
                        Menu.objects.filter(
                            module=module,
                            parent_id__in=frontier,
                        ).values_list(
                            "id",
                            flat=True,
                        )
                    )

                    new_ids = child_ids - excluded_ids

                    if not new_ids:
                        break

                    excluded_ids.update(new_ids)
                    frontier = new_ids

                parent_queryset = parent_queryset.exclude(
                    id__in=excluded_ids,
                )

            self.fields["parent"].queryset = parent_queryset.order_by(
                "sort_order",
                "name",
            )

        else:

            # Allow form use without a fixed module.
            self.fields["module"].queryset = Module.objects.filter(
                is_active=True,
            ).order_by(
                "sort_order",
                "name",
            )

            self.fields["parent"].queryset = Menu.objects.filter(
                is_active=True,
                module__is_active=True,
            ).order_by(
                "module__sort_order",
                "module__name",
                "sort_order",
                "name",
            )


class ActionForm(forms.ModelForm):

    class Meta:
        model = Action
        fields = [
            "menu",
            "name",
            "code",
            "description",
            "is_active",
            "sort_order",
        ]

        widgets = {
            "menu": forms.Select(attrs={
                "class": "form-control",
            }),
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter action name",
            }),
            "code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter action code",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Enter description (optional)",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
            "sort_order": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 0,
            }),
        }

    def __init__(self, *args, menu=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["sort_order"].required = False
        self.fields["sort_order"].empty_value = 0

        if menu is not None:

            # Restrict menu to the selected active menu.
            self.fields["menu"].queryset = Menu.objects.filter(
                pk=menu.pk,
                is_active=True,
                module__is_active=True,
            )

            self.fields["menu"].initial = menu.pk
            self.fields["menu"].disabled = True

        else:

            # Allow selection from active menus.
            self.fields["menu"].queryset = Menu.objects.filter(
                is_active=True,
                module__is_active=True,
            ).order_by(
                "module__sort_order",
                "module__name",
                "sort_order",
                "name",
            )

        self.fields["menu"].empty_label = "Select menu"

    def clean_name(self):
        name = self.cleaned_data.get("name")

        if not name:
            return name

        menu = self.cleaned_data.get("menu")

        if menu is None:
            return name

        existing_actions = Action.objects.filter(
            menu=menu,
            name__iexact=name,
        )

        if self.instance.pk:
            existing_actions = existing_actions.exclude(
                pk=self.instance.pk,
            )

        if existing_actions.exists():
            raise forms.ValidationError(
                "An action with this name already exists in this menu."
            )

        return name

    def clean_code(self):
        code = self.cleaned_data.get("code")

        if not code:
            return code

        menu = self.cleaned_data.get("menu")

        if menu is None:
            return code

        existing_actions = Action.objects.filter(
            menu=menu,
            code=code,
        )

        if self.instance.pk:
            existing_actions = existing_actions.exclude(
                pk=self.instance.pk,
            )

        if existing_actions.exists():
            raise forms.ValidationError(
                "An action with this code already exists in this menu."
            )

        return code
