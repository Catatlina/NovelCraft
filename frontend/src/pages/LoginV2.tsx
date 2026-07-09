import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogIn, UserPlus, Sparkles, Eye, EyeOff } from 'lucide-react';
import { api } from '@/api/client';
import '@/styles/novelcraft-theme.css';

export default function Login() {
  const nav = useNavigate();
  const [tab, setTab] = useState<'login'|'register'>('login');
  const [user, setUser] = useState('');
  const [pass, setPass] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState('');

  const submit = async () => {
    if (!user || !pass || pass.length < 8) { setErr('用户名非空，密码≥8位'); return; }
    if (tab === 'register' && pass !== confirm) { setErr('两次密码不一致'); return; }
    setLoading(true); setErr('');
    try {
      const ep = tab === 'login' ? '/auth/login' : '/auth/register';
      await api(ep, 'POST', { username: user, password: pass });
      nav('/');
    } catch (e: any) { setErr(e?.detail || '操作失败'); }
    finally { setLoading(false); }
  };

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: 'var(--nc-bg)', position: 'relative', overflow: 'hidden' }}>
      {/* Ambient glow */}
      <div style={{ position: 'absolute', top: '-20%', left: '10%', width: 400, height: 400,
        borderRadius: '50%', background: 'radial-gradient(circle, rgba(255,107,53,0.08), transparent 70%)' }} />
      <div style={{ position: 'absolute', bottom: '-10%', right: '5%', width: 300, height: 300,
        borderRadius: '50%', background: 'radial-gradient(circle, rgba(0,229,255,0.06), transparent 70%)' }} />

      <div className="nc-card" style={{ width: 400, padding: '32px 36px', position: 'relative', zIndex: 1 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ fontSize: 32, fontWeight: 800, marginBottom: 4,
            background: 'linear-gradient(135deg, var(--nc-primary), var(--nc-accent))',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            <Sparkles size={28} style={{ display: 'inline', marginRight: 8 }} />
            星禾写作助手
          </div>
          <p style={{ fontSize: 13, color: 'var(--nc-text-dim)' }}>AI 驱动的智能写作平台</p>
        </div>

        <div className="nc-tabs" style={{ marginBottom: 20 }}>
          <div className={`nc-tab ${tab === 'login' ? 'active' : ''}`} onClick={() => { setTab('login'); setErr(''); }}>
            <LogIn size={14} style={{ marginRight: 6 }} />登录
          </div>
          <div className={`nc-tab ${tab === 'register' ? 'active' : ''}`} onClick={() => { setTab('register'); setErr(''); }}>
            <UserPlus size={14} style={{ marginRight: 6 }} />注册
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--nc-text-dim)', marginBottom: 4, display: 'block' }}>用户名</label>
            <input className="nc-input" value={user} onChange={e => setUser(e.target.value)} placeholder="输入用户名" />
          </div>
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--nc-text-dim)', marginBottom: 4, display: 'block' }}>密码</label>
            <div style={{ position: 'relative' }}>
              <input className="nc-input" type={showPw ? 'text' : 'password'}
                value={pass} onChange={e => setPass(e.target.value)} placeholder="至少8位" />
              <button onClick={() => setShowPw(!showPw)}
                style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', color: 'var(--nc-text-dim)', cursor: 'pointer' }}>
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>
          {tab === 'register' && (
            <div>
              <label style={{ fontSize: 12, fontWeight: 600, color: 'var(--nc-text-dim)', marginBottom: 4, display: 'block' }}>确认密码</label>
              <input className="nc-input" type="password" value={confirm} onChange={e => setConfirm(e.target.value)} placeholder="再次输入" />
            </div>
          )}
          {err && <p style={{ fontSize: 12, color: 'var(--nc-danger)' }}>{err}</p>}
          <button className="nc-btn nc-btn-primary" onClick={submit} disabled={loading}
            style={{ width: '100%', padding: 12, fontSize: 15 }}>
            {loading ? '处理中...' : tab === 'login' ? '登录' : '注册'}
          </button>
        </div>
        <p style={{ textAlign: 'center', marginTop: 20, fontSize: 11, color: 'var(--nc-text-dim)' }}>
          星禾写作助手 v8.0 · AI 驱动的智能写作平台
        </p>
      </div>
    </div>
  );
}
