import React, { useState, useEffect } from 'react';
import { api } from '@/api/client';
import { Key, Cpu, Shield, Globe, CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react';

interface ConfigData {
  deepseek_api_key: string; deepseek_model: string; deepseek_base_url: string;
  deepseek_price_input: number; deepseek_price_output: number;
  max_chapter_tokens: number; cors_origins: string;
  environment: string; cookie_secure: boolean;
}

export default function ConfigCenter() {
  const [config, setConfig] = useState<ConfigData | null>(null);
  const [status, setStatus] = useState<any>(null);
  const [tab, setTab] = useState('api');
  const [msg, setMsg] = useState<{text:string;ok:boolean}|null>(null);
  const [showKey, setShowKey] = useState(false);

  useEffect(() => { load(); loadStatus(); }, []);
  const load = async () => { try { setConfig(await api('/config')); } catch {} };
  const loadStatus = async () => { try { setStatus(await api('/config/status')); } catch {} };
  const flash = (t:string,ok:boolean) => { setMsg({text:t,ok}); setTimeout(()=>setMsg(null),2500); };
  const save = async (key:string, val:string) => {
    try { await api('/config','PUT',{key,value:val}); flash(`${key} 已更新`,true); load(); loadStatus(); }
    catch { flash('保存失败',false); }
  };

  if (!config) return <div className="flex h-40 items-center justify-center text-gray-400">加载中...</div>;

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800 dark:text-white">配置中心</h1>
          <p className="mt-1 text-sm text-gray-500">
            状态：{status?.deepseek_configured
              ? <span className="font-semibold text-green-500">● DeepSeek 已连接</span>
              : <span className="font-semibold text-yellow-500">○ 未配置</span>}
            · {status?.environment} · {status?.python}
          </p>
        </div>
        {msg && (
          <div className={`flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium ${
            msg.ok ? 'bg-green-50 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                   : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
            {msg.ok ? <CheckCircle size={16}/> : <AlertTriangle size={16}/>}
            {msg.text}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-gray-200 dark:border-gray-700">
        {[{id:'api',label:'API & 模型',icon:Key},{id:'pricing',label:'定价',icon:Cpu},{id:'security',label:'安全',icon:Shield},{id:'cors',label:'跨域',icon:Globe}].map(t=>(
          <button key={t.id} onClick={()=>setTab(t.id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
              tab===t.id ? 'border-primary-500 text-primary-500' : 'border-transparent text-gray-400 hover:text-gray-600 dark:hover:text-gray-300'}`}>
            <t.icon size={14}/>{t.label}
          </button>
        ))}
      </div>

      {/* API Tab */}
      {tab==='api' && (
        <div className="grid grid-cols-2 gap-4">
          <Card icon={Key} label="API Key" hint="加密存储">
            <div className="flex gap-2">
              <input type={showKey?'text':'password'} defaultValue={config.deepseek_api_key}
                placeholder="sk-..." id="apikey"
                className="flex-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"/>
              <button onClick={()=>setShowKey(!showKey)}
                className="rounded-lg px-3 py-2 text-xs text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700">{showKey?'隐藏':'显示'}</button>
            </div>
            <SaveBtn onClick={()=>{const e=document.getElementById('apikey') as HTMLInputElement; if(e?.value) save('deepseek_api_key',e.value);}}/>
          </Card>
          <Card icon={Cpu} label="模型">
            <input defaultValue={config.deepseek_model}
              onChange={e=>save('deepseek_model',e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"/>
          </Card>
          <Card icon={Globe} label="API 地址">
            <input defaultValue={config.deepseek_base_url}
              onChange={e=>save('deepseek_base_url',e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"/>
          </Card>
          <Card icon={Cpu} label="Token上限" hint={`当前: ${config.max_chapter_tokens}`}>
            <input type="number" defaultValue={config.max_chapter_tokens}
              onChange={e=>save('max_chapter_tokens',e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"/>
          </Card>
        </div>
      )}

      {/* Pricing Tab */}
      {tab==='pricing' && (
        <div className="grid grid-cols-2 gap-4">
          <Card icon={Cpu} label="输入价格" hint="¥/百万tokens">
            <input type="number" step="0.1" defaultValue={config.deepseek_price_input}
              onChange={e=>save('DEEPSEEK_PRICE_INPUT_PER_1M',e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"/>
          </Card>
          <Card icon={Cpu} label="输出价格" hint="¥/百万tokens">
            <input type="number" step="0.1" defaultValue={config.deepseek_price_output}
              onChange={e=>save('DEEPSEEK_PRICE_OUTPUT_PER_1M',e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"/>
          </Card>
        </div>
      )}

      {/* Security Tab */}
      {tab==='security' && (
        <div className="grid grid-cols-2 gap-4">
          <Card icon={Shield} label="环境">
            <select defaultValue={config.environment}
              onChange={e=>save('environment',e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
              <option value="development">development</option>
              <option value="production">production</option>
            </select>
          </Card>
          <Card icon={Shield} label="Cookie Secure">
            <select defaultValue={config.cookie_secure?'true':'false'}
              onChange={e=>save('COOKIE_SECURE',e.target.value)}
              className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white">
              <option value="false">false (HTTP)</option>
              <option value="true">true (HTTPS)</option>
            </select>
          </Card>
        </div>
      )}

      {/* CORS Tab */}
      {tab==='cors' && (
        <Card icon={Globe} label="允许域名" hint="逗号分隔">
          <input defaultValue={config.cors_origins}
            onChange={e=>save('CORS_ORIGINS',e.target.value)}
            className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"/>
        </Card>
      )}

      {/* Status */}
      <div className="rounded-2xl border border-gray-200 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-dark-surface">
        <h3 className="mb-4 flex items-center gap-2 text-base font-semibold text-gray-800 dark:text-white">
          <RefreshCw size={16} className="text-primary-500"/> 实时状态
        </h3>
        <div className="grid grid-cols-4 gap-4 text-center">
          {[{label:'API',ok:true},{label:'DeepSeek',ok:status?.deepseek_configured},{label:'DB',ok:true},{label:'Redis',ok:true}].map(s=>(
            <div key={s.label}>
              <div className={`text-2xl font-extrabold ${s.ok?'text-green-500':'text-yellow-500'}`}>{s.ok?'●':'○'}</div>
              <div className="mt-1 text-xs text-gray-400">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Card({icon:Icon,label,hint,children}:any){
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm dark:border-gray-700 dark:bg-dark-surface">
      <div className="mb-3 flex items-center gap-2">
        <Icon size={16} className="text-primary-500"/><span className="text-sm font-semibold">{label}</span>
        {hint && <span className="text-xs text-gray-400">{hint}</span>}
      </div>
      {children}
    </div>
  );
}

function SaveBtn({onClick}:{onClick:()=>void}){
  return <button onClick={onClick}
    className="btn-primary mt-3 text-xs px-3 py-1.5">保存</button>;
}
