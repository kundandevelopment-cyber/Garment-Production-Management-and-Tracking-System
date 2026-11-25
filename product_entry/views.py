from django.shortcuts import render


def dashboard(request):
    return render(
        request,
        "product_entry/dashboard.html",
    )
