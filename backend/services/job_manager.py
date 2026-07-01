import uuid
import asyncio
import json
from typing import Dict, List, Optional, Set
from pydantic import BaseModel
from datetime import datetime

class JobStatus(BaseModel):
    model_config = {'protected_namespaces': ()}
    id: str
    filepath: str
    status: str  # pending, probing, extracting, transcribing, translating, completed, failed
    progress: float
    message: str
    created_at: datetime
    updated_at: datetime
    target_languages: List[str]
    base_language: str
    model_size: str
    provider: str
    engine: str
    ignore_forced_subs: bool
    custom_prompt: str = ""
    use_vad: bool = True
    transcribed: bool = False
    translation_engine: str = "nllb"
    llm_model: str = ""
    llm_model_path: str = ""
    hardcode_subs: bool = False
    deep_cleanup: bool = True
    vad_onset: float = 0.500
    vad_offset: float = 0.363
    vad_model: str = "pyannote"
    fetch_internet_subs: bool = False
    allow_title_match: bool = False
    use_nfo: bool = False
    auto_sync: bool = False
    fallback_to_targets: bool = False
    fetch_all_available: bool = False
    actual_source_lang: Optional[str] = None
    transcription_lang_hint: Optional[str] = None
    enable_extraction: bool = True
    enable_transcription: bool = True
    emby_naming: bool = False

class JobManager:
    def __init__(self):
        self.jobs: Dict[str, JobStatus] = {}
        self.listeners: Set[asyncio.Queue] = set()

    async def add_listener(self, queue: asyncio.Queue):
        self.listeners.add(queue)
        # On new connection: send full list so client can build initial state
        all_jobs = [job.model_dump() for job in self.get_all_jobs()]
        await queue.put(json.dumps({"type": "init", "jobs": all_jobs}, default=str))

    async def remove_listener(self, queue: asyncio.Queue):
        if queue in self.listeners:
            self.listeners.remove(queue)

    # Fix #5: Send only the changed job as a delta instead of re-serializing the ENTIRE list on
    # every tiny progress update. Reduces SSE payload from O(n) to O(1) per update.
    async def _notify_listeners(self, job: JobStatus):
        payload = json.dumps({"type": "update", "job": job.model_dump()}, default=str)
        for q in self.listeners:
            await q.put(payload)

    def create_job(self, filepath: str, target_languages: List[str], base_language: str, model_size: str, provider: str = "auto", engine: str = "faster-whisper", ignore_forced_subs: bool = True, custom_prompt: str = "", use_vad: bool = True, translation_engine: str = "nllb", llm_model: str = "", hardcode_subs: bool = False, deep_cleanup: bool = True, vad_onset: float = 0.500, vad_offset: float = 0.363, vad_model: str = "pyannote", fetch_internet_subs: bool = False, allow_title_match: bool = False, use_nfo: bool = False, auto_sync: bool = False, fallback_to_targets: bool = False, fetch_all_available: bool = False, llm_model_path: str = "", enable_extraction: bool = True, enable_transcription: bool = True, emby_naming: bool = False) -> JobStatus:
        job_id = str(uuid.uuid4())
        now = datetime.now()
        job = JobStatus(
            id=job_id,
            filepath=filepath,
            status="pending",
            progress=0.0,
            message="Waiting to start",
            created_at=now,
            updated_at=now,
            target_languages=target_languages,
            base_language=base_language,
            model_size=model_size,
            provider=provider,
            engine=engine,
            ignore_forced_subs=ignore_forced_subs,
            custom_prompt=custom_prompt,
            use_vad=use_vad,
            transcribed=False,
            translation_engine=translation_engine,
            llm_model=llm_model,
            hardcode_subs=hardcode_subs,
            deep_cleanup=deep_cleanup,
            vad_onset=vad_onset,
            vad_offset=vad_offset,
            vad_model=vad_model,
            fetch_internet_subs=fetch_internet_subs,
            allow_title_match=allow_title_match,
            use_nfo=use_nfo,
            auto_sync=auto_sync,
            fallback_to_targets=fallback_to_targets,
            fetch_all_available=fetch_all_available,
            llm_model_path=llm_model_path,
            enable_extraction=enable_extraction,
            enable_transcription=enable_transcription,
            emby_naming=emby_naming
        )
        self.jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[JobStatus]:
        return self.jobs.get(job_id)

    def get_all_jobs(self) -> List[JobStatus]:
        return sorted(list(self.jobs.values()), key=lambda x: x.created_at, reverse=False)

    async def update_job(self, job_id: str, status: str = None, progress: float = None, message: str = None, transcribed: bool = None, transcription_lang_hint: str = None):
        job = self.jobs.get(job_id)
        if job:
            if status is not None:
                job.status = status
            if progress is not None:
                job.progress = progress
            if message is not None:
                job.message = message
            if transcribed is not None:
                job.transcribed = transcribed
            if transcription_lang_hint is not None:
                job.transcription_lang_hint = transcription_lang_hint
            job.updated_at = datetime.now()
            await self._notify_listeners(job)
            
    async def cancel_job(self, job_id: str) -> bool:
        job = self.jobs.get(job_id)
        if job and job.status not in ["completed", "failed", "cancelled"]:
            job.status = "cancelled"
            job.message = "Cancelled by user"
            job.updated_at = datetime.now()
            await self._notify_listeners(job)
            return True
        return False

job_manager = JobManager()
