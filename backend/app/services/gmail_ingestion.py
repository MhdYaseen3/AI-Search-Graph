import re
from email.utils import parseaddr

from app.integration.gmail.client import GmailClient
from app.models import Candidate
from app.schemas.candidate import CandidateCreate
from app.services.candidate_management import CandidateManagementService
from app.services.pdf_extraction import PDFExtractionService
from app.services.skill_extraction import SkillExtractionService
from app.services.project_extraction import ProjectExtractionService
from app.services.education_extraction import EducationExtractionService
from app.services.technology_extraction import TechnologyExtractionService
from app.services.neo4j_graph import Neo4jGraphService
from app.services.gmail_message_tracking import (
    GmailMessageTrackingService,
)


class GmailIngestionService:
    """Process resume attachments received through Gmail."""

    def __init__(
        self,
        candidate_service: CandidateManagementService,
        pdf_service: PDFExtractionService,
        skill_service: SkillExtractionService,
        project_service: ProjectExtractionService,
        education_service: EducationExtractionService,
        technology_service: TechnologyExtractionService,
        graph_service: Neo4jGraphService,
        message_tracking_service: GmailMessageTrackingService,
    ):
        self.gmail = GmailClient()
        self.candidate_service = candidate_service
        self.pdf_service = pdf_service
        self.skill_service = skill_service
        self.project_service = project_service
        self.education_service = education_service
        self.technology_service = technology_service
        self.graph_service = graph_service
        self.message_tracking_service = message_tracking_service

    async def process_resume_emails(self, max_results: int = 10) -> list[dict]:
        messages = self.gmail.list_messages(max_results=max_results)
        attachments = self.gmail.list_attachments(max_results=max_results)

        print("\n========== GMAIL INGESTION DEBUG ==========")
        print("MESSAGES FOUND:", len(messages))
        print("ATTACHMENTS FOUND:", len(attachments))

        for message in messages:
            print(
                "MESSAGE:",
                message.get("id"),
                "| SENDER:",
                message.get("sender"),
                "| SUBJECT:",
                message.get("subject"),
            )

        for attachment in attachments:
            print(
                "ATTACHMENT:",
                attachment.get("message_id"),
                "| FILE:",
                attachment.get("filename"),
                "| MIME:",
                attachment.get("mime_type"),
                "| ATTACHMENT ID:",
                attachment.get("attachment_id"),
            )

        print("===========================================\n")

        results = []

        for attachment in attachments:

            # --------------------------------------------------
            # 1. Check file type
            # --------------------------------------------------
            if attachment.get("mime_type") != "application/pdf":
                print(
                    "SKIPPED: Attachment is not PDF:",
                    attachment.get("filename"),
                    attachment.get("mime_type"),
                )
                continue

            message_id = attachment["message_id"]
            already_processed = (
                await self.message_tracking_service.is_processed(
                    message_id
                )
            )

            if already_processed:
                print(
                    "SKIPPED: Gmail message already processed:",
                    message_id,
                )
                continue

            # --------------------------------------------------
            # 2. Find the Gmail message belonging to attachment
            # --------------------------------------------------
            message = next(
                (
                    item
                    for item in messages
                    if item["id"] == message_id
                ),
                None,
            )

            if not message:
                print(
                    "SKIPPED: Could not find message:",
                    message_id,
                )
                continue

            print(
                "MATCHED MESSAGE:",
                message_id,
            )

            # --------------------------------------------------
            # 3. Parse sender
            # --------------------------------------------------
            sender_name, sender_email = parseaddr(
                message.get("sender", "")
            )

            print(
                "SENDER NAME:",
                sender_name,
                "| EMAIL:",
                sender_email,
            )

            if not sender_email:
                print(
                    "SKIPPED: Could not extract sender email"
                )
                continue

            full_name = (
                sender_name.strip()
                or sender_email.split("@")[0]
            )

            print(
                "CANDIDATE NAME:",
                full_name,
            )

            # --------------------------------------------------
            # 4. Check existing candidate
            # --------------------------------------------------
            candidate = await self.candidate_service.get_by_email(
                sender_email
            )

            if candidate:
                candidate_id = candidate.id
                created = False

                print(
                    "EXISTING CANDIDATE:",
                    candidate_id,
                )

            else:
                candidate = await self.candidate_service.create(
                    CandidateCreate(
                        full_name=full_name,
                        email=sender_email,
                    )
                )

                candidate_id = candidate.id
                created = True

                print(
                    "NEW CANDIDATE CREATED:",
                    candidate_id,
                )

            # --------------------------------------------------
            # 5. Download attachment
            # --------------------------------------------------
            file_path = self.gmail.download_attachment(
                message_id=message_id,
                attachment_id=attachment["attachment_id"],
                filename=attachment["filename"],
            )

            print(
                "DOWNLOADED FILE:",
                file_path,
            )

            # --------------------------------------------------
            # 6. Extract PDF text
            # --------------------------------------------------
            raw_text = await self.pdf_service.extract_text(
                file_path
            )

            print(
                "PDF TEXT LENGTH:",
                len(raw_text),
            )

            # --------------------------------------------------
            # 7. Extract resume information
            # --------------------------------------------------
            skills = await self.skill_service.extract_skills(
                raw_text
            )

            projects = await self.project_service.extract_projects(
                raw_text
            )

            education = await self.education_service.extract_education(
                raw_text
            )

            technologies = (
                await self.technology_service.extract_technologies(
                    raw_text
                )
            )

            print("SKILLS:", skills)
            print("PROJECTS:", projects)
            print("EDUCATION:", education)
            print("TECHNOLOGIES:", technologies)

            # --------------------------------------------------
            # 8. Create Neo4j relationships
            # --------------------------------------------------
            for skill in skills:
                await self.graph_service.link_skill(
                    candidate_id,
                    skill,
                )

            for project in projects:
                await self.graph_service.link_project(
                    candidate_id,
                    project,
                )

            from app.models.education import Education
            from app.models.technology import Technology

            for edu in education:
                await self.graph_service.link_education(
                    candidate_id,
                    Education(institution=edu),
                )

            for tech in technologies:
                await self.graph_service.link_technology(
                    candidate_id,
                    Technology(name=tech),
                )

            await self.message_tracking_service.mark_processed(
                message_id=message_id,
                candidate_id=candidate_id,
            )

            # --------------------------------------------------
            # 9. Add result
            # --------------------------------------------------
            results.append(
                {
                    "message_id": message_id,
                    "candidate_id": candidate.id,
                    "created": created,
                    "skills": skills,
                    "projects": projects,
                    "education": education,
                    "technologies": technologies,
                }
            )

        return results

