
from functools import wraps
from django.shortcuts import get_object_or_404

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

from .services import (
    user_has_module_access,
    user_has_menu_access,
    user_has_action_access,
)


def module_required(module_code):
    """
    Restrict a view to users who have access to a module.
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            module = _get_module(module_code)

            if not user_has_module_access(request.user, module):
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


def menu_required(module_code, menu_code):
    """
    Restrict a view to users who have access to a specific menu
    within a specific module.
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            menu = _get_menu(module_code, menu_code)

            if not user_has_menu_access(request.user, menu):
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


def action_required(module_code, menu_code, action_code):
    """
    Restrict a view to users who have permission for a specific
    action within a specific menu and module.
    """

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped_view(request, *args, **kwargs):
            action = _get_action(
                module_code,
                menu_code,
                action_code,
            )

            if not user_has_action_access(request.user, action):
                raise PermissionDenied

            return view_func(request, *args, **kwargs)

        return wrapped_view

    return decorator


def _get_module(module_code):
    from .models import Module

    return get_object_or_404(
        Module,
        code=module_code,
        is_active=True,
    )


def _get_menu(module_code, menu_code):
    from .models import Menu

    return get_object_or_404(
        Menu,
        module__code=module_code,
        module__is_active=True,
        code=menu_code,
        is_active=True,
    )


def _get_action(module_code, menu_code, action_code):
    from .models import Action

    return get_object_or_404(
        Action,
        menu__module__code=module_code,
        menu__module__is_active=True,
        menu__code=menu_code,
        menu__is_active=True,
        code=action_code,
        is_active=True,
    )
