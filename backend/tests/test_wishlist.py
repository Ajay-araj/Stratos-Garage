"""
Wishlist tests: add, remove, list, duplicate prevention, auth guards.
"""
import pytest
from rest_framework import status


@pytest.mark.django_db
class TestWishlist:
    list_url = '/api/wishlist/'
    add_url = '/api/wishlist/add/'

    def _remove_url(self, product_id):
        return f'/api/wishlist/{product_id}/'

    def test_get_empty_wishlist(self, buyer_client):
        resp = buyer_client.get(self.list_url)
        assert resp.status_code == status.HTTP_200_OK
        # May return a list or a dict with items key
        items = resp.data if isinstance(resp.data, list) else resp.data.get('items', [])
        assert len(items) == 0

    def test_add_product_to_wishlist(self, buyer_client, product):
        resp = buyer_client.post(self.add_url, {'product_id': product.id})
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED)

    def test_list_wishlist_contains_added_product(self, buyer_client, product):
        buyer_client.post(self.add_url, {'product_id': product.id})
        resp = buyer_client.get(self.list_url)
        assert resp.status_code == status.HTTP_200_OK
        items = resp.data if isinstance(resp.data, list) else resp.data.get('items', [])
        product_ids = [
            i['product']['id'] if isinstance(i.get('product'), dict) else i.get('product_id', i.get('product'))
            for i in items
        ]
        assert product.id in product_ids

    def test_add_same_product_twice_is_idempotent(self, buyer_client, product):
        buyer_client.post(self.add_url, {'product_id': product.id})
        resp = buyer_client.post(self.add_url, {'product_id': product.id})
        # Must not create a duplicate — either 200/201 (idempotent) or 400 (validation)
        assert resp.status_code in (
            status.HTTP_200_OK,
            status.HTTP_201_CREATED,
            status.HTTP_400_BAD_REQUEST,
        )
        # Count items in wishlist must be 1
        list_resp = buyer_client.get(self.list_url)
        items = list_resp.data if isinstance(list_resp.data, list) else list_resp.data.get('items', [])
        assert len(items) == 1

    def test_add_nonexistent_product(self, buyer_client):
        resp = buyer_client.post(self.add_url, {'product_id': 99999})
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND)

    def test_remove_product_from_wishlist(self, buyer_client, product):
        buyer_client.post(self.add_url, {'product_id': product.id})
        resp = buyer_client.delete(self._remove_url(product.id))
        assert resp.status_code in (status.HTTP_200_OK, status.HTTP_204_NO_CONTENT)
        # Wishlist must be empty after removal
        list_resp = buyer_client.get(self.list_url)
        items = list_resp.data if isinstance(list_resp.data, list) else list_resp.data.get('items', [])
        assert len(items) == 0

    def test_wishlist_requires_auth(self, api_client):
        resp = api_client.get(self.list_url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_add_to_wishlist_requires_auth(self, api_client, product):
        resp = api_client.post(self.add_url, {'product_id': product.id})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_user_isolation_wishlist(self, buyer_client, buyer2_client, product):
        """Buyer 1's wishlist must not bleed into Buyer 2's wishlist."""
        buyer_client.post(self.add_url, {'product_id': product.id})
        resp = buyer2_client.get(self.list_url)
        assert resp.status_code == status.HTTP_200_OK
        items = resp.data if isinstance(resp.data, list) else resp.data.get('items', [])
        assert len(items) == 0

    def test_inactive_product_not_addable(self, buyer_client, product):
        product.is_active = False
        product.save(update_fields=['is_active'])
        resp = buyer_client.post(self.add_url, {'product_id': product.id})
        assert resp.status_code in (status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND)
