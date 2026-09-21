const $ = id => document.getElementById(id);
const labels = {monitor:'Monitor',needs_corroboration:'Needs corroboration',review_recommended:'Review recommended',dismissed:'Dismissed',follow_up_required:'Follow-up required'};
let map, mapLayer, geometry, lastStream;
let snapshot, sequence=0, busy=false;
let anchor=Date.now();
const text = (tag, value, className) => {const e=document.createElement(tag);e.textContent=value;if(className)e.className=className;return e;};
async function api(path, data){const r=await fetch(path,data?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)}:undefined);const v=await r.json();if(!r.ok)throw Error(v.error||'Request failed');return v;}
function stamp(value){return new Date(value).toISOString().slice(11,19)+' UTC';}
function renderEnvironment(context){
 const area=$('environment-content');area.replaceChildren();
 if(!context){area.append(text('p','No monitoring archive was available to this application at the selected replay time.','subtle'));return;}
 area.append(text('h3',context.station_name+' · '+context.stream_id),text('p','REAL USGS MEASUREMENTS · '+context.variable+' ('+context.unit+')','real-label'));
 area.append(text('p','Provider dates: '+context.records[0].measurement_date+' through '+context.records.at(-1).measurement_date+'. Daily summaries, not instantaneous sensor readings.','subtle'));
 const table=document.createElement('table');table.className='flow-table';
 const header=document.createElement('tr');['Provider date','Daily mean · '+context.unit,'Provider status','Source / type'].forEach(v=>header.append(text('th',v)));table.append(header);
 for(const record of context.records){const row=document.createElement('tr');[record.measurement_date,record.value===null?'Missing':String(record.value),record.approval_status||'Unknown','REAL · SENSOR'].forEach(v=>row.append(text('td',v)));table.append(row);}
 area.append(table,text('p',context.limitations,'subtle'),text('p','Downloaded '+context.retrieved_at+' · Imported '+context.imported_at+'. Initial publication time is unknown. Historical revisions are not live alerts.','subtle'));
 const details=document.createElement('details');details.append(text('summary','Source and provenance'));
 const link=text('a','Open original USGS daily data');link.href=context.provenance.files['daily.json'].requested_url;link.target='_blank';link.rel='noopener noreferrer';details.append(link);
 details.append(text('p','Credit: U.S. Geological Survey. Station '+context.lat+', '+context.lon+'. SHA-256: '+context.provenance.files['daily.json'].sha256,'subtle'));
 details.append(text('p','Provider revisions: '+[...new Set(context.records.map(r=>r.provider_last_modified||'unknown'))].join(', '),'subtle'));
 area.append(details);
}
async function refresh(){
 const ticket=++sequence;
 $('review-submit').disabled=true;
 try{
  const present=$('time').value==='360';
  const at=new Date(present?Date.now():anchor-(360-Number($('time').value))*60000).toISOString();
  const result=await api('/api/snapshot?stream='+encodeURIComponent($('stream').value)+'&as_of='+encodeURIComponent(at));
  if(ticket!==sequence)return;
  snapshot=result;
  if(window.L){
   if(!map){map=L.map('map').setView([34.22,-118.17],13);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:18,attribution:'© OpenStreetMap contributors · USGS NLDI'}).addTo(map);geometry=await api('/api/geometry');map.on('click',e=>{$('report-lat').value=e.latlng.lat.toFixed(6);$('report-lon').value=e.latlng.lng.toFixed(6);});}
   if(mapLayer)map.removeLayer(mapLayer);
   mapLayer=L.featureGroup().addTo(map);
   for(const feature of geometry.features.filter(f=>f.properties.stream_id===result.stream_id))L.geoJSON(feature,{style:{color:feature.properties.source_type==='real'?'#17888a':'#986725'}}).addTo(mapLayer);
   for(const r of result.evidence)L.circleMarker([r.lat,r.lon],{radius:6}).bindTooltip((r.synthetic?'SYNTHETIC':'REAL')+' '+r.signal).addTo(mapLayer);
   if(lastStream!==result.stream_id&&mapLayer.getBounds().isValid()){map.fitBounds(mapLayer.getBounds().pad(.1));lastStream=result.stream_id;const center=map.getCenter();$('report-lat').value=center.lat.toFixed(6);$('report-lon').value=center.lng.toFixed(6);}
   $('schematic').hidden=true;
  }else $('map').hidden=true;
  renderEnvironment(result.environmental_context);
  const weather=$('weather');weather.replaceChildren();
  if(result.forecast){weather.append(text('p',result.forecast.source_type.toUpperCase()+' · FORECAST · fetched '+result.forecast.fetched_at),text('p','Provider issue time: '+(result.forecast.issued_at||'not supplied')+' · '+(result.forecast.attribution||'Provider unknown')+'. Fetch time is receipt, not publication.','subtle'));}
  weather.append(text('p',result.watch?'WATCH: '+result.watch.rain_mm+' mm; window '+result.watch.window_start+'; lead '+result.watch.lead_hours+' hours. Illustrative runoff concern only.':'No active rainfall Watch. Missing, dry or expired forecast.'));
  for(const alert of result.alerts||[])weather.append(text('p','DRY RUN · '+alert.level.toUpperCase()+' · '+alert.status.toUpperCase()+' · '+alert.decision_hash.slice(0,12)));

  $('clock').textContent=(present?'Present · ':'Replay · ')+new Date(at).toISOString().replace('T',' ').slice(0,19)+' UTC';
  $('state').textContent=labels[result.display_state];
  $('state').className='badge'+(result.state==='review_recommended'?' escalated':'');
  $('count').textContent=result.evidence.length;$('sources').textContent=result.distinct_sources;$('latency').textContent=result.query_ms;
  $('reasons').replaceChildren(...result.reasons.map(r=>text('li',r)));
  $('evidence').replaceChildren(...result.evidence.map(r=>{const e=text('div','','record');e.append(text('b',r.signal==='rainfall'?`Rainfall · ${r.value} mm`:r.signal.charAt(0).toUpperCase()+r.signal.slice(1)),text('p',`${r.source_id} · observed ${stamp(r.observed_at)}\nReceived ${stamp(r.received_at)}`),text('span',(r.synthetic?'SYNTHETIC':'REAL · UNVERIFIED')+' · '+(r.signal==='rainfall'?'RAINFALL CONTEXT':'CITIZEN REPORT'),'synthetic'));return e;}));
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
$('observation-form').onsubmit=async e=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;try{const before=snapshot?.display_state;const reach=await api('/api/reach?lat='+encodeURIComponent($('report-lat').value)+'&lon='+encodeURIComponent($('report-lon').value));if(reach.stream_id!==$('stream').value)throw Error('Location must be within 200 m of the selected mapped reach.');await api('/api/observations',{source_id:$('source').value,external_id:crypto.randomUUID(),stream_id:$('stream').value,observed_at:new Date().toISOString(),lat:Number($('report-lat').value),lon:Number($('report-lon').value),signal:$('signal').value,synthetic:true,note:'Synthetic workflow report at current application time. Not a real report or historical USGS event.'});anchor=Date.now();$('time').value='360';await refresh();$('message').textContent='Your synthetic report changed the evidence: '+labels[before]+' → '+labels[snapshot.display_state]+'. A changed snapshot requires a new review.';}catch(err){$('message').textContent=err.message;}finally{button.disabled=false;}};
$('export').onclick=()=>{if(!snapshot)return;const blob=new Blob([JSON.stringify(snapshot,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='aquasentinel-evidence.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
(async()=>{try{const {streams}=await api('/api/streams');$('stream').replaceChildren(...streams.map(s=>{const o=text('option',s);o.value=s;return o;}));if(!streams.length){$('message').textContent='No streams yet. Start the server with --demo to load synthetic observations.';return;}await refresh();}catch(e){$('message').textContent=e.message;}})();

$('queue-alert').onclick=async()=>{try{await api('/api/alerts',{stream_id:$('stream').value});await refresh();}catch(e){$('message').textContent=e.message;}};

for(const [id,path] of [["brief-export","brief"],["fhir-export","fhir"]])$(id).onclick=()=>{if(snapshot)window.open("/api/"+path+"?stream="+encodeURIComponent(snapshot.stream_id)+"&as_of="+encodeURIComponent(snapshot.as_of),"_blank","noopener");};
