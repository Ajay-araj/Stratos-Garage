"""
Authentication & user management tests.
Covers: register, login, logout, token refresh, forgot/reset password,
        profile, change password, address CRUD.
"""
import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework import status


# ─── Register ─────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRegister:
    url = '/api/users/register/'

    def test_register_success(self, api_client):
        resp = api_client.post(self.url, {
            'username': 'newuser', 'email': 'newuser@test.com',
            'password': 'StrongPass123!', 'password2': 'StrongPass123!',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert 'user' in resp.data
        assert resp.data['user']['role'] == 'buyer'

    def test_register_as_seller(self, api_client):
        resp = api_client.post(self.url, {
            'username': 'sellerX', 'email': 'sellerX@test.com',
            'password': 'StrongPass123!', 'password2': 'StrongPass123!',
            'role': 'seller',
        })
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['user']['role'] == 'seller'

    def test_register_duplicate_email(self, api_client, buyer):
        resp = api_client.post(self.url, {
            'username': 'other', 'email': buyer.email,
            'password': 'StrongPass123!', 'password2': 'StrongPass123!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_duplicate_username(self, api_client, buyer):
        resp = api_client.post(self.url, {
            'username': buyer.username, 'email': 'unique@test.com',
            'password': 'StrongPass123!', 'password2': 'StrongPass123!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_password_mismatch(self, api_client):
        resp = api_client.post(self.url, {
            'username': 'mismatch', 'email': 'mm@test.com',
            'password': 'StrongPass123!', 'password2': 'WrongPass456!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_weak_password(self, api_client):
        resp = api_client.post(self.url, {
            'username': 'weakuser', 'email': 'weak@test.com',
            'password': '123', 'password2': '123',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_invalid_email(self, api_client):
        resp = api_client.post(self.url, {
            'username': 'bademail', 'email': 'not-an-email',
            'password': 'StrongPass123!', 'password2': 'StrongPass123!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_register_missing_fields(self, api_client):
        resp = api_client.post(self.url, {'username': 'incomplete'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Login ────────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogin:
    url = '/api/users/login/'

    def test_login_success(self, api_client, buyer):
        resp = api_client.post(self.url, {
            'username': buyer.username, 'password': 'TestPass123!',
        })
        assert resp.status_code == status.HTTP_200_OK
        assert 'access' in resp.data
        assert 'refresh' in resp.data

    def test_login_wrong_password(self, api_client, buyer):
        resp = api_client.post(self.url, {
            'username': buyer.username, 'password': 'WrongPassword!',
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        resp = api_client.post(self.url, {
            'username': 'ghost', 'password': 'anything',
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_empty_credentials(self, api_client):
        resp = api_client.post(self.url, {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Token Refresh ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTokenRefresh:
    url = '/api/users/token/refresh/'

    def test_refresh_success(self, api_client, buyer):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = str(RefreshToken.for_user(buyer))
        resp = api_client.post(self.url, {'refresh': refresh})
        assert resp.status_code == status.HTTP_200_OK
        assert 'access' in resp.data

    def test_refresh_invalid_token(self, api_client):
        resp = api_client.post(self.url, {'refresh': 'completely.invalid.token'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_empty(self, api_client):
        resp = api_client.post(self.url, {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Logout ───────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogout:
    url = '/api/users/logout/'

    def test_logout_success(self, buyer_client, buyer):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = str(RefreshToken.for_user(buyer))
        resp = buyer_client.post(self.url, {'refresh': refresh})
        assert resp.status_code == status.HTTP_200_OK

    def test_logout_blacklists_token(self, buyer_client, buyer):
        """Token cannot be used again after blacklisting."""
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh_obj = RefreshToken.for_user(buyer)
        refresh_str = str(refresh_obj)
        buyer_client.post(self.url, {'refresh': refresh_str})
        # Second attempt must fail
        resp = buyer_client.post(self.url, {'refresh': refresh_str})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_no_token(self, buyer_client):
        resp = buyer_client.post(self.url, {})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_invalid_token(self, buyer_client):
        resp = buyer_client.post(self.url, {'refresh': 'bad.token.here'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_logout_requires_auth(self, api_client):
        resp = api_client.post(self.url, {'refresh': 'anything'})
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Profile ──────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProfile:
    url = '/api/users/profile/'

    def test_get_profile(self, buyer_client, buyer):
        resp = buyer_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['username'] == buyer.username
        assert resp.data['email'] == buyer.email
        # Password must never be in response
        assert 'password' not in resp.data

    def test_update_phone(self, buyer_client):
        resp = buyer_client.patch(self.url, {'phone': '+919876543210'})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['phone'] == '+919876543210'

    def test_cannot_change_role_via_profile(self, buyer_client):
        """Role is read-only — must be ignored silently."""
        resp = buyer_client.patch(self.url, {'role': 'admin'})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['role'] == 'buyer'

    def test_profile_requires_auth(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Change Password ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestChangePassword:
    url = '/api/users/profile/change-password/'

    def test_change_password_success(self, buyer_client, buyer):
        resp = buyer_client.post(self.url, {
            'old_password': 'TestPass123!',
            'new_password': 'NewStrongPass456!',
            'new_password2': 'NewStrongPass456!',
        })
        assert resp.status_code == status.HTTP_200_OK
        buyer.refresh_from_db()
        assert buyer.check_password('NewStrongPass456!')

    def test_change_password_wrong_old(self, buyer_client):
        resp = buyer_client.post(self.url, {
            'old_password': 'WrongOldPass!',
            'new_password': 'NewPass123!',
            'new_password2': 'NewPass123!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_mismatch_new(self, buyer_client):
        resp = buyer_client.post(self.url, {
            'old_password': 'TestPass123!',
            'new_password': 'NewPass123!',
            'new_password2': 'DifferentNew456!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_requires_auth(self, api_client):
        resp = api_client.post(self.url, {
            'old_password': 'x', 'new_password': 'y', 'new_password2': 'y',
        })
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Forgot / Reset Password ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestForgotPassword:
    url = '/api/users/forgot-password/'

    def test_returns_ok_for_unknown_email(self, api_client):
        """Never reveal whether the email exists."""
        resp = api_client.post(self.url, {'email': 'ghost@test.com'})
        assert resp.status_code == status.HTTP_200_OK

    def test_returns_ok_for_known_email(self, api_client, buyer):
        resp = api_client.post(self.url, {'email': buyer.email})
        assert resp.status_code == status.HTTP_200_OK

    def test_invalid_email_format(self, api_client):
        resp = api_client.post(self.url, {'email': 'not-an-email'})
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestResetPassword:
    forgot_url = '/api/users/forgot-password/'
    reset_url = '/api/users/reset-password/'

    def _get_valid_token(self, buyer):
        from users.models import PasswordResetToken
        PasswordResetToken.objects.filter(user=buyer).delete()
        token = PasswordResetToken.objects.create(
            user=buyer,
            expires_at=timezone.now() + timedelta(hours=1),
        )
        return token

    def test_reset_password_success(self, api_client, buyer):
        token = self._get_valid_token(buyer)
        resp = api_client.post(self.reset_url, {
            'token': str(token.token),
            'new_password': 'BrandNewPass123!',
            'new_password2': 'BrandNewPass123!',
        })
        assert resp.status_code == status.HTTP_200_OK
        buyer.refresh_from_db()
        assert buyer.check_password('BrandNewPass123!')

    def test_reset_token_is_consumed(self, api_client, buyer):
        """Token must be marked as used after first successful reset."""
        token = self._get_valid_token(buyer)
        api_client.post(self.reset_url, {
            'token': str(token.token),
            'new_password': 'BrandNewPass123!',
            'new_password2': 'BrandNewPass123!',
        })
        token.refresh_from_db()
        assert token.is_used is True

    def test_reset_expired_token(self, api_client, buyer):
        from users.models import PasswordResetToken
        token = PasswordResetToken.objects.create(
            user=buyer,
            expires_at=timezone.now() - timedelta(hours=1),
        )
        resp = api_client.post(self.reset_url, {
            'token': str(token.token),
            'new_password': 'NewPass123!',
            'new_password2': 'NewPass123!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_reset_used_token(self, api_client, buyer):
        from users.models import PasswordResetToken
        token = PasswordResetToken.objects.create(
            user=buyer,
            expires_at=timezone.now() + timedelta(hours=1),
            is_used=True,
        )
        resp = api_client.post(self.reset_url, {
            'token': str(token.token),
            'new_password': 'NewPass123!',
            'new_password2': 'NewPass123!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_reset_invalid_uuid(self, api_client):
        resp = api_client.post(self.reset_url, {
            'token': 'not-a-uuid',
            'new_password': 'NewPass123!',
            'new_password2': 'NewPass123!',
        })
        assert resp.status_code == status.HTTP_400_BAD_REQUEST


# ─── Addresses ────────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAddress:
    list_url = '/api/users/addresses/'

    def _addr_payload(self, **overrides):
        base = {
            'full_name': 'Test Buyer',
            'phone': '9876543210',
            'address_line1': '123 Test St',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'pincode': '400001',
        }
        base.update(overrides)
        return base

    def test_create_address(self, buyer_client):
        resp = buyer_client.post(self.list_url, self._addr_payload())
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['city'] == 'Mumbai'

    def test_list_addresses(self, buyer_client):
        buyer_client.post(self.list_url, self._addr_payload())
        resp = buyer_client.get(self.list_url)
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data) == 1

    def test_get_address_detail(self, buyer_client):
        create = buyer_client.post(self.list_url, self._addr_payload())
        addr_id = create.data['id']
        resp = buyer_client.get(f'{self.list_url}{addr_id}/')
        assert resp.status_code == status.HTTP_200_OK

    def test_update_address(self, buyer_client):
        create = buyer_client.post(self.list_url, self._addr_payload())
        addr_id = create.data['id']
        resp = buyer_client.patch(f'{self.list_url}{addr_id}/', {'city': 'Pune'})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['city'] == 'Pune'

    def test_delete_address(self, buyer_client):
        create = buyer_client.post(self.list_url, self._addr_payload())
        addr_id = create.data['id']
        resp = buyer_client.delete(f'{self.list_url}{addr_id}/')
        assert resp.status_code == status.HTTP_204_NO_CONTENT
        resp2 = buyer_client.get(f'{self.list_url}{addr_id}/')
        assert resp2.status_code == status.HTTP_404_NOT_FOUND

    def test_default_address_toggling(self, buyer_client):
        """Setting a second address as default must unset the first."""
        a1 = buyer_client.post(self.list_url, self._addr_payload(is_default=True))
        a2 = buyer_client.post(self.list_url, self._addr_payload(
            full_name='Second', address_line1='456 Other St', is_default=True,
        ))
        from users.models import Address
        addr1 = Address.objects.get(pk=a1.data['id'])
        assert addr1.is_default is False

    def test_cannot_access_other_users_address(self, buyer_client, buyer2_client):
        create = buyer_client.post(self.list_url, self._addr_payload())
        addr_id = create.data['id']
        resp = buyer2_client.get(f'{self.list_url}{addr_id}/')
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    def test_address_requires_auth(self, api_client):
        resp = api_client.get(self.list_url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


# ─── Health Check ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestHealthCheck:
    url = '/api/health/'

    def test_health_check_ok(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['status'] == 'ok'
        assert 'database' in resp.data['checks']
