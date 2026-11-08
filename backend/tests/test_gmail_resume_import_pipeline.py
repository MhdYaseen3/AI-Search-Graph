import io
import hashlib
import re
import zipfile
from types import SimpleNamespace

import fitz
import pytest
from fastapi.testclient import TestClient
from google.oauth2.credentials import Credentials

from app.api.deps import get_gmail_message_tracking_service, get_resume_ingest_service
from app.api.v1.endpoints.gmail import get_gmail_service
from app.core.exceptions import ValidationError
from app.main import app
from app.models import Candidate, Education, Experience, Project, Skill, Technology
from app.schemas.candidate import CandidateCreate
from app.services.candidate_management import CandidateManagementService
from app.services.candidate_graph import CandidateGraphService
from app.services.gmail_message_tracking import GmailMessageTrackingService
from app.services.neo4j_graph import Neo4jGraphService
from app.services.pdf_extraction import PDFExtractionService
from app.services.resume_ingest import ResumeIngestService
from app.services.resume_upload import ResumeUploadService
from app.services.query_parser import QueryParser
from app.services.search import SearchService


def make_pdf(text: str) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_textbox(fitz.Rect(50, 50, 550, 780), text)
    content = document.tobytes()
    document.close()
    return content


def make_docx(text: str) -> bytes:
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(
            f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>"
            for line in text.splitlines()
        )
        + "</w:body></w:document>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("word/document.xml", xml)
    return output.getvalue()


class FakeGmailService:
    def __init__(self, content: bytes):
        self.content = content
        self.downloaded = []
        self.fail_next_download = False

    def get_credentials(self, state):
        return Credentials(token="test-token")

    def download_attachment(self, credentials, message_id, attachment_id):
        self.downloaded.append((message_id, attachment_id))
        if self.fail_next_download:
            self.fail_next_download = False
            raise RuntimeError("temporary Gmail download failure")
        return self.content

    def compute_file_hash(self, content):
        return hashlib.sha256(content).hexdigest()


class FakeNeo4jResult:
    def __init__(self, data=None):
        self._data = data or []

    async def consume(self):
        return None

    async def data(self):
        return self._data


class FakeNeo4jTransaction:
    def __init__(self, database):
        self.database = database

    async def run(self, query, parameters=None):
        parameters = parameters or {}
        returned_records = []
        self.database.statements.append((query, parameters))
        node_match = re.search(
            r"MERGE \(n:(\w+) \{(\w+): \$(\w+)\}\)",
            query,
        )
        if node_match:
            label, unique_property, parameter_name = node_match.groups()
            candidate = {
                **parameters["properties"],
                unique_property: parameters[parameter_name],
                "created_at": parameters["created_at"],
                "updated_at": parameters["updated_at"],
            }
            self.database.nodes.setdefault(label, {})[
                candidate[unique_property]
            ] = candidate
            if label == "Candidate":
                self.database.candidates[candidate["id"]] = candidate
        relationship_match = re.search(
            r"MERGE \(c\)-\[:(\w+)\]->\((\w+)\)",
            query,
        )
        if relationship_match:
            relationship, target_alias = relationship_match.groups()
            target_match = re.search(
                rf"MATCH \({target_alias}:(\w+) \{{(\w+): \$(\w+)\}}\)",
                query,
            )
            if target_match:
                label, property_name, parameter_name = target_match.groups()
                self.database.links.add(
                    (
                        parameters["candidate_id"],
                        relationship,
                        label,
                        property_name,
                        parameters[parameter_name],
                    )
                )
        if "MERGE (a:GmailAttachment" in query:
            key = (parameters["message_id"], parameters["attachment_id"])
            self.database.attachments.add(key)
            is_new = key not in self.database.attachment_metadata
            record = self.database.attachment_metadata.setdefault(
                key,
                {
                    "message_id": key[0],
                    "attachment_id": key[1],
                    "status": "PENDING",
                },
            )
            record.update(parameters)
            for status in ("PENDING", "PROCESSING", "SUCCESS", "FAILED", "DUPLICATE"):
                if f"a.status = '{status}'" in query and (
                    status != "PENDING" or is_new
                ):
                    record["status"] = status
            if "a.failure_reason = $reason" in query:
                record["failure_reason"] = parameters.get("reason")
            if "a.sha256 = coalesce($sha256, a.sha256)" in query:
                record["sha256"] = parameters.get("sha256") or record.get("sha256")
            if record.get("status") == "SUCCESS" and record.get("sha256"):
                self.database.hashes[record["sha256"]] = {
                    "status": "SUCCESS",
                    "candidate_id": record.get("candidate_id"),
                    "message_id": key[0],
                    "attachment_id": key[1],
                }
        if "MATCH (a:GmailAttachment" in query:
            key = (parameters["message_id"], parameters["attachment_id"])
            record = self.database.attachment_metadata.get(key)
            if record:
                record.update(parameters)
                for status in ("PENDING", "PROCESSING", "SUCCESS", "FAILED", "DUPLICATE"):
                    if f"a.status = '{status}'" in query:
                        record["status"] = status
                if "a.updated_at = $now" in query and parameters.get("now"):
                    record["updated_at"] = parameters["now"]
                if "a.attempted_at = $now" in query and parameters.get("now"):
                    record["updated_at"] = parameters["now"]
                if "a.failure_reason = $reason" in query:
                    record["failure_reason"] = parameters.get("reason")
                if "a.sha256 = coalesce($sha256, a.sha256)" in query:
                    record["sha256"] = parameters.get("sha256") or record.get("sha256")
                if "a.sha256 = $sha256" in query and parameters.get("sha256"):
                    record["sha256"] = parameters["sha256"]
        if "MERGE (h:GmailAttachmentHash" in query:
            sha256 = parameters["sha256"]
            self.database.hashes.setdefault(
                sha256,
                {"sha256": sha256, "status": "PENDING"},
            )
        if "MATCH (h:GmailAttachmentHash" in query:
            sha256 = parameters["sha256"]
            record = self.database.hashes.get(sha256)
            if record and (
                "WHERE h.message_id = $message_id" not in query
                or (
                    record.get("message_id") == parameters.get("message_id")
                    and record.get("attachment_id") == parameters.get("attachment_id")
                )
            ):
                for status in ("PROCESSING", "SUCCESS", "FAILED"):
                    if f"h.status = '{status}'" in query:
                        record["status"] = status
                record.update(parameters)
                if "h.updated_at = $now" in query and parameters.get("now"):
                    record["updated_at"] = parameters["now"]
        if "RETURN properties(a) AS record" in query:
            key = (parameters["message_id"], parameters["attachment_id"])
            record = self.database.attachment_metadata.get(key)
            if record:
                returned_records = [{"record": dict(record)}]
        elif "RETURN properties(h) AS record" in query:
            record = self.database.hashes.get(parameters["sha256"])
            if record:
                returned_records = [{"record": dict(record)}]
        return FakeNeo4jResult(returned_records)


class FakeNeo4jDatabase:
    def __init__(self):
        self.candidates = {}
        self.attachments = set()
        self.attachment_metadata = {}
        self.statements = []
        self.transaction_count = 0
        self.nodes = {}
        self.links = set()
        self.hashes = {}

    async def execute_read(self, query, parameters=None):
        parameters = parameters or {}
        email = parameters.get("email")
        if email:
            matches = [
                {"c": candidate}
                for candidate in self.candidates.values()
                if candidate.get("email", "").strip().casefold() == email
                and (
                    not parameters.get("full_name")
                    or " ".join(candidate.get("full_name", "").casefold().split())
                    == parameters["full_name"]
                )
            ]
            return matches[:1]
        if "OPTIONAL MATCH (c)-[r]->(n)" in query:
            candidate = self.candidates.get(parameters["candidate_id"])
            if not candidate:
                return []
            related = []
            for candidate_id, relationship, label, property_name, value in self.links:
                if candidate_id != parameters["candidate_id"]:
                    continue
                node = self.nodes[label].get(value)
                if node:
                    related.append(
                        {
                            "relationship": relationship,
                            "labels": [label],
                            "properties": node,
                        }
                    )
            return [{
                "candidate_id": candidate["id"],
                "candidate_name": candidate["full_name"],
                "related": related,
            }]
        if "OPTIONAL MATCH (c)-[:HAS_SKILL]" in query:
            candidate = next(iter(self.candidates.values()), None)
            if not candidate:
                return []

            def related_names(relationship, label):
                return [
                    self.nodes[label][value].get("name")
                    for candidate_id, rel, node_label, _, value in self.links
                    if candidate_id == candidate["id"]
                    and rel == relationship
                    and node_label == label
                    and value in self.nodes.get(label, {})
                ]

            skills = related_names("HAS_SKILL", "Skill")
            technologies = related_names("USES_TECHNOLOGY", "Technology")
            projects = related_names("WORKED_ON", "Project")
            education = [
                self.nodes["Education"][value].get("institution")
                for candidate_id, rel, label, _, value in self.links
                if candidate_id == candidate["id"]
                and rel == "STUDIED_AT"
                and label == "Education"
                and value in self.nodes.get("Education", {})
            ]
            matched_skills = [
                requested for requested in parameters["skills"]
                if requested.casefold() in {item.casefold() for item in skills}
            ]
            matched_technologies = [
                requested for requested in parameters["technologies"]
                if requested.casefold() in {
                    item.casefold() for item in technologies
                }
            ]
            if parameters["skills"] and not matched_skills:
                return []
            if parameters["technologies"] and not matched_technologies:
                return []
            return [{
                "candidate_id": candidate["id"],
                "full_name": candidate["full_name"],
                "summary": candidate.get("summary"),
                "skills": skills,
                "technologies": technologies,
                "projects": projects,
                "education": education,
                "roles": [],
                "experiences": [],
                "matched_skills": matched_skills,
                "matched_technologies": matched_technologies,
                "matched_projects": [],
                "matched_roles": [],
                "matched_education": [],
            }]
        return []

    async def execute_write_transaction(self, work):
        self.transaction_count += 1
        return await work(FakeNeo4jTransaction(self))


class FakeTrackingService:
    def __init__(self, database):
        self.database = database

    async def claim_attachment(self, message_id, attachment_id, filename):
        key = (message_id, attachment_id)
        record = self.database.attachment_metadata.get(key)
        if record and record.get("status") in {"SUCCESS", "DUPLICATE", "PROCESSING"}:
            return {"claimed": False, **record}
        record = {
            "message_id": message_id,
            "attachment_id": attachment_id,
            "filename": filename,
            "status": "PROCESSING",
            "source": "gmail",
        }
        self.database.attachments.add(key)
        self.database.attachment_metadata[key] = record
        return {"claimed": True, **record}

    async def set_attachment_hash(self, message_id, attachment_id, sha256):
        self.database.attachment_metadata[
            (message_id, attachment_id)
        ]["sha256"] = sha256

    async def claim_hash(self, message_id, attachment_id, sha256):
        record = self.database.hashes.get(sha256)
        if record and record.get("status") == "SUCCESS":
            return {
                "claimed": False,
                "duplicate": True,
                "candidate_id": record.get("candidate_id"),
            }
        if record and record.get("status") == "PROCESSING":
            same_owner = (
                record.get("message_id") == message_id
                and record.get("attachment_id") == attachment_id
            )
            if not same_owner:
                return {"claimed": False, "duplicate": False, "busy": True}
        self.database.hashes[sha256] = {
            "status": "PROCESSING",
            "message_id": message_id,
            "attachment_id": attachment_id,
        }
        return {"claimed": True, "duplicate": False, "busy": False}

    async def mark_duplicate(self, message_id, attachment_id, sha256, candidate_id):
        self.database.attachment_metadata[
            (message_id, attachment_id)
        ].update(
            status="DUPLICATE",
            sha256=sha256,
            candidate_id=candidate_id,
        )

    async def mark_pending(self, message_id, attachment_id, reason):
        self.database.attachment_metadata[
            (message_id, attachment_id)
        ].update(status="PENDING", failure_reason=reason)

    async def mark_failed(self, message_id, attachment_id, reason, sha256=None):
        self.database.attachment_metadata[
            (message_id, attachment_id)
        ].update(
            status="FAILED",
            failure_reason=reason,
            sha256=sha256,
        )
        if sha256:
            self.database.hashes[sha256] = {
                "status": "FAILED",
                "message_id": message_id,
                "attachment_id": attachment_id,
            }

    async def list_import_history(self, limit):
        return [
            {"import": item, "candidate_id": item.get("candidate_id")}
            for item in list(self.database.attachment_metadata.values())[:limit]
        ]

    async def get_attachment_import(self, message_id, attachment_id):
        return self.database.attachment_metadata.get((message_id, attachment_id))


def make_ingest_service(upload_dir, database):
    class ExtractionService:
        async def extract_skills(self, text):
            return [Skill(name="Python")]

        async def extract_projects(self, text):
            return [Project(name="GraphCV portfolio")]

        async def extract_technologies(self, text):
            return ["FastAPI"]

    graph_service = Neo4jGraphService(database)
    pdf_service = PDFExtractionService()
    return ResumeIngestService(
        upload_service=ResumeUploadService(
            upload_dir=upload_dir,
            pdf_extractor=pdf_service,
        ),
        pdf_service=pdf_service,
        candidate_service=CandidateManagementService(database),
        graph_service=graph_service,
        skill_service=ExtractionService(),
        project_service=ExtractionService(),
        education_service=SimpleNamespace(),
        technology_service=ExtractionService(),
    )


@pytest.mark.parametrize(
    ("filename", "mime_type", "content"),
    [
        (
            "jordan-lee.pdf",
            "application/pdf",
            make_pdf(
                "Jordan Lee\njordan.lee@example.com\n"
                "Software Engineer\nExperience 2020 - Present"
            ),
        ),
        (
            "jordan-lee.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            make_docx(
                "Jordan Lee\njordan.lee@example.com\n"
                "Software Engineer\nExperience 2020 - Present"
            ),
        ),
    ],
)
@pytest.mark.asyncio
async def test_selected_gmail_resume_runs_through_shared_ingest_pipeline(
    tmp_path, filename, mime_type, content
):
    database = FakeNeo4jDatabase()
    gmail_service = FakeGmailService(content)
    tracking_service = FakeTrackingService(database)
    ingest_service = make_ingest_service(tmp_path, database)
    app.dependency_overrides[get_gmail_service] = lambda: gmail_service
    app.dependency_overrides[get_gmail_message_tracking_service] = (
        lambda: tracking_service
    )
    app.dependency_overrides[get_resume_ingest_service] = lambda: ingest_service
    try:
        response = TestClient(app).post(
            "/api/v1/gmail/import",
            params={"state": "test-state"},
            json={
                "attachments": [
                    {
                        "message_id": "gmail-message-1",
                        "attachment_id": "gmail-attachment-1",
                        "filename": filename,
                        "size": len(content),
                        "mime_type": mime_type,
                        "subject": "Application",
                        "sender": "sender@example.com",
                        "date": "2026-01-01",
                        "classification": "RESUME",
                    }
                ]
            },
        )
    finally:
        app.dependency_overrides.pop(get_gmail_service, None)
        app.dependency_overrides.pop(get_gmail_message_tracking_service, None)
        app.dependency_overrides.pop(get_resume_ingest_service, None)

    assert response.status_code == 200
    data = response.json()
    assert data["success_count"] == 1
    assert data["failure_count"] == 0
    candidate_id = data["imported_candidates"][0]
    assert data["results"][0]["message_id"] == "gmail-message-1"
    assert data["results"][0]["attachment_id"] == "gmail-attachment-1"
    assert data["results"][0]["candidate_id"] == candidate_id
    assert gmail_service.downloaded == [
        ("gmail-message-1", "gmail-attachment-1")
    ]
    assert len(database.candidates) == 1
    candidate = database.candidates[candidate_id]
    assert candidate["full_name"] == "Jordan Lee"
    assert candidate["source"] == "gmail"
    assert database.attachment_metadata[
        ("gmail-message-1", "gmail-attachment-1")
    ]["candidate_id"] == candidate_id
    tracking_query = next(
        query
        for query, _ in database.statements
        if "MERGE (a:GmailAttachment" in query
    )
    assert "a.source = 'gmail'" in tracking_query
    assert database.transaction_count == 1
    queries = [query for query, _ in database.statements]
    assert any("HAS_SKILL" in query for query in queries)
    assert any("WORKED_ON" in query for query in queries)
    assert any("USES_TECHNOLOGY" in query for query in queries)

    app.dependency_overrides[get_gmail_service] = lambda: gmail_service
    app.dependency_overrides[get_gmail_message_tracking_service] = (
        lambda: tracking_service
    )
    app.dependency_overrides[get_resume_ingest_service] = lambda: ingest_service
    try:
        second_import = TestClient(app).post(
            "/api/v1/gmail/import",
            params={"state": "test-state"},
            json={
                "attachments": [
                    {
                        "message_id": "gmail-message-1",
                        "attachment_id": "gmail-attachment-2",
                        "filename": filename,
                        "size": len(content),
                        "mime_type": mime_type,
                        "subject": "Application",
                        "sender": "sender@example.com",
                        "date": "2026-01-02",
                        "classification": "RESUME",
                    }
                ]
            },
        )
    finally:
        app.dependency_overrides.pop(get_gmail_service, None)
        app.dependency_overrides.pop(get_gmail_message_tracking_service, None)
        app.dependency_overrides.pop(get_resume_ingest_service, None)
    assert second_import.status_code == 200
    assert second_import.json()["success_count"] == 0
    assert second_import.json()["results"][0]["status"] == "DUPLICATE"
    assert second_import.json()["results"][0]["candidate_id"] == candidate_id
    assert len(database.candidates) == 1
    assert len(gmail_service.downloaded) == 2

    query = QueryParser().parse("Find Python developers")
    search_results = await SearchService(database).search(query)
    assert [item["candidate_id"] for item in search_results] == [candidate_id]

    graph = await CandidateGraphService(database).get_candidate_graph(candidate_id)
    assert {link.type for link in graph.links} >= {
        "HAS_SKILL",
        "WORKED_ON",
        "USES_TECHNOLOGY",
    }


def test_failed_gmail_import_can_be_retried_without_duplicate_candidate(tmp_path):
    database = FakeNeo4jDatabase()
    content = make_pdf(
        "Jordan Lee\njordan.lee@example.com\n"
        "Software Engineer\nExperience 2020 - Present"
    )
    gmail_service = FakeGmailService(content)
    gmail_service.fail_next_download = True
    tracking_service = FakeTrackingService(database)
    ingest_service = make_ingest_service(tmp_path, database)
    app.dependency_overrides[get_gmail_service] = lambda: gmail_service
    app.dependency_overrides[get_gmail_message_tracking_service] = (
        lambda: tracking_service
    )
    app.dependency_overrides[get_resume_ingest_service] = lambda: ingest_service
    payload = {
        "attachments": [
            {
                "message_id": "retry-message",
                "attachment_id": "retry-attachment",
                "filename": "jordan-lee.pdf",
                "size": len(content),
                "mime_type": "application/pdf",
                "subject": "Application",
                "sender": "sender@example.com",
                "date": "2026-01-01",
                "classification": "RESUME",
            }
        ]
    }
    try:
        first = TestClient(app).post(
            "/api/v1/gmail/import",
            params={"state": "test-state"},
            json=payload,
        )
        assert first.status_code == 200
        assert first.json()["failure_count"] == 1
        assert first.json()["results"][0]["status"] == "FAILED"
        failed_record = database.attachment_metadata[
            ("retry-message", "retry-attachment")
        ]
        assert failed_record["failure_reason"] == (
            "Unable to download or process this attachment."
        )
        assert database.candidates == {}

        retried = TestClient(app).post(
            "/api/v1/gmail/import/retry",
            params={"state": "test-state"},
            json={
                "message_id": "retry-message",
                "attachment_id": "retry-attachment",
            },
        )
    finally:
        app.dependency_overrides.pop(get_gmail_service, None)
        app.dependency_overrides.pop(get_gmail_message_tracking_service, None)
        app.dependency_overrides.pop(get_resume_ingest_service, None)

    assert retried.status_code == 200
    assert retried.json()["success_count"] == 1
    assert retried.json()["results"][0]["status"] == "SUCCESS"
    assert len(database.candidates) == 1
    assert database.attachment_metadata[
        ("retry-message", "retry-attachment")
    ]["status"] == "SUCCESS"


def test_gmail_import_history_returns_minimal_safe_metadata():
    database = FakeNeo4jDatabase()
    database.attachment_metadata[("history-message", "history-attachment")] = {
        "message_id": "history-message",
        "attachment_id": "history-attachment",
        "filename": "resume.pdf",
        "sha256": "a" * 64,
        "status": "FAILED",
        "imported_at": "2026-11-08T10:00:00+00:00",
        "failure_reason": "Gmail API request failed.",
        "email_body": "must not appear",
        "oauth_token": "must not appear",
    }
    tracking_service = FakeTrackingService(database)
    app.dependency_overrides[get_gmail_message_tracking_service] = (
        lambda: tracking_service
    )
    try:
        response = TestClient(app).get("/api/v1/gmail/import-history")
    finally:
        app.dependency_overrides.pop(get_gmail_message_tracking_service, None)

    assert response.status_code == 200
    assert response.json()[0]["status"] == "FAILED"
    assert response.json()[0]["sha256"] == "a" * 64
    assert "email_body" not in response.json()[0]
    assert "oauth_token" not in response.json()[0]


@pytest.mark.asyncio
async def test_gmail_candidate_matching_requires_email_and_same_name():
    database = FakeNeo4jDatabase()
    service = CandidateManagementService(database)

    async def create(name, attachment_id, sha256):
        return await service.create_gmail_candidate(
            CandidateCreate(
                full_name=name,
                email="shared@example.com",
                source="gmail",
            ),
            [],
            [],
            [],
            [],
            [],
            message_id="candidate-match-message",
            attachment_id=attachment_id,
            filename="resume.pdf",
            sha256=sha256,
        )

    first = await create("Alex Rivera", "attachment-1", "1" * 64)
    other_person = await create("Taylor Rivera", "attachment-2", "2" * 64)
    same_person = await create("  ALEX   RIVERA  ", "attachment-3", "3" * 64)

    assert first.id != other_person.id
    assert first.id == same_person.id
    assert len(database.candidates) == 2


@pytest.mark.asyncio
async def test_tracking_service_claims_failed_retry_and_content_hash_atomically():
    database = FakeNeo4jDatabase()
    tracking = GmailMessageTrackingService(database)

    first_claim = await tracking.claim_attachment(
        "message-1",
        "attachment-1",
        "resume.pdf",
    )
    duplicate_request = await tracking.claim_attachment(
        "message-1",
        "attachment-1",
        "resume.pdf",
    )
    assert first_claim["claimed"] is True
    assert database.attachment_metadata[
        ("message-1", "attachment-1")
    ].get("updated_at"), database.statements
    assert duplicate_request["claimed"] is False
    assert duplicate_request["status"] == "PROCESSING"

    await tracking.mark_failed(
        "message-1",
        "attachment-1",
        "Gmail API request failed.",
    )
    retry_claim = await tracking.claim_attachment(
        "message-1",
        "attachment-1",
        "resume.pdf",
    )
    assert retry_claim["claimed"] is True
    assert retry_claim["status"] == "PROCESSING"

    first_hash_claim = await tracking.claim_hash(
        "message-1",
        "attachment-1",
        "f" * 64,
    )
    concurrent_hash_claim = await tracking.claim_hash(
        "message-2",
        "attachment-2",
        "f" * 64,
    )
    assert first_hash_claim["claimed"] is True
    assert concurrent_hash_claim["busy"] is True

    database.hashes["f" * 64].update(
        status="SUCCESS",
        candidate_id="candidate-1",
    )
    duplicate_hash_claim = await tracking.claim_hash(
        "message-3",
        "attachment-3",
        "f" * 64,
    )
    assert duplicate_hash_claim["duplicate"] is True
    assert duplicate_hash_claim["candidate_id"] == "candidate-1"


@pytest.mark.parametrize(
    ("filename", "mime_type", "content"),
    [
        ("empty.pdf", "application/pdf", b""),
        ("blank.pdf", "application/pdf", make_pdf("")),
        ("invalid.pdf", "application/pdf", b"not a pdf"),
        ("invalid.docx", "application/octet-stream", b"not a docx"),
        (
            "empty.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            make_docx(""),
        ),
        ("legacy.doc", "application/msword", b"unsupported"),
    ],
)
def test_gmail_import_reports_invalid_documents_without_candidate_creation(
    tmp_path, filename, mime_type, content
):
    database = FakeNeo4jDatabase()
    gmail_service = FakeGmailService(content)
    tracking_service = FakeTrackingService(database)
    ingest_service = make_ingest_service(tmp_path, database)
    app.dependency_overrides[get_gmail_service] = lambda: gmail_service
    app.dependency_overrides[get_gmail_message_tracking_service] = (
        lambda: tracking_service
    )
    app.dependency_overrides[get_resume_ingest_service] = lambda: ingest_service
    try:
        response = TestClient(app).post(
            "/api/v1/gmail/import",
            params={"state": "test-state"},
            json={
                "attachments": [
                    {
                        "message_id": "gmail-message-invalid",
                        "attachment_id": "gmail-attachment-invalid",
                        "filename": filename,
                        "size": len(content),
                        "mime_type": mime_type,
                        "subject": "Application",
                        "sender": "sender@example.com",
                        "date": "2026-01-01",
                        "classification": "RESUME",
                    }
                ]
            },
        )
    finally:
        app.dependency_overrides.pop(get_gmail_service, None)
        app.dependency_overrides.pop(get_gmail_message_tracking_service, None)
        app.dependency_overrides.pop(get_resume_ingest_service, None)

    assert response.status_code == 200
    assert response.json()["failure_count"] == 1
    assert response.json()["results"][0]["success"] is False
    assert response.json()["results"][0]["error"]
    assert database.candidates == {}


def test_non_resume_is_rejected_before_gmail_download(tmp_path):
    database = FakeNeo4jDatabase()
    gmail_service = FakeGmailService(b"unused")
    tracking_service = FakeTrackingService(database)
    ingest_service = make_ingest_service(tmp_path, database)
    app.dependency_overrides[get_gmail_service] = lambda: gmail_service
    app.dependency_overrides[get_gmail_message_tracking_service] = (
        lambda: tracking_service
    )
    app.dependency_overrides[get_resume_ingest_service] = lambda: ingest_service
    try:
        response = TestClient(app).post(
            "/api/v1/gmail/import",
            params={"state": "test-state"},
            json={
                "attachments": [
                    {
                        "message_id": "gmail-message-1",
                        "attachment_id": "gmail-attachment-1",
                        "filename": "scholarship.pdf",
                        "size": 20,
                        "mime_type": "application/pdf",
                        "subject": "Scholarship",
                        "sender": "sender@example.com",
                        "date": "2026-01-01",
                        "classification": "NON_RESUME",
                    }
                ]
            },
        )
    finally:
        app.dependency_overrides.pop(get_gmail_service, None)
        app.dependency_overrides.pop(get_gmail_message_tracking_service, None)
        app.dependency_overrides.pop(get_resume_ingest_service, None)

    assert response.status_code == 200
    assert response.json()["failure_count"] == 1
    assert gmail_service.downloaded == []


@pytest.mark.asyncio
async def test_resume_graph_writer_merges_all_existing_relationship_types():
    database = FakeNeo4jDatabase()
    graph_service = Neo4jGraphService(database)
    candidate = Candidate(
        id="gmail-candidate",
        full_name="Jordan Lee",
        source="gmail",
    )

    await graph_service.persist_resume_graph(
        candidate,
        [Skill(name="Python")],
        [Project(name="GraphCV portfolio")],
        [Education(institution="Example University", degree="BSc")],
        [Experience(company="Example Corp", role="Engineer")],
        [Technology(name="FastAPI")],
        gmail_message_id="message",
        gmail_attachment_id="attachment",
        filename="resume.pdf",
        sha256="test-sha256",
    )

    relationship_queries = {
        relationship
        for query, _ in database.statements
        for relationship in (
            "HAS_SKILL",
            "WORKED_ON",
            "STUDIED_AT",
            "WORKED_AT",
            "USES_TECHNOLOGY",
        )
        if f"MERGE (c)-[:{relationship}]" in query
    }
    assert relationship_queries == {
        "HAS_SKILL",
        "WORKED_ON",
        "STUDIED_AT",
        "WORKED_AT",
        "USES_TECHNOLOGY",
    }
    assert database.transaction_count == 1
    assert database.attachment_metadata[
        ("message", "attachment")
    ]["candidate_id"] == "gmail-candidate"


@pytest.mark.asyncio
async def test_gmail_upload_enforces_configured_file_size(tmp_path, monkeypatch):
    from fastapi import UploadFile
    from starlette.datastructures import Headers

    content = make_pdf("Jordan Lee")
    monkeypatch.setattr(
        "app.services.resume_upload.settings.max_upload_size_mb",
        0,
    )
    service = ResumeUploadService(
        upload_dir=tmp_path,
        pdf_extractor=PDFExtractionService(),
    )
    upload = UploadFile(
        file=io.BytesIO(content),
        filename="jordan-lee.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )

    with pytest.raises(ValidationError, match="maximum size"):
        await service.upload_and_extract_gmail(
            upload,
            content,
            candidate_id="candidate",
        )


@pytest.mark.asyncio
async def test_failed_gmail_graph_write_removes_persisted_upload(tmp_path):
    from fastapi import UploadFile
    from starlette.datastructures import Headers

    content = make_pdf(
        "Jordan Lee\njordan.lee@example.com\n"
        "Software Engineer\nExperience 2020 - Present"
    )
    ingest_service = make_ingest_service(tmp_path, FakeNeo4jDatabase())

    async def fail_graph_persistence(*args, **kwargs):
        raise RuntimeError("Neo4j write failed")

    ingest_service.candidate_service.create_gmail_candidate = fail_graph_persistence
    upload = UploadFile(
        file=io.BytesIO(content),
        filename="jordan-lee.pdf",
        headers=Headers({"content-type": "application/pdf"}),
    )

    with pytest.raises(RuntimeError, match="Neo4j write failed"):
        await ingest_service.ingest_gmail_attachment(
            upload,
            content,
            message_id="message",
            attachment_id="attachment",
            sha256="test-sha256",
        )

    assert list(tmp_path.iterdir()) == []
