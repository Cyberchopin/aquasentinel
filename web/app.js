const $ = id => document.getElementById(id);
const labels = {monitor:'Monitor',needs_corroboration:'Needs corroboration',review_recommended:'Review recommended',dismissed:'Dismissed',follow_up_required:'Follow-up required'};
let snapshot, sequence=0, busy=false;
let anchor=Date.now();
const text = (tag, value, className) => {const e=document.createElement(tag);e.textContent=value;if(className)e.className=className;return e;};
async function api(path, data){const r=await fetch(path,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:undefined);const v=await r.json();if(!r.ok)throw Error(v.error||'Request failed');return v;}
function stamp(value){return new Date(value).toISOString().slice(11,19)+' UTC';}
async function refresh(){
 const ticket=++sequence;
 $('review-submit').disabled=true;
 try{
  const present=$('time').value==='360';
  const at=new Date(present?Date.now():anchor-(360-Number($('time').value))*60000).toISOString();
  const result=await api('/api/snapshot?stream='+encodeURIComponent($('stream').value)+'&as_of='+encodeURIComponent(at));
  if(ticket!==sequence)return;
  snapshot=result;
  $('clock').textContent=(present?'Present · ':'Replay · ')+new Date(at).toISOString().replace('T',' ').slice(0,19)+' UTC';
  $('state').textContent=labels[result.display_state];
  $('state').className='badge'+(result.state==='review_recommended'?' escalated':'');
  $('count').textContent=result.evidence.length;$('sources').textContent=result.distinct_sources;$('latency').textContent=result.query_ms;
  $('reasons').replaceChildren(...result.reasons.map(r=>text('li',r)));
  $('evidence').replaceChildren(...result.evidence.map(r=>{const e=text('div','','record');e.append(text('b',r.signal==='rainfall'?`Rainfall · ${r.value} mm`:r.signal.charAt(0).toUpperCase()+r.signal.slice(1)),text('p',`${r.source_id} · observed ${stamp(r.observed_at)}\nReceived ${stamp(r.received_at)}`),text('span',r.synthetic?'SYNTHETIC FIXTURE':'USER-SUPPLIED · UNVERIFIED','synthetic'));return e;}));
  if(!result.evidence.length)$('evidence').append(text('p','No observations were available at this point.','subtle'));
  $('markers').replaceChildren(...result.evidence.slice(0,5).map((r,i)=>{const c=document.createElementNS('http://www.w3.org/2000/svg','circle');c.setAttribute('cx',String(65+i*66));c.setAttribute('cy',String([87,136,125,99,105][i]));c.setAttribute('r','7');c.setAttribute('fill',r.signal==='normal'?'#bd8734':'#34664b');c.setAttribute('stroke','#fff');c.setAttribute('stroke-width','3');return c;}));
  $('review-submit').disabled=!present||!result.evidence.length||busy;
  $('review-status').textContent=!present?'Return to present to save a review.':result.review_current?'Saved review matches the current evidence.':result.reviews.length?'Evidence or priority changed. A fresh review is needed.':'No review recorded for this evidence.';
  $('reviews').replaceChildren(...result.reviews.map(r=>{const e=text('div','','audit');e.append(text('b',labels[r.action]),text('p',r.note),text('span',stamp(r.reviewed_at)));return e;}));
 }catch(e){if(ticket===sequence)$('message').textContent=e.message;}
}
$('stream').onchange=refresh;
let timer;$('time').oninput=()=>{++sequence;$('review-submit').disabled=true;clearTimeout(timer);timer=setTimeout(refresh,90);};
$('live').onclick=()=>{anchor=Date.now();$('time').value='360';refresh();};
$('review-form').onsubmit=async e=>{e.preventDefault();if(busy||!snapshot||$('time').value!=='360')return;busy=true;$('review-submit').disabled=true;try{await api('/api/reviews',{stream_id:snapshot.stream_id,decision_hash:snapshot.decision_hash,action:$('action').value,note:$('review-note').value});$('review-note').value='';$('message').textContent='Review saved with its evidence snapshot.';}catch(err){$('message').textContent=err.message;}finally{busy=false;await refresh();}};
$('observation-form').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;try{await api('/api/observations',{source_id:$('source').value,external_id:crypto.randomUUID(),stream_id:$('stream').value,observed_at:new Date().toISOString(),lat:33.68,lon:-117.82,signal:$('signal').value,synthetic:true,note:'Synthetic observation added in the local demo.'});anchor=Date.now();$('time').value='360';$('message').textContent='Synthetic observation added. Review the updated evidence.';await refresh();}catch(err){$('message').textContent=err.message;}finally{button.disabled=false;}};
$('export').onclick=()=>{if(!snapshot)return;const blob=new Blob([JSON.stringify(snapshot,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='aquasentinel-evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
(async()=>{try{const {streams}=await api('/api/streams');$('stream').replaceChildren(...streams.map(s=>{const o=text('option',s);o.value=s;return o;}));if(!streams.length){$('message').textContent='No streams yet. Start the server with --demo to load synthetic observations.';return;}await refresh();}catch(e){$('message').textContent=e.message;}})();
