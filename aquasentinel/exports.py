"""Non-diagnostic One Health briefs and environmental FHIR R4 collections."""
from html import escape
from uuid import uuid5, NAMESPACE_URL
from .engine import digest


def brief(snapshot):
    s = snapshot
    state = s['display_state']
    status = 'Rainfall Watch' if s.get('watch') else state.replace('_', ' ')
    sections = {
        'City water ecologist': 'Check the reported reach, habitat and monitoring coverage; consider an authorized site assessment or sampling if warranted.',
        'Public-health officer': 'Review potential recreational contact pathways with local water staff; obtain verified environmental findings before considering any public advisory.',
        'Animal-health / parks staff': 'Check reported wildlife or habitat changes with qualified staff; document observations without inferring disease or a responsible polluter.'}
    urgency = ('Routine monitoring; no verified event is established.' if state in {'monitor','dismissed'} and not s.get('watch')
               else 'Human corroboration is needed before field action or public communication.')
    evidence = [f"{'SYNTHETIC' if r['synthetic'] else 'REAL / UNVERIFIED'} citizen/context: {r['signal']} at {r['observed_at']}; received {r['received_at']}" for r in s['evidence']]
    if s.get('environmental_context'):
        c=s['environmental_context']
        evidence += [f"REAL / SENSOR: daily discharge {r['value']} {r['unit']} on provider date {r['measurement_date']} (historical context)" for r in c['records']]
    if s.get('forecast'):
        evidence.append(f"{s['forecast']['source_type'].upper()} / FORECAST captured {s['forecast']['fetched_at']}; issue time unknown unless supplied")
    esc=lambda v: escape(str(v))
    return ('<!doctype html><html lang="en"><meta charset="utf-8"><title>One Health routing brief</title>'
        '<style>body{font:17px system-ui;max-width:850px;margin:40px auto;padding:20px;line-height:1.5}h2{margin-top:2em}code{overflow-wrap:anywhere}@media print{button{display:none}}</style>'
        '<h1>One Health routing brief</h1><p>Environmental evidence for human, animal and ecosystem follow-up.</p>'
        f'<p>Stream: {esc(s["stream_id"])} · As of {esc(s["as_of"])} · {esc(status)}</p><p>{esc(urgency)}</p>'
        + ''.join(f'<h2>{esc(a)}</h2><p>{esc(action)}</p>' for a,action in sections.items())
        + '<h2>Evidence and uncertainty</h2><ul>'+''.join(f'<li>{esc(e)}</li>' for e in evidence)+'</ul>'
        + '<p>Illustrative thresholds; source identities are unverified. Discharge is not water-quality truth. '
          'Rainfall Watch is not a diagnosis, disease prediction, confirmed hazard, or public advisory. '
          'No brief is automatically sent to these audiences.</p>'
        + f'<p>Snapshot: <code>{esc(s["decision_hash"])}</code>. Review current: {s["review_current"]}.</p></html>')


def fhir_bundle(s):
    entries=[]
    def add(resource, key):
        identity=str(uuid5(NAMESPACE_URL, 'https://github.com/Cyberchopin/aquasentinel/'+key))
        resource['id']=identity
        url='urn:uuid:'+identity
        entries.append({'fullUrl':url,'resource':resource})
        return url
    location=add({'resourceType':'Location','name':s['stream_id'], 'description':'Environmental stream; not a patient'},'stream/'+s['stream_id'])
    obs=[]
    for r in s['evidence']:
        resource={'resourceType':'Observation','status':'preliminary','code':{'text':'Citizen/context '+r['signal']},
            'subject':{'reference':location},'effectiveDateTime':r['observed_at'],
            'note':[{'text':('SYNTHETIC' if r['synthetic'] else 'REAL / UNVERIFIED')+'; received_at='+r['received_at']+'; '+r.get('note','')}]}
        if r['signal']=='rainfall': resource['valueQuantity']={'value':r['value'],'unit':'mm','system':'http://unitsofmeasure.org','code':'mm'}
        else: resource['valueString']=r['signal']+' (subjective citizen report, not sensor measurement)'
        obs.append(add(resource,'observation/'+r['id']))
    c=s.get('environmental_context')
    if c:
        for r in c['records']:
            resource={'resourceType':'Observation','status':'final' if r['approval_status']=='Approved' else 'preliminary',
                'code':{'text':'USGS daily mean discharge (00060; statistic 00003)'},'subject':{'reference':location},
                'effectiveDateTime':r['measurement_date'],
                'note':[{'text':'REAL / SENSOR daily aggregate; not water quality. Retrieved '+c['retrieved_at']+'; original publication unknown.'}]}
            if r['value'] is None: resource['dataAbsentReason']={'text':'Missing provider value'}
            else: resource['valueQuantity']={'value':r['value'],'unit':'ft^3/s','system':'http://unitsofmeasure.org','code':'[ft_i]3/s'}
            obs.append(add(resource,'sensor/'+c['dataset_id']+'/'+r['provider_id']))
    # Provenance targets a review-specific artifact, never current evidence for a stale review.
    for r in s['reviews']:
        review=add({'resourceType':'Basic','code':{'text':'Environmental review snapshot'},
            'identifier':[{'system':'https://github.com/Cyberchopin/aquasentinel/snapshot','value':r['decision_hash']}],
            'extension':[{'url':'https://github.com/Cyberchopin/aquasentinel/review-note','valueString':r['note']}]},'review/'+s['stream_id']+'/'+str(r['id']))
        add({'resourceType':'Provenance','target':[{'reference':review}], 'recorded':r['reviewed_at'],
            'activity':{'text':r['action']},'agent':[{'who':{'display':'Unauthenticated demo reviewer'}}]},'provenance/'+review)
    if s['review_current'] and s['display_state']=='follow_up_required':
        add({'resourceType':'Task','status':'requested','intent':'proposal','description':'Human environmental follow-up; not a clinical order',
             'focus':{'reference':location},'identifier':[{'value':s['decision_hash']}]},'task/'+s['decision_hash'])
    return {'resourceType':'Bundle','type':'collection','identifier':{'value':s['decision_hash']},'timestamp':s['as_of'],'entry':entries}
