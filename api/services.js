const BASE_URL = 'https://bridgetosuccess.learncentre.tech/public/study_api_sprint13_security_promo/';
const DOWNLOAD_API = 'https://r-gengpt-api.vercel.app/api/video/download?url=';
const PDF_BASE = 'https://bridgetosuccess.learncentre.tech/public/storage/pdf/';
const USER_ID = '12644';

function decodeQuery(raw) {
  if (!raw || typeof raw !== 'string' || raw.length > 12000) return {};
  try {
    const normalized = raw.replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(Buffer.from(normalized, 'base64').toString('utf8')) || {};
  } catch { return {}; }
}
function encodeWrap(data) {
  const json = JSON.stringify(data);
  return { d: Buffer.from(json, 'utf8').toString('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/g, '') };
}
function send(res, data, status = 200) {
  res.status(status).setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  return res.send(encodeWrap(data));
}
async function apiCall(fields) {
  const body = new URLSearchParams(fields);
  const r = await fetch(BASE_URL, { method: 'POST', headers: { 'User-Agent': 'okhttp/5.3.2', 'Content-Type': 'application/x-www-form-urlencoded' }, body, signal: AbortSignal.timeout(30000) });
  const txt = await r.text();
  try { return JSON.parse(txt); } catch { return { success: 0, error: `upstream_bad_json_${r.status}` }; }
}
function youtubeId(input) {
  const s = String(input || '').trim();
  const m = s.match(/(?:youtube\.com\/(?:[^/]+\/.+\/|(?:v|e(?:mbed)?)\/|.*[?&]v=)|youtu\.be\/)([^"&?/\s]{11})/i);
  if (m) return m[1];
  return /^[A-Za-z0-9_-]{11}$/.test(s) ? s : null;
}
async function videoInfo(input) {
  const id = youtubeId(input);
  if (!id) return null;
  const r = await fetch(DOWNLOAD_API + encodeURIComponent('https://youtu.be/' + id), { headers: { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json' }, signal: AbortSignal.timeout(45000) });
  const j = await r.json().catch(() => null);
  if (!j || j.status !== 'success' || !j.data || !Array.isArray(j.data.medias)) return null;
  return j.data;
}
function sizeOf(m) {
  const n = Number(m.contentLength || m.clen || m.size || 0);
  if (n > 0) return n;
  const mt = String(m.url || '').match(/[&?]clen=(\d+)/);
  return mt ? Number(mt[1]) : 0;
}
function buildFormats(data) {
  return data.medias.filter(m => m.type === 'video' && m.url && m.height).map(m => ({
    fid: String(m.formatId || ''), h: Number(m.height), e: m.ext || 'mp4', a: !!m.audioQuality,
    br: Number(m.bitrate || 0), fps: Number(m.fps || 0), s: sizeOf(m)
  })).sort((a,b) => b.h-a.h || Number(b.a)-Number(a.a) || b.br-a.br);
}
function buildStream(data, quality) {
  const videos=[], audios=[], muxed=[];
  for (const m of data.medias) {
    if (!m.url) continue;
    const item={ h:Number(m.height||0), e:m.ext||'mp4', url:m.url, mime:m.mimeType||(m.type==='audio'?'audio/mp4':'video/mp4'), br:Number(m.bitrate||0) };
    if (m.type==='video') (m.audioQuality ? muxed : videos).push(item);
    else if (m.type==='audio') audios.push(item);
  }
  audios.sort((a,b)=>b.br-a.br); videos.sort((a,b)=>a.h-b.h); muxed.sort((a,b)=>a.h-b.h);
  const bestAudio=audios[0]||null, list=[];
  for (const m of muxed) list.push({h:m.h,vUrl:m.url,vMime:m.mime,aUrl:null,aMime:null,muxed:true});
  for (const v of videos) list.push({h:v.h,vUrl:v.url,vMime:v.mime,aUrl:bestAudio?.url||null,aMime:bestAudio?.mime||null,muxed:false});
  const byH=new Map();
  for (const q of list) { const old=byH.get(q.h); if (!old || (q.muxed && !old.muxed)) byH.set(q.h,q); }
  const formats=[...byH.values()].sort((a,b)=>a.h-b.h);
  if (!formats.length) return null;
  let chosen=formats[0]; for (const f of formats) if (f.h<=quality) chosen=f;
  if (formats[formats.length-1].h<quality) chosen=formats[formats.length-1];
  return { chosen, formats };
}
async function proxyStream(url, res, filename, contentType) {
  const u = new URL(url);
  if (u.protocol !== 'https:') return res.status(400).end();
  const upstream = await fetch(u, { headers: { 'User-Agent': 'Mozilla/5.0' }, redirect: 'follow', signal: AbortSignal.timeout(120000) });
  if (!upstream.ok || !upstream.body) return res.status(502).end();
  res.status(200);
  res.setHeader('Content-Type', contentType || upstream.headers.get('content-type') || 'application/octet-stream');
  if (filename) res.setHeader('Content-Disposition', `attachment; filename*=UTF-8''${encodeURIComponent(filename)}`);
  res.setHeader('Cache-Control','no-store');
  const len=upstream.headers.get('content-length'); if (len) res.setHeader('Content-Length',len);
  const { Readable } = require('stream');
  return Readable.fromWeb(upstream.body).pipe(res);
}

module.exports = async (req, res) => {
  try {
    const q = decodeQuery(req.query.q);
    const action = q.a;
    if (action === 'courses') return send(res, await apiCall({tag:'allCourses',isEBook:'0',userId:USER_ID}));
    if (action === 'content') return send(res, await apiCall({tag:'getCategoryMixed',courseId:String(q.c||''),userId:USER_ID,categoryId:String(q.k||'')}));
    if (action === 'formats' || action === 'stream' || action === 'dl_video') {
      const data = await videoInfo(q.v);
      if (!data) return send(res,{success:0,error:'video_unavailable'},502);
      if (action === 'formats') return send(res,{success:1,title:data.title||'',formats:buildFormats(data)});
      if (action === 'stream') {
        const stream=buildStream(data,Number(q.h||720));
        return send(res,stream?{success:1,title:data.title||'',...stream}:{success:0,error:'no_streams'},stream?200:404);
      }
      const target=data.medias.find(m=>String(m.formatId||'')===String(q.f||''));
      if (!target || !target.url) return res.status(404).end();
      const clean=String(data.title||'video').replace(/[\\/:*?"<>|\x00-\x1F]+/g,'_').replace(/\s+/g,' ').trim().slice(0,140)||'video';
      const quality=target.quality || `${target.height||''}p`;
      const ext=String(target.ext||'mp4').replace(/[^a-z0-9]/gi,'')||'mp4';
      return await proxyStream(target.url,res,`${clean} - ${quality}.${ext}`,'application/octet-stream');
    }
    if (action === 'dl_pdf') {
      const file=String(q.f||'');
      if (!/^[a-z0-9]+\.pdf$/i.test(file)) return res.status(400).end();
      return await proxyStream(PDF_BASE+file,res,file,'application/pdf');
    }
    return send(res,{success:0,error:'unknown_action'},400);
  } catch (e) {
    console.error('BTS API error:',e);
    if (!res.headersSent) return send(res,{success:0,error:'server_error'},500);
    return res.end();
  }
};
