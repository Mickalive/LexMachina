"""
LexMachina Streaming Import Manager
Provides asynchronous, streaming import of user corpus records with
progress tracking, cancellation support, and incremental persistence.

Designed for 192k-scale imports without blocking the server.
"""
import hashlib
import json
import os
import time
import threading
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any

import numpy as np


class ImportJob:
    """Represents a single import job with progress tracking and cancellation."""

    def __init__(self, job_id: str, records: List[Dict]):
        self.job_id = job_id
        self.records = records
        self.status = "pending"  # pending, running, completed, failed, cancelled
        self.total = len(records)
        self.processed = 0
        self.valid = 0
        self.invalid = 0
        self.positioned = 0
        self.errors: List[str] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.result_positions: List[Dict] = []
        self._cancelled = False

    def cancel(self):
        """Request cancellation of this import job."""
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def progress(self) -> Dict[str, Any]:
        """Return current progress snapshot."""
        elapsed_ms = 0.0
        if self.start_time:
            end = self.end_time or time.time()
            elapsed_ms = round((end - self.start_time) * 1000, 1)

        return {
            "job_id": self.job_id,
            "status": self.status,
            "total": self.total,
            "processed": self.processed,
            "valid": self.valid,
            "invalid": self.invalid,
            "positioned": self.positioned,
            "elapsed_ms": elapsed_ms,
            "progress_pct": round(self.processed / self.total * 100, 1) if self.total > 0 else 100.0,
        }


class ImportManager:
    """Manages streaming import jobs with background processing.

    Accepts a NavigationAPI instance to leverage its schema validation,
    embedding model, and position persistence infrastructure.
    """

    BATCH_SIZE = 50

    def __init__(self, nav_api):
        self._nav_api = nav_api
        self._jobs: Dict[str, ImportJob] = {}
        self._lock = threading.Lock()

    def submit_import(self, records: List[Dict]) -> str:
        """Submit records for asynchronous import.

        Args:
            records: List of decision record dicts to import.

        Returns:
            job_id string for status polling.
        """
        job_id = f"import_{uuid.uuid4().hex[:12]}"
        job = ImportJob(job_id, records)

        with self._lock:
            self._jobs[job_id] = job

        thread = threading.Thread(
            target=self._process_job, args=(job,), daemon=True
        )
        thread.start()

        return job_id

    def get_status(self, job_id: str) -> Dict[str, Any]:
        """Get import job status and progress.

        Args:
            job_id: The job ID returned by submit_import.

        Returns:
            Progress dict, or error dict if job not found.
        """
        with self._lock:
            job = self._jobs.get(job_id)

        if job is None:
            return {"error": f"Job {job_id} not found"}

        return job.progress()

    def cancel_import(self, job_id: str) -> bool:
        """Cancel a running import job.

        Args:
            job_id: The job ID to cancel.

        Returns:
            True if cancellation was requested, False if job not found.
        """
        with self._lock:
            job = self._jobs.get(job_id)

        if job is None:
            return False

        job.cancel()
        return True

    def _process_job(self, job: ImportJob):
        """Process import job in background thread.

        Iterates through records in batches, validates each record,
        computes map positions for valid records, and persists results
        incrementally. Checks for cancellation between batches.
        """
        job.status = "running"
        job.start_time = time.time()

        try:
            validator = self._nav_api.corpus._schema_validator
            embedding_model = self._nav_api._embedding_model
            base_embeddings = self._nav_api._base_embeddings
            base_decision_ids = self._nav_api._base_decision_ids
            import_positions_file = self._nav_api._import_positions_file
            imported_positions = self._nav_api._imported_positions
            default_representation = self._nav_api._get_default_representation()

            # Get base map data for cluster assignments
            zoom_level = 1
            base_map = self._nav_api.map_loader.get_zoom_level(
                default_representation, zoom_level
            )
            base_positions = base_map.positions if base_map else {}
            base_cluster_assignments = base_map.cluster_assignments if base_map else {}

            has_embeddings = (
                base_embeddings is not None
                and len(base_embeddings) > 0
                and embedding_model is not None
            )

            # Process in batches
            records = job.records
            valid_records: List[Dict] = []

            for batch_start in range(0, len(records), self.BATCH_SIZE):
                if job.is_cancelled:
                    job.status = "cancelled"
                    job.end_time = time.time()
                    return

                batch_end = min(batch_start + self.BATCH_SIZE, len(records))
                batch = records[batch_start:batch_end]

                for record in batch:
                    try:
                        result = validator.validate(record, strict=False)
                        if result.valid:
                            job.valid += 1
                            valid_records.append(result.normalized_record)
                        else:
                            job.invalid += 1
                            job.errors.append(
                                f"{record.get('decision_id', 'unknown')}: "
                                + "; ".join(result.errors)
                            )
                    except Exception as e:
                        job.invalid += 1
                        job.errors.append(
                            f"{record.get('decision_id', 'unknown')}: validation exception: {e}"
                        )
                    finally:
                        job.processed += 1

                # Persist validated records incrementally after each batch
                if valid_records:
                    self._persist_batch(valid_records, import_positions_file, job)
                    valid_records.clear()

                # Yield control briefly to allow cancellation checks
                time.sleep(0)

            # Phase 2: Compute positions for all valid imported decisions
            if not job.is_cancelled and has_embeddings and job.valid > 0:
                self._compute_positions(job, embedding_model, base_embeddings,
                                       base_decision_ids, base_positions,
                                       base_cluster_assignments,
                                       default_representation, zoom_level,
                                       import_positions_file, imported_positions)

            if job.is_cancelled:
                job.status = "cancelled"
            elif job.errors and job.valid == 0:
                job.status = "failed"
            else:
                job.status = "completed"

        except Exception as e:
            job.status = "failed"
            job.errors.append(f"Fatal processing error: {e}")

        finally:
            job.end_time = time.time()

    def _persist_batch(
        self,
        records: List[Dict],
        positions_file: Optional[Path],
        job: Optional[ImportJob] = None,
    ):
        """Persist a batch of validated records to disk as JSONL."""
        if not positions_file:
            return

        positions_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(positions_file, "a", encoding="utf-8") as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            error_msg = f"Persist batch failed ({len(records)} records): {e}"
            if job is not None:
                job.errors.append(error_msg)
            raise

    def compact_positions(self, positions_file: Optional[Path] = None):
        """Deduplicate imported_positions.jsonl by keeping only the last
        position for each (decision_id, representation) pair.

        This prevents unbounded file growth on re-import.
        """
        if not positions_file or not positions_file.exists():
            return

        latest: Dict[tuple, Dict] = {}
        with open(positions_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = (record.get("decision_id", ""), record.get("representation", ""))
                latest[key] = record

        tmp_file = positions_file.with_suffix(".jsonl.compact")
        with open(tmp_file, "w", encoding="utf-8") as f:
            for record in latest.values():
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

        tmp_file.replace(positions_file)

    def _compute_positions(
        self,
        job: ImportJob,
        embedding_model,
        base_embeddings: np.ndarray,
        base_decision_ids: List[str],
        base_positions: Dict,
        base_cluster_assignments: Dict,
        representation: str,
        zoom_level: int,
        import_positions_file: Optional[Path],
        imported_positions: Dict,
    ):
        """Compute map positions for valid records via k-NN in embedding space.

        Processes records in batches for memory efficiency and checks
        for cancellation between each batch.
        """
        # Read validated decisions from the already-persisted JSONL file
        # instead of loading all 192k full-text decisions into memory.
        imported_decisions: List[Dict] = []
        if import_positions_file and import_positions_file.exists():
            with open(import_positions_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    did = record.get("decision_id", "")
                    if did and (did, representation) not in imported_positions:
                        imported_decisions.append(record)

        if not imported_decisions:
            return

        # Build texts for embedding
        texts: List[str] = []
        for d in imported_decisions:
            text = d.get("full_text", "") or d.get("text", "")
            if not text:
                text = f"{d.get('title', '')} {d.get('legal_area', '')}"
            texts.append(text)

        # Compute embeddings in batches
        embedding_batch_size = 256
        all_embeddings = None

        for emb_start in range(0, len(texts), embedding_batch_size):
            if job.is_cancelled:
                return

            emb_end = min(emb_start + embedding_batch_size, len(texts))
            batch_texts = texts[emb_start:emb_end]

            try:
                batch_embs = embedding_model.encode(
                    batch_texts, convert_to_numpy=True, show_progress_bar=False
                )
                if all_embeddings is None:
                    all_embeddings = batch_embs
                else:
                    all_embeddings = np.vstack([all_embeddings, batch_embs])
            except Exception:
                # Skip remaining if encoding fails
                return

        if all_embeddings is None or len(all_embeddings) == 0:
            return

        # Pre-normalize base embeddings for cosine similarity
        base_norms = np.linalg.norm(base_embeddings, axis=1, keepdims=True)
        base_norms[base_norms == 0] = 1
        base_normalized = base_embeddings / base_norms

        k = 5
        jitter_scale = 0.01

        # Process position computation in batches
        for pos_start in range(0, len(imported_decisions), self.BATCH_SIZE):
            if job.is_cancelled:
                return

            pos_end = min(pos_start + self.BATCH_SIZE, len(imported_decisions))

            for i in range(pos_start, pos_end):
                decision = imported_decisions[i]
                did = decision.get("decision_id", "")
                if not did:
                    continue

                # Skip already-positioned
                if (did, representation) in imported_positions:
                    continue

                emb = all_embeddings[i]

                # Cosine similarity against base corpus
                emb_norm = np.linalg.norm(emb)
                if emb_norm == 0:
                    continue
                emb_normalized = emb / emb_norm
                similarities = base_normalized @ emb_normalized

                # Top-k neighbors
                top_k_indices = np.argpartition(similarities, -k)[-k:]
                top_k_indices = top_k_indices[np.argsort(similarities[top_k_indices])[::-1]]

                # Gather neighbor clusters and positions
                neighbor_clusters: List[int] = []
                neighbor_positions: List[tuple] = []
                for idx in top_k_indices:
                    neighbor_did = base_decision_ids[idx]
                    if neighbor_did in base_cluster_assignments:
                        neighbor_clusters.append(base_cluster_assignments[neighbor_did])
                    if neighbor_did in base_positions:
                        neighbor_positions.append(base_positions[neighbor_did])

                if not neighbor_clusters:
                    continue

                # Majority cluster assignment
                from collections import Counter
                cluster_counter = Counter(neighbor_clusters)
                assigned_cluster = cluster_counter.most_common(1)[0][0]

                # Position: centroid of neighbors with jitter
                if neighbor_positions:
                    centroid_x = float(np.mean([p[0] for p in neighbor_positions]))
                    centroid_y = float(np.mean([p[1] for p in neighbor_positions]))
                    seed = int(hashlib.md5(did.encode()).hexdigest()[:8], 16) % (2**31)
                    rng = np.random.RandomState(seed)
                    x = centroid_x + float(rng.normal(0, jitter_scale))
                    y = centroid_y + float(rng.normal(0, jitter_scale))
                else:
                    x, y = 0.0, 0.0

                record = {
                    "decision_id": did,
                    "x": x,
                    "y": y,
                    "cluster": int(assigned_cluster),
                    "zoom_level": zoom_level,
                    "representation": representation,
                    "neighbor_count": len(neighbor_clusters),
                    "assigned_via": "knn_embedding",
                }

                # Persist position
                imported_positions[(did, representation)] = record
                if import_positions_file:
                    try:
                        with open(import_positions_file, "a", encoding="utf-8") as f:
                            f.write(json.dumps(record, ensure_ascii=False) + "\n")
                    except Exception:
                        pass

                job.positioned += 1
                job.result_positions.append(record)

            # Yield between batches
            time.sleep(0)
