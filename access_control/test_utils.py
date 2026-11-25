from django.test import SimpleTestCase

from .utils import paginate_queryset, get_pagination_data


class PaginateQuerysetTests(SimpleTestCase):

    def test_paginate_queryset_returns_correct_first_page(self):
        items = ["A", "B", "C", "D", "E"]

        page_obj, paginator = paginate_queryset(
            items,
            page_number=1,
            page_size=2,
        )

        self.assertEqual(list(page_obj), ["A", "B"])
        self.assertEqual(page_obj.number, 1)
        self.assertEqual(paginator.count, 5)
        self.assertEqual(paginator.num_pages, 3)

    def test_paginate_queryset_returns_correct_second_page(self):
        items = ["A", "B", "C", "D", "E"]

        page_obj, paginator = paginate_queryset(
            items,
            page_number=2,
            page_size=2,
        )

        self.assertEqual(list(page_obj), ["C", "D"])
        self.assertTrue(page_obj.has_previous())
        self.assertTrue(page_obj.has_next())

    def test_paginate_queryset_handles_invalid_page(self):
        items = ["A", "B", "C"]

        page_obj, paginator = paginate_queryset(
            items,
            page_number="invalid",
            page_size=2,
        )

        self.assertEqual(page_obj.number, 1)
        self.assertEqual(list(page_obj), ["A", "B"])

    def test_paginate_queryset_enforces_maximum_page_size(self):
        items = list(range(150))

        page_obj, paginator = paginate_queryset(
            items,
            page_number=1,
            page_size=500,
        )

        self.assertEqual(paginator.per_page, 100)
        self.assertEqual(len(page_obj), 100)

    def test_paginate_queryset_enforces_minimum_page_size(self):
        items = list(range(10))

        page_obj, paginator = paginate_queryset(
            items,
            page_number=1,
            page_size=-5,
        )

        self.assertEqual(paginator.per_page, 1)
        self.assertEqual(len(page_obj), 1)

    def test_paginate_queryset_handles_invalid_page_size(self):
        items = list(range(30))

        page_obj, paginator = paginate_queryset(
            items,
            page_number=1,
            page_size="abc",
        )

        self.assertEqual(paginator.per_page, 20)
        self.assertEqual(len(page_obj), 20)

class PaginationDataTests(SimpleTestCase):

    def test_returns_correct_pagination_data_for_first_page(self):
        items = list(range(45))
        page_obj, _ = paginate_queryset(items, page_number=1, page_size=20)

        data = get_pagination_data(page_obj)

        self.assertEqual(data, {
            "page": 1,
            "page_size": 20,
            "total_items": 45,
            "total_pages": 3,
            "has_next": True,
            "has_previous": False,
        })

    def test_returns_correct_pagination_data_for_last_page(self):
        items = list(range(45))
        page_obj, _ = paginate_queryset(items, page_number=3, page_size=20)

        data = get_pagination_data(page_obj)

        self.assertEqual(data, {
            "page": 3,
            "page_size": 20,
            "total_items": 45,
            "total_pages": 3,
            "has_next": False,
            "has_previous": True,
        })

    def test_returns_correct_pagination_data_for_single_page(self):
        items = list(range(5))
        page_obj, _ = paginate_queryset(items, page_number=1, page_size=20)

        data = get_pagination_data(page_obj)

        self.assertEqual(data, {
            "page": 1,
            "page_size": 20,
            "total_items": 5,
            "total_pages": 1,
            "has_next": False,
            "has_previous": False,
        })