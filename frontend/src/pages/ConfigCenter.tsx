import React, { useState, useEffect } from 'react';
import { api } from '@/api/client';
import { Key, Cpu, Shield, Globe, Save, RefreshCw, CheckCircle, AlertTriangle } from 'lucide-react';
import '@/styles/novelcraft-theme.css';

interface ConfigData {
  deepseek_api_key: string;
  deepseek_model: string;
  deepseek_base_url: string;
  deepseek_price_input: number;
  deepseek_price_output: number;
  max_chapter_tokens: number;
  cors_origins: string;
  environment: string;
  cookie_secure: boolean;
}

const TABS = [
  { id: 'api', label: 'API & 模型', icon: Key },
  { id: 'pricing', label: '定价', icon: Cpu },
  { id: 'security', label: '安全', icon: Shield },
  { id: 'cors', label: '跨域', icon: Globe },
];

export default function ConfigCenter() {
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [tab, setTab] = useState('api');
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [msg, setMsg] = useState<{text: string; ok: boolean} | null>(null);
  const [showKey, setShowKey] = useState(false);

  useEffect(() => { loadConfig(); loadStatus(); }, []);

  const loadConfig = async () => {
    const d = await api('/config');
    setConfig(d);
  };
  const loadStatus = async () => {
    const s = await api('/config/status');
    setStatus(s);
  };

  const flash = (text: string, ok: boolean) => {
    setMsg({text, ok});
    setTimeout(() => setMsg(null), 2500);
  };

  const save = async (key: string, value: string) => {
    setSaving(s => ({...s, [key]: true}));
    try {
      await api('/config', 'PUT', { key, value });
      flash(`${key} 已更新`, true);
      loadConfig();
      loadStatus();
    } catch {
      flash('保存失败', false);
    } finally {
      setSaving(s => ({...s, [key]: false}));
    }
  };

  if (!config) return <div className="nc-page"><div className="nc-spinner">加载中...</div></div>;

  return (
    <div className="nc-main">
      <div className="nc-page">
        {/* Header */}
        <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom: 24}}>
          <div>
            <h1 className="nc-page-title" style={{marginBottom: 4}}>配置中心</h1>
            <p style={{color:'var(--nc-text-dim)', fontSize:13}}>
              系统状态：
              <span style={{color: status?.deepseek_configured ? 'var(--nc-success)' : 'var(--nc-warning)', fontWeight:600}}>
                {status?.deepseek_configured ? '● DeepSeek 已连接' : '○ DeepSeek 未配置'}
              </span>
              &nbsp;· {status?.environment} · {status?.python}
            </p>
          </div>
          {msg && (
            <div className={`nc-card ${msg.ok ? '' : ''}`} style={{
              padding:'10px 20px', display:'flex', alignItems:'center', gap:8,
              borderColor: msg.ok ? 'var(--nc-success)' : 'var(--nc-danger)',
              animation: 'fadeIn 0.3s ease-out'
            }}>
              {msg.ok ? <CheckCircle size={16} color="var(--nc-success)"/> : <AlertTriangle size={16} color="var(--nc-danger)"/>}
              <span style={{fontSize:13}}>{msg.text}</span>
            </div>
          )}
        </div>

        {/* Tabs */}
        <div className="nc-tabs">
          {TABS.map(t => (
            <div key={t.id} className={`nc-tab ${tab === t.id ? 'active' : ''}`} onClick={() => setTab(t.id)}>
              <t.icon size={14} style={{marginRight:6}}/>{t.label}
            </div>
          ))}
        </div>

        {/* API Tab */}
        {tab === 'api' && (
          <div className="nc-grid-2 nc-fade-in">
            <ConfigCard icon={Key} label="API Key" hint="DeepSeek API 密钥，加密存储">
              <div style={{display:'flex', gap:8}}>
                <input className="nc-input" type={showKey ? 'text' : 'password'}
                  defaultValue={config.deepseek_api_key}
                  placeholder="sk-..." style={{flex:1}}/>
                <button className="nc-btn nc-btn-ghost nc-btn-sm" onClick={() => setShowKey(!showKey)}>
                  {showKey ? '隐藏' : '显示'}
                </button>
              </div>
              <SaveBtn saving={!!saving['deepseek_api_key']} onClick={() => {
                const el = document.querySelector<HTMLInputElement>('.nc-input');
                if (el?.value) save('deepseek_api_key', el.value);
              }}/>
            </ConfigCard>

            <ConfigCard icon={Cpu} label="模型" hint="调用模型名称">
              <input className="nc-input" defaultValue={config.deepseek_model}
                onChange={e => save('deepseek_model', e.target.value)}/>
            </ConfigCard>

            <ConfigCard icon={Globe} label="API 地址" hint="Base URL">
              <input className="nc-input" defaultValue={config.deepseek_base_url}
                onChange={e => save('deepseek_base_url', e.target.value)}/>
            </ConfigCard>

            <ConfigCard icon={Settings} label="章节Token上限" hint={`当前: ${config.max_chapter_tokens}`}>
              <input className="nc-input" type="number" defaultValue={config.max_chapter_tokens}
                onChange={e => save('max_chapter_tokens', e.target.value)}/>
            </ConfigCard>
          </div>
        )}

        {/* Pricing Tab */}
        {tab === 'pricing' && (
          <div className="nc-grid-2 nc-fade-in">
            <ConfigCard icon={Cpu} label="输入价格" hint="¥/百万tokens">
              <input className="nc-input" type="number" step="0.1" defaultValue={config.deepseek_price_input}
                onChange={e => save('DEEPSEEK_PRICE_INPUT_PER_1M', e.target.value)}/>
            </ConfigCard>
            <ConfigCard icon={Cpu} label="输出价格" hint="¥/百万tokens">
              <input className="nc-input" type="number" step="0.1" defaultValue={config.deepseek_price_output}
                onChange={e => save('DEEPSEEK_PRICE_OUTPUT_PER_1M', e.target.value)}/>
            </ConfigCard>
          </div>
        )}

        {/* Security Tab */}
        {tab === 'security' && (
          <div className="nc-grid-2 nc-fade-in">
            <ConfigCard icon={Shield} label="环境" hint="production 强制 HTTPS">
              <select className="nc-input" defaultValue={config.environment}
                onChange={e => save('environment', e.target.value)}>
                <option value="development">development</option>
                <option value="production">production</option>
              </select>
            </ConfigCard>
            <ConfigCard icon={Shield} label="Cookie Secure" hint="HTTPS 时启用">
              <select className="nc-input" defaultValue={config.cookie_secure ? 'true' : 'false'}
                onChange={e => save('COOKIE_SECURE', e.target.value)}>
                <option value="false">false (HTTP)</option>
                <option value="true">true (HTTPS)</option>
              </select>
            </ConfigCard>
          </div>
        )}

        {/* CORS Tab */}
        {tab === 'cors' && (
          <div className="nc-fade-in">
            <ConfigCard icon={Globe} label="CORS 允许域名" hint="逗号分隔">
              <input className="nc-input" defaultValue={config.cors_origins}
                onChange={e => save('CORS_ORIGINS', e.target.value)}/>
            </ConfigCard>
          </div>
        )}

        {/* Status card */}
        <div className="nc-card" style={{marginTop: 32}}>
          <div className="nc-section-title">
            <RefreshCw size={16} color="var(--nc-accent)"/> 实时状态
          </div>
          <div className="nc-grid-4" style={{marginTop:12}}>
            <StatusItem label="API" ok />
            <StatusItem label="DeepSeek" ok={status?.deepseek_configured}/>
            <StatusItem label="DB" ok />
            <StatusItem label="Redis" ok />
          </div>
        </div>
      </div>
    </div>
  );
}

function ConfigCard({ icon: Icon, label, hint, children }: any) {
  return (
    <div className="nc-card" style={{display:'flex', flexDirection:'column', gap:10}}>
      <div style={{display:'flex', alignItems:'center', gap:8, marginBottom:4}}>
        <Icon size={16} color="var(--nc-primary)"/>
        <span style={{fontWeight:600, fontSize:14}}>{label}</span>
        <span style={{fontSize:11, color:'var(--nc-text-dim)'}}>{hint}</span>
      </div>
      {children}
    </div>
  );
}

function SaveBtn({ saving, onClick }: { saving: boolean; onClick: () => void }) {
  return (
    <button className={`nc-btn nc-btn-primary nc-btn-sm`} onClick={onClick} disabled={saving}
      style={{marginTop: 6}}>
      {saving ? <RefreshCw size={14} className="nc-spinner"/> : <Save size={14}/>}
      {saving ? '保存中...' : '保存'}
    </button>
  );
}

function StatusItem({ label, ok }: { label: string; ok: boolean }) {
  return (
    <div style={{textAlign:'center'}}>
      <div style={{fontSize:28, fontWeight:800, color: ok ? 'var(--nc-success)' : 'var(--nc-warning)'}}>
        {ok ? '●' : '○'}
      </div>
      <div style={{fontSize:11, color:'var(--nc-text-dim)', marginTop:4}}>{label}</div>
    </div>
  );
}
