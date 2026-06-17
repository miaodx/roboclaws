from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Normalizer = Callable[..., dict[str, Any]]
CandidateScorer = Callable[[dict[str, Any], list[Any]], dict[str, Any]]
RatioFn = Callable[[int | float, int | float], float]


def score_variant_metrics(
    *,
    variant_id: str,
    frames: list[Any],
    labels: list[Any],
    predictions: dict[str, dict[str, Any]],
    threshold: int,
    response_schema: str,
    visual_labeler_response_schema: str,
    failure_classes: tuple[str, ...],
    normalize_response: Normalizer,
    score_candidate: CandidateScorer,
    ratio: RatioFn,
) -> dict[str, Any]:
    response_schema = _response_schema_for_variant(
        variant_id,
        response_schema=response_schema,
        visual_labeler_response_schema=visual_labeler_response_schema,
    )
    state = RawFpvVariantScoreState(
        variant_id=variant_id,
        threshold=threshold,
        failure_counts={key: 0 for key in failure_classes},
        hidden_truth_object_count=len(_object_ids(label for label in labels if _is_hidden(label))),
        visible_truth_objects=_object_ids(label for label in labels if not _is_hidden(label)),
        visible_truth_label_count=sum(1 for label in labels if not _is_hidden(label)),
    )
    labels_by_frame = _labels_by_frame(labels)

    for frame in frames:
        response = predictions.get(frame.frame_id) or _empty_response(response_schema)
        normalized = normalize_response(response, frame=frame, variant_id=variant_id)
        state.add_frame(
            frame=frame,
            frame_labels=labels_by_frame.get(frame.frame_id, []),
            normalized=normalized,
            score_candidate=score_candidate,
        )

    hidden_target_recovery = state.hidden_target_recovery()
    return {
        "variant_id": variant_id,
        **hidden_target_recovery,
        "visible_movable_label_quality": state.visible_movable_label_quality(ratio),
        "hidden_target_recovery": hidden_target_recovery,
        "evaluated_frames": state.evaluated_frames,
    }


@dataclass
class RawFpvVariantScoreState:
    variant_id: str
    threshold: int
    failure_counts: dict[str, int]
    hidden_truth_object_count: int
    visible_truth_objects: set[str]
    visible_truth_label_count: int
    evaluated_frames: list[dict[str, Any]] = field(default_factory=list)
    strict_unique: set[str] = field(default_factory=set)
    coarse_unique: set[str] = field(default_factory=set)
    diagnostic_unique: set[str] = field(default_factory=set)
    visible_matched_objects: set[str] = field(default_factory=set)
    visible_predicted_object_hits: int = 0
    visible_duplicate_count: int = 0
    category_tier_counts: dict[str, int] = field(
        default_factory=lambda: {
            "exact": 0,
            "semantic": 0,
            "coarse_family": 0,
            "mismatch": 0,
        }
    )
    coarse_locality_match_count: int = 0
    surface_hint_only_count: int = 0
    duplicate_count: int = 0
    schema_failure_count: int = 0
    candidate_count: int = 0

    def add_frame(
        self,
        *,
        frame: Any,
        frame_labels: list[Any],
        normalized: dict[str, Any],
        score_candidate: CandidateScorer,
    ) -> None:
        schema_errors = list(normalized.get("schema_errors") or [])
        hidden_labels, visible_labels = _split_labels(frame_labels)

        self._record_schema_errors(schema_errors)
        self.surface_hint_only_count += int(normalized.get("surface_hint_only_count") or 0)
        frame_scores = self._score_frame_candidates(
            list(normalized.get("candidates") or []),
            hidden_labels=hidden_labels,
            visible_labels=visible_labels,
            score_candidate=score_candidate,
        )
        if not hidden_labels:
            self.failure_counts["missing_private_label"] += 1
        self.evaluated_frames.append(
            _frame_score_payload(
                frame=frame,
                candidates=list(normalized.get("candidates") or []),
                schema_errors=schema_errors,
                frame_labels=frame_labels,
                hidden_labels=hidden_labels,
                visible_labels=visible_labels,
                frame_scores=frame_scores,
            )
        )

    def hidden_target_recovery(self) -> dict[str, Any]:
        strict_count = len(self.strict_unique)
        coarse_count = len(self.coarse_unique)
        return {
            "variant_id": self.variant_id,
            "truth_object_count": self.hidden_truth_object_count,
            "candidate_count": self.candidate_count,
            "schema_failure_count": self.schema_failure_count,
            "failure_class_counts": dict(self.failure_counts),
            "strict_bbox_unique_confirmable_count": strict_count,
            "coarse_unique_confirmable_count": coarse_count,
            "unique_confirmable_count": coarse_count,
            "duplicate_count": self.duplicate_count,
            "diagnostic_candidate_unique_confirmable_count": len(self.diagnostic_unique),
            "live_like_top_candidate": {
                "threshold": self.threshold,
                "strict_bbox_unique_confirmable_count": strict_count,
                "coarse_unique_confirmable_count": coarse_count,
                "strict_bbox_threshold_met": strict_count >= self.threshold,
                "coarse_threshold_met": coarse_count >= self.threshold,
            },
        }

    def visible_movable_label_quality(self, ratio: RatioFn) -> dict[str, Any]:
        return {
            "status": "scoreable" if self.visible_truth_objects else "truth_sparse",
            "truth_object_count": len(self.visible_truth_objects),
            "truth_label_count": self.visible_truth_label_count,
            "predicted_object_hit_count": self.visible_predicted_object_hits,
            "predicted_object_label_count": self.candidate_count,
            "unique_matched_object_count": len(self.visible_matched_objects),
            "recall": ratio(len(self.visible_matched_objects), len(self.visible_truth_objects)),
            "precision": ratio(self.visible_predicted_object_hits, self.candidate_count),
            "category_match_tiers": dict(self.category_tier_counts),
            "coarse_locality_match_count": self.coarse_locality_match_count,
            "duplicate_rate": ratio(
                self.visible_duplicate_count,
                self.visible_predicted_object_hits,
            ),
            "schema_failure_rate": ratio(self.schema_failure_count, max(1, self.candidate_count)),
            "surface_hint_only_count": self.surface_hint_only_count,
            "fixtures_surfaces_scored_as_hints_only": True,
        }

    def _record_schema_errors(self, schema_errors: list[str]) -> None:
        if not schema_errors:
            return
        self.schema_failure_count += len(schema_errors)
        self.failure_counts["schema_failure"] += len(schema_errors)

    def _score_frame_candidates(
        self,
        candidates: list[dict[str, Any]],
        *,
        hidden_labels: list[Any],
        visible_labels: list[Any],
        score_candidate: CandidateScorer,
    ) -> list[dict[str, Any]]:
        frame_scores = []
        for index, candidate in enumerate(candidates):
            score = score_candidate(candidate, hidden_labels)
            score["rank"] = index + 1
            frame_scores.append(score)
            self._record_hidden_candidate(index, score)
            if index == 0:
                self._record_visible_candidate(
                    candidate,
                    visible_labels=visible_labels,
                    score_candidate=score_candidate,
                )
        return frame_scores

    def _record_hidden_candidate(self, index: int, score: dict[str, Any]) -> None:
        self.candidate_count += 1
        matched_id = str(score.get("matched_object_id") or "")
        if bool(score.get("coarse_confirmable")) and self._is_duplicate(
            self.diagnostic_unique, matched_id
        ):
            self.duplicate_count += 1
        if index == 0:
            self._record_top_hidden_candidate(score, matched_id)

    def _record_top_hidden_candidate(self, score: dict[str, Any], matched_id: str) -> None:
        if bool(score.get("strict_bbox_confirmable")) and self._is_duplicate(
            self.strict_unique, matched_id
        ):
            self.duplicate_count += 1
        if bool(score.get("coarse_confirmable")) and self._is_duplicate(
            self.coarse_unique, matched_id
        ):
            self.duplicate_count += 1
        if score.get("strict_bbox_confirmable") or score.get("coarse_confirmable"):
            return
        reason = str(score.get("failure_class") or "")
        if reason in self.failure_counts:
            self.failure_counts[reason] += 1

    def _record_visible_candidate(
        self,
        candidate: dict[str, Any],
        *,
        visible_labels: list[Any],
        score_candidate: CandidateScorer,
    ) -> None:
        visible_score = score_candidate(candidate, visible_labels)
        visible_matched_id = str(visible_score.get("matched_object_id") or "")
        if bool(visible_score.get("coarse_confirmable")) and visible_matched_id:
            self.visible_predicted_object_hits += 1
            if self._is_duplicate(self.visible_matched_objects, visible_matched_id):
                self.visible_duplicate_count += 1
        tier = str(visible_score.get("category_match_tier") or "mismatch")
        if tier in self.category_tier_counts:
            self.category_tier_counts[tier] += 1
        if visible_score.get("coarse_region_match"):
            self.coarse_locality_match_count += 1

    @staticmethod
    def _is_duplicate(unique_ids: set[str], object_id: str) -> bool:
        if not object_id:
            return False
        duplicate = object_id in unique_ids
        unique_ids.add(object_id)
        return duplicate


def _frame_score_payload(
    *,
    frame: Any,
    candidates: list[dict[str, Any]],
    schema_errors: list[str],
    frame_labels: list[Any],
    hidden_labels: list[Any],
    visible_labels: list[Any],
    frame_scores: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "frame_id": frame.frame_id,
        "source_observation_id": frame.source_observation_id,
        "candidate_count": len(candidates),
        "schema_errors": schema_errors,
        "label_count": len(frame_labels),
        "hidden_target_label_count": len(hidden_labels),
        "visible_movable_label_count": len(visible_labels),
        "scores": frame_scores,
    }


def _labels_by_frame(labels: list[Any]) -> dict[str, list[Any]]:
    labels_by_frame: dict[str, list[Any]] = {}
    for label in labels:
        labels_by_frame.setdefault(label.frame_id, []).append(label)
    return labels_by_frame


def _split_labels(labels: list[Any]) -> tuple[list[Any], list[Any]]:
    hidden_labels = [label for label in labels if _is_hidden(label)]
    visible_labels = [label for label in labels if not _is_hidden(label)]
    return hidden_labels, visible_labels


def _object_ids(labels: Any) -> set[str]:
    return {str(label.object_id) for label in labels}


def _is_hidden(label: Any) -> bool:
    return bool(label.hidden_target)


def _empty_response(response_schema: str) -> dict[str, Any]:
    return {
        "schema": response_schema,
        "candidates": [],
        "labels": [],
    }


def _response_schema_for_variant(
    variant_id: str,
    *,
    response_schema: str,
    visual_labeler_response_schema: str,
) -> str:
    if variant_id == "raw_fpv_visual_labeler":
        return visual_labeler_response_schema
    return response_schema
