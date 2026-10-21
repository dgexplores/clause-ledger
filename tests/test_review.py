import io

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from clause_ledger.analysis import analyze
from clause_ledger.app import create_app
from clause_ledger.models import Policy
from clause_ledger.samples import SAMPLES


def test_rules_and_exact_evidence_ranges():
    for sample, expected in zip(SAMPLES, ((5, 0, 0), (1, 3, 1), (4, 1, 0))):
        report = analyze([sample["text"]], Policy())
        assert tuple(report["counts"][key] for key in ("clear", "attention", "missing")) == expected
        for finding in report["findings"]:
            for evidence in finding["evidence"]:
                assert sample["text"][evidence["start"]:evidence["end"]] == evidence["quote"]
    report = analyze([SAMPLES[2]["text"]], Policy())
    assert report["findings"][0]["ambiguous"]
    assert report["findings"][0]["value"] is None


def test_policy_snapshot_and_unsupported_phrasing():
    report = analyze(["We pay promptly, offer reliable service, and allow inspections."], Policy(require_audit=False))
    assert report["counts"]["missing"] == 4
    assert report["counts"]["not_required"] == 1
    assert report["policy"]["require_audit"] is False


def test_end_to_end_review_and_cross_session_isolation(tmp_path):
    application = create_app(tmp_path / "test.db")
    with TestClient(application) as first, TestClient(application) as second:
        for path in ("/", "/docs", "/openapi.json", "/healthz", "/static/style.css", "/static/app.js"):
            assert first.get(path).status_code == 200
        response = first.post("/api/documents", json={"title": "Sample", "text": SAMPLES[0]["text"]})
        assert response.status_code == 201
        document = response.json()
        identifier = document["id"]
        assert second.get("/api/documents").json() == []
        assert second.get(f"/api/documents/{identifier}").status_code == 404
        payload = {"decision": "approved", "reviewer": "Demo reviewer", "note": "Checked the five source quotes.", "expected_version": 1}
        assert second.post(f"/api/documents/{identifier}/review", json=payload).status_code == 404
        saved = first.post(f"/api/documents/{identifier}/review", json=payload)
        assert saved.status_code == 200
        assert saved.json()["status"] == "approved"
        assert saved.json()["version"] == 2
        assert len(saved.json()["events"]) == 1
        assert first.post(f"/api/documents/{identifier}/review", json=payload).status_code == 409
        assert second.delete(f"/api/documents/{identifier}").status_code == 404
        assert first.delete(f"/api/documents/{identifier}").status_code == 204
        assert first.get(f"/api/documents/{identifier}").status_code == 404


def test_missing_and_invalid_requests(tmp_path):
    with TestClient(create_app(tmp_path / "test.db")) as client:
        assert client.post("/api/documents", json={"title": " ", "text": " " * 40}).status_code == 422
        assert client.post("/api/documents", json={"title": "x", "text": "abc"}).status_code == 422
        assert client.post("/api/documents", json={"title": "x", "text": SAMPLES[0]["text"], "policy": {"min_uptime_percent": 150}}).status_code == 422
        assert client.post("/api/documents", json={"title": "x", "text": SAMPLES[0]["text"]}, headers={"Origin": "https://untrusted.example"}).status_code == 403
        assert client.post("/api/documents", content=b"x" * 1100001, headers={"Content-Type": "application/json"}).status_code == 413
        assert client.get("/").headers["content-security-policy"].startswith("default-src 'self'")
        assert "clause_session=" in client.get("/").request.headers["cookie"]


def test_pdf_limits_and_unreadable_uploads(tmp_path):
    with TestClient(create_app(tmp_path / "test.db")) as client:
        for data in (b"not a pdf", b"%PDF-broken"):
            assert client.post("/api/documents/pdf", data={"title": "test"}, files={"file": ("test.pdf", data, "application/pdf")}).status_code == 422
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        buffer = io.BytesIO()
        writer.write(buffer)
        assert client.post("/api/documents/pdf", data={"title": "blank"}, files={"file": ("blank.pdf", buffer.getvalue(), "application/pdf")}).status_code == 422
        assert client.post("/api/documents/pdf", data={"title": "huge"}, files={"file": ("big.pdf", b"%PDF-" + b"x" * 1048576, "application/pdf")}).status_code == 413


def test_storage_survives_app_restart(tmp_path):
    path = tmp_path / "test.db"
    with TestClient(create_app(path)) as first:
        result = first.post("/api/documents", json={"title": "persisted", "text": SAMPLES[0]["text"]}).json()
        cookies = dict(first.cookies)
    with TestClient(create_app(path)) as second:
        second.cookies.update(cookies)
        assert second.get("/api/documents/" + result["id"]).json()["title"] == "persisted"


def test_demo_session_quota(tmp_path):
    with TestClient(create_app(tmp_path / "test.db")) as client:
        for i in range(20):
            assert client.post("/api/documents", json={"title": str(i), "text": SAMPLES[0]["text"]}).status_code == 201
        assert client.post("/api/documents", json={"title": "overflow", "text": SAMPLES[0]["text"]}).status_code == 429


def text_pdf(pages):
    """Create a real searchable PDF fixture without an external generator."""
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    for text in pages:
        page = writer.add_blank_page(width=612, height=792)
        font = DictionaryObject({NameObject('/Type'): NameObject('/Font'), NameObject('/Subtype'): NameObject('/Type1'), NameObject('/BaseFont'): NameObject('/Helvetica')})
        page[NameObject('/Resources')] = DictionaryObject({NameObject('/Font'): DictionaryObject({NameObject('/F1'): writer._add_object(font)})})
        stream = DecodedStreamObject()
        commands = ['BT /F1 11 Tf 50 750 Td']
        for line in text.splitlines():
            escaped = line.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')
            commands.append(f'({escaped}) Tj 0 -16 Td')
        commands.append('ET')
        stream.set_data('\n'.join(commands).encode('latin-1'))
        page[NameObject('/Contents')] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_positive_pdf_upload_preserves_page_and_evidence(tmp_path):
    pages = ["Fictional supplier agreement.\nPayment terms: NET 45 days.\nUptime commitment: 99.9%.",
             "Breach notification: within 48 hours.\nThe customer may terminate on notice.\nThe customer may audit service records."]
    with TestClient(create_app(tmp_path / 'pdf.db')) as client:
        response = client.post('/api/documents/pdf', data={'title': 'Searchable two-page PDF'}, files={'file': ('supplier.pdf', text_pdf(pages), 'application/pdf')})
        assert response.status_code == 201, response.text
        document = response.json()
        assert len(document['pages']) == 2
        assert document['report']['counts']['clear'] == 5
        audit = next(item for item in document['report']['findings'] if item['key'] == 'audit')
        assert audit['evidence'][0]['page'] == 2
        for finding in document['report']['findings']:
            for evidence in finding['evidence']:
                assert document['pages'][evidence['page']-1][evidence['start']:evidence['end']] == evidence['quote']


def test_pdf_page_limit_and_encrypted_pdf(tmp_path):
    from pypdf import PdfReader
    raw = text_pdf(['Fictional supplier document with enough text to analyze.'] * 11)
    writer = PdfWriter()
    writer.append(PdfReader(io.BytesIO(text_pdf(['Fictional supplier agreement for encryption test.']))))
    writer.encrypt('fixture-password')
    output = io.BytesIO()
    writer.write(output)
    with TestClient(create_app(tmp_path / 'limits.db')) as client:
        for content in (raw, output.getvalue()):
            response = client.post('/api/documents/pdf', data={'title': 'Rejected PDF'}, files={'file': ('supplier.pdf', content, 'application/pdf')})
            assert response.status_code == 422


def test_concurrent_review_writers_cannot_overwrite_same_version(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    from clause_ledger.models import ReviewInput
    from clause_ledger.storage import Storage
    store = Storage(tmp_path / 'race.db')
    report = analyze([SAMPLES[0]['text']], Policy())
    document = store.create('owner', 'Concurrent review', [SAMPLES[0]['text']], report)
    payload = ReviewInput(decision='approved', reviewer='Reviewer', note='Reviewed the evidence.', expected_version=1)
    def attempt(_):
        try:
            store.review('owner', document['id'], payload)
            return 'saved'
        except ValueError:
            return 'stale'
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, range(2))) == ['saved', 'stale']
    assert len(store.get('owner', document['id'])['events']) == 1


def test_expired_records_cannot_be_read_or_reviewed(tmp_path):
    from datetime import datetime, timezone, timedelta
    from clause_ledger.models import ReviewInput
    from clause_ledger.storage import Storage
    store = Storage(tmp_path / 'expired.db')
    document = store.create('owner', 'Expired review', [SAMPLES[0]['text']], analyze([SAMPLES[0]['text']], Policy()))
    with store.connect() as connection:
        connection.execute('UPDATE documents SET created_at=? WHERE id=?', ((datetime.now(timezone.utc)-timedelta(hours=25)).isoformat(), document['id']))
    assert store.get('owner', document['id']) is None
    assert store.listing('owner') == []
    payload = ReviewInput(decision='approved', reviewer='Reviewer', note='An outdated review.', expected_version=1)
    try:
        store.review('owner', document['id'], payload)
    except KeyError:
        pass
    else:
        raise AssertionError('Expired records must not accept a decision')


def test_explicit_negation_is_never_marked_clear():
    report = analyze(['No customer may audit operational records.\nPayment terms: NET 30 days are not accepted.'], Policy())
    findings = {finding['key']: finding for finding in report['findings']}
    assert findings['audit']['state'] == 'attention'
    assert findings['payment_days']['state'] == 'attention'
    assert findings['audit']['negation_flag'] is True
