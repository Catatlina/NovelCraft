import React, { useState, useEffect } from 'react';
import { Settings, LogOut, User, Shield, Key } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { api } from '@/api/client';
import { useAuthStore } from '@/store/authStore';
import '@/styles/novelcraft-theme.css';

export default function SettingsV2() {
  const nav = useNavigate();
  const user = useAuthStore(s => s.user);
  const logout = useAuthStore(s => s.logout);
  const [oldPw, setOldPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [msg, setMsg] = useState('');

  const handleLogout = async () => {
    try { await api('/auth/logout', 'POST', {}); } catch {}
    logout(); nav('/login');
  };

  const changePw = async () => {
    if (!oldPw || newPw.length < 8) { setMsg('新密码至少8位'); return; }
    try {
      await api('/auth/change-password', 'POST', { old_password: oldPw, new_password: newPw });
      setMsg('密码修改成功'); setOldPw(''); setNewPw('');
    } catch { setMsg('修改失败'); }
  };

  return (
    <div style={{ maxWidth: 600 }}>
      <h1 className="nc-page-title"><Settings size={22} style={{ marginRight: 8, display: 'inline' }} />设置</h1>

      <div className="nc-card" style={{ padding: 20, marginBottom: 14 }}>
        <h3 className="nc-section-title"><User size={16} /> 账户信息</h3>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '8px 12px', fontSize: 13 }}>
          <span style={{ color: 'var(--nc-text-dim)' }}>用户名</span><span>{user?.username || '-'}</span>
          <span style={{ color: 'var(--nc-text-dim)' }}>邮箱</span><span>{user?.email || '-'}</span>
          <span style={{ color: 'var(--nc-text-dim)' }}>角色</span>
          <span className="nc-tag nc-tag-accent">{user?.is_admin ? '管理员' : '用户'}</span>
        </div>
      </div>

      <div className="nc-card" style={{ padding: 20, marginBottom: 14 }}>
        <h3 className="nc-section-title"><Key size={16} /> 修改密码</h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <input className="nc-input" type="password" placeholder="旧密码" value={oldPw} onChange={e => setOldPw(e.target.value)} />
          <input className="nc-input" type="password" placeholder="新密码 (≥8位)" value={newPw} onChange={e => setNewPw(e.target.value)} />
          <button className="nc-btn nc-btn-primary nc-btn-sm" onClick={changePw}>修改</button>
          {msg && <p style={{ fontSize: 12, color: msg.includes('成功') ? 'var(--nc-success)' : 'var(--nc-danger)' }}>{msg}</p>}
        </div>
      </div>

      <div className="nc-card" style={{ padding: 20, marginBottom: 14 }}>
        <h3 className="nc-section-title"><Shield size={16} /> 快捷入口</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="nc-btn nc-btn-secondary nc-btn-sm" onClick={() => nav('/config')}>
            <Settings size={14} /> 配置中心
          </button>
          <button className="nc-btn nc-btn-secondary nc-btn-sm" onClick={handleLogout} style={{ color: 'var(--nc-danger)' }}>
            <LogOut size={14} /> 退出登录
          </button>
        </div>
      </div>
    </div>
  );
}
