"""Unit tests for security.py — password hashing + JWT tokens"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
    decode_token_with_type,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        h = hash_password("my-secret-password")
        assert verify_password("my-secret-password", h)

    def test_wrong_password(self):
        h = hash_password("correct")
        assert not verify_password("wrong", h)

    def test_empty_password(self):
        h = hash_password("")
        assert verify_password("", h)

    def test_hash_is_different_each_time(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # different salts

    def test_special_chars(self):
        h = hash_password("中文密码!@#$%^&*()")
        assert verify_password("中文密码!@#$%^&*()", h)

    def test_corrupted_hash(self):
        assert not verify_password("x", "bad:format")
        assert not verify_password("x", ":")
        assert not verify_password("x", "not-hex:not-hex")

    def test_verify_none(self):
        assert not verify_password("x", None)


class TestJWT:
    def test_create_and_decode(self):
        token = create_token("user-123")
        user_id = decode_token(token)
        assert user_id == "user-123"

    def test_access_token_type(self):
        token = create_access_token("user-456")
        uid = decode_token_with_type(token, "access")
        assert uid == "user-456"

    def test_refresh_token_type(self):
        token = create_refresh_token("user-789")
        uid = decode_token_with_type(token, "refresh")
        assert uid == "user-789"

    def test_wrong_type_rejected(self):
        token = create_access_token("user")
        assert decode_token_with_type(token, "refresh") is None

    def test_invalid_token(self):
        assert decode_token("not.a.jwt") is None
        assert decode_token("") is None

    def test_tampered_token(self):
        token = create_token("user")
        # 翻转中间某个字符而不是最后一个字符：JWT末尾的base64编码存在padding
        # 冗余，翻转最后一个字符有极小概率解码出和原文完全相同的字节
        # (相当于没有真正篡改)，导致这个测试偶发性失败。翻转中间字符
        # (落在签名段内部)不受这个边界情况影响。
        mid = len(token) // 2
        tampered = token[:mid] + ("A" if token[mid] != "A" else "B") + token[mid + 1:]
        assert decode_token(tampered) is None

    def test_backward_compat(self):
        token = create_token("old-style")
        assert decode_token(token) == "old-style"
