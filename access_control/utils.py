from django.core.paginator import Paginator


def paginate_queryset(queryset, page_number=1, page_size=20, max_page_size=100):
    try:
        page_size = int(page_size)
    except (TypeError, ValueError):
        page_size = 20

    page_size = max(1, min(page_size, max_page_size))

    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page_number)

    return page_obj, paginator


def get_pagination_data(page_obj):
    paginator = page_obj.paginator

    return {
        "page": page_obj.number,
        "page_size": paginator.per_page,
        "total_items": paginator.count,
        "total_pages": paginator.num_pages,
        "has_next": page_obj.has_next(),
        "has_previous": page_obj.has_previous(),
    }