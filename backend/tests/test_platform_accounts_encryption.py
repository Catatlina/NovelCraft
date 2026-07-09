"""Unit tests for platform_accounts.py — encryption key fail-fast behavior (P2-fix).

覆盖点：
1. ACCOUNT_ENCRYPTION_KEY 未配置时，加密/解密必须 fail-fast 报错，
   不能像修复前那样静默生成一把用后即丢的临时密钥。
2. 配置了合法密钥后，加密解密应正常往返。
3. 配置了格式非法的密钥时，应给出明确的格式错误而不是静默兜底。
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import importlib

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException


def _reload_platform_accounts_with_key(key: str):
    """在设置好 settings.account_encryption_key 后重新加载模块，
    确保每个测试用例拿到干净的模块级缓存状态。"""
    from app.core.config import settings
    settings.account_encryption_key = key

    import app.api.platform_accounts as pa
    importlib.reload(pa)
    return pa


class TestEncryptionKeyFailFast:
    def test_missing_key_raises_clear_error(self):
        """未配置密钥时，加密应立即报错，而不是静默生成临时密钥。"""
        pa = _reload_platform_accounts_with_key("")
        with pytest.raises(HTTPException) as exc_info:
            pa.encrypt_credentials("some-secret-token")
        assert exc_info.value.status_code == 500
        assert "ACCOUNT_ENCRYPTION_KEY" in exc_info.value.detail

    def test_invalid_key_format_raises_clear_error(self):
        """密钥格式非法（非 32 字节 url-safe base64）时应明确报错。"""
        pa = _reload_platform_accounts_with_key("not-a-valid-fernet-key")
        with pytest.raises(HTTPException) as exc_info:
            pa.encrypt_credentials("some-secret-token")
        assert exc_info.value.status_code == 500

    def test_valid_key_roundtrip(self):
        """配置合法密钥后，加密解密应正常往返，不受影响。"""
        valid_key = Fernet.generate_key().decode()
        pa = _reload_platform_accounts_with_key(valid_key)

        plaintext = '{"email": "a@b.com", "password": "pw123"}'
        token = pa.encrypt_credentials(plaintext)
        assert token != plaintext

        decrypted = pa.decrypt_credentials(token)
        assert decrypted == plaintext

    def test_key_persists_across_calls_within_process(self):
        """同一进程内密钥只解析一次并缓存，不会每次调用重新生成不同密钥
        （这正是修复前 bug 的根源之一：确保修复后至少同进程内是稳定的）。"""
        valid_key = Fernet.generate_key().decode()
        pa = _reload_platform_accounts_with_key(valid_key)

        token1 = pa.encrypt_credentials("payload-1")
        token2 = pa.encrypt_credentials("payload-2")
        # 两次加密用的是同一把密钥，因此互相都能被同一个 fernet 实例解密
        assert pa.decrypt_credentials(token1) == "payload-1"
        assert pa.decrypt_credentials(token2) == "payload-2"
