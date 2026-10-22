import json
import httpx
import pytest
from fastapi.testclient import TestClient
from clause_ledger.semantic import analyze_semantic, ProviderError
from clause_ledger.models import Policy
from clause_ledger.app import create_app


def provider(monkeypatch, fields):
    monkeypatch.setenv('CLAUSE_LLM_API_KEY', 'test-only')
    monkeypatch.setenv('CLAUSE_LLM_MODEL', 'test-model')
    return httpx.MockTransport(lambda request: httpx.Response(200, json={'choices': [{'message': {'content': json.dumps({'fields': fields})}}]}))


def test_exact_quote_and_local_policy(monkeypatch):
    quote='Invoices shall be settled in 90 days.'
    fields=[{'key':'payment_days','value':90,'page':1,'quote':quote,'confidence':0.95}]
    result=analyze_semantic([quote],Policy(),provider(monkeypatch,fields))
    finding=result['findings'][0]
    assert finding['state']=='attention' and finding['evidence'][0]['start']==0
    assert result['requires_review'] and result['engine']=='provider-extraction.v1'


@pytest.mark.parametrize('change',[{'quote':'invented quote'},{'value':30},{'page':2},{'confidence':1.2},{'value':True}])
def test_rejects_hallucinated_or_invalid_evidence(monkeypatch,change):
    quote='Invoices shall be settled in 90 days.'
    field={'key':'payment_days','value':90,'page':1,'quote':quote,'confidence':0.95,**change}
    with pytest.raises(ProviderError):
        analyze_semantic([quote],Policy(),provider(monkeypatch,[field]))


def test_negation_and_confidence_never_auto_clear(monkeypatch):
    quote='Customer may not audit the supplier.'
    fields=[{'key':'audit','value':True,'page':1,'quote':quote,'confidence':0.99}]
    result=analyze_semantic([quote],Policy(),provider(monkeypatch,fields))
    assert result['findings'][-1]['state']=='attention'


def test_unconfigured_semantic_does_not_save(monkeypatch,tmp_path):
    monkeypatch.delenv('CLAUSE_LLM_API_KEY',raising=False)
    with TestClient(create_app(tmp_path/'review.db')) as client:
        response=client.post('/api/documents',json={'title':'Contract','text':'A fictional contract with sufficient text.','engine':'semantic'})
        assert response.status_code==503
        assert client.get('/api/documents').json()==[]


def test_provider_failure_redacts_body(monkeypatch):
    provider(monkeypatch,[])
    transport=httpx.MockTransport(lambda request:httpx.Response(401,text='secret-key-should-not-leak'))
    with pytest.raises(ProviderError) as error:
        analyze_semantic(['source'],Policy(),transport)
    assert 'secret-key' not in str(error.value)


def test_operator_token_blocks_provider_before_call(monkeypatch,tmp_path):
    import clause_ledger.app as module
    monkeypatch.setenv('CLAUSE_LLM_API_KEY','test-key')
    monkeypatch.setenv('CLAUSE_LLM_MODEL','test-model')
    monkeypatch.setenv('CLAUSE_LLM_ACCESS_TOKEN','operator-secret')
    calls=[]
    monkeypatch.setattr(module,'analyze_semantic',lambda *args:calls.append(args))
    with TestClient(create_app(tmp_path/'review.db')) as client:
        payload={'title':'Contract','text':'A fictional contract with sufficient text.','engine':'semantic'}
        assert client.post('/api/documents',json=payload).status_code==403
        assert client.post('/api/documents',json=payload,headers={'X-AI-Token':'wrong'}).status_code==403
        assert not calls


def test_model_cannot_silently_resolve_known_conflict(monkeypatch):
    quote='Payment terms: 30 days'
    pages=[quote+'\nPayment terms: 90 days']
    fields=[{'key':'payment_days','value':30,'page':1,'quote':quote,'confidence':0.99}]
    finding=analyze_semantic(pages,Policy(),provider(monkeypatch,fields))['findings'][0]
    assert finding['state']=='attention' and finding['ambiguous']


def test_context_negation_is_not_hidden_by_truncated_quote(monkeypatch):
    quote='Customer may audit'
    fields=[{'key':'audit','value':True,'page':1,'quote':quote,'confidence':0.99}]
    finding=analyze_semantic([quote+' but not without separate permission.'],Policy(),provider(monkeypatch,fields))['findings'][-1]
    assert finding['state']=='attention'


def test_authorized_provider_report_persists_and_keeps_review_boundary(monkeypatch,tmp_path):
    import clause_ledger.app as module
    quote='Payment terms: 30 days. Supplier agreement.'
    fields=[{'key':'payment_days','value':30,'page':1,'quote':quote,'confidence':0.9}]
    report=analyze_semantic([quote],Policy(),provider(monkeypatch,fields))
    monkeypatch.setenv('CLAUSE_LLM_ACCESS_TOKEN','operator-secret')
    monkeypatch.setattr(module,'analyze_semantic',lambda *args:report)
    with TestClient(create_app(tmp_path/'review.db')) as client:
        response=client.post('/api/documents',json={'title':'Contract','text':quote,'engine':'semantic'},headers={'X-AI-Token':'operator-secret'})
        assert response.status_code==201
        assert response.json()['report']['requires_review']
        assert response.json()['report']['engine']=='provider-extraction.v1'
