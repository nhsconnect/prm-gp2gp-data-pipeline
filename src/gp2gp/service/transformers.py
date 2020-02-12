from collections import defaultdict
from datetime import timedelta
from typing import Iterable, Iterator, Counter, DefaultDict, Set

from gp2gp.service.models import Transfer, ERROR_SUPPRESSED, PracticeSlaMetrics, SlaBand
from gp2gp.spine.models import ParsedConversation


THREE_DAYS_IN_SECONDS = 259200
EIGHT_DAYS_IN_SECONDS = 691200


def _calculate_sla(conversation):
    if conversation.request_completed is None or conversation.request_completed_ack is None:
        return None
    return conversation.request_completed_ack.time - conversation.request_completed.time


def _extract_requesting_practice_ods_code(conversation):
    return conversation.request_started.from_party_ods_code


def _extract_sending_practice_ods_code(conversation):
    return conversation.request_started.to_party_ods_code


def _extract_error_code(conversation):
    if conversation.request_completed_ack:
        return conversation.request_completed_ack.error_code
    return None


def _is_pending(conversation):
    return conversation.request_completed_ack is None


def _derive_transfer(conversation: ParsedConversation) -> Transfer:
    return Transfer(
        conversation_id=conversation.id,
        sla_duration=_calculate_sla(conversation),
        requesting_practice_ods_code=_extract_requesting_practice_ods_code(conversation),
        sending_practice_ods_code=_extract_sending_practice_ods_code(conversation),
        error_code=_extract_error_code(conversation),
        pending=_is_pending(conversation),
    )


def derive_transfers(conversations: Iterable[ParsedConversation]) -> Iterator[Transfer]:
    return (_derive_transfer(c) for c in conversations)


def _is_successful(transfer):
    return transfer.error_code is None or transfer.error_code == ERROR_SUPPRESSED


def filter_failed_transfers(transfers: Iterable[Transfer]) -> Iterator[Transfer]:
    return (t for t in transfers if _is_successful(t))


def filter_pending_transfers(transfers: Iterable[Transfer]) -> Iterator[Transfer]:
    return (t for t in transfers if not t.pending)


def _assign_to_sla_band(sla_duration: timedelta):
    sla_duration_in_seconds = sla_duration.total_seconds()
    if sla_duration_in_seconds <= THREE_DAYS_IN_SECONDS:
        return SlaBand.WITHIN_3_DAYS
    elif sla_duration_in_seconds <= EIGHT_DAYS_IN_SECONDS:
        return SlaBand.WITHIN_8_DAYS
    else:
        return SlaBand.BEYOND_8_DAYS


def calculate_sla_by_practice(transfers: Iterable[Transfer]) -> Iterator[PracticeSlaMetrics]:
    practice_counts: DefaultDict[str, Counter] = defaultdict(Counter)

    for transfer in transfers:
        ods_code = transfer.requesting_practice_ods_code
        if transfer.sla_duration is not None:
            sla_band = _assign_to_sla_band(transfer.sla_duration)
            practice_counts[ods_code][sla_band] += 1

    return (
        PracticeSlaMetrics(
            ods_code,
            within_3_days=counts[SlaBand.WITHIN_3_DAYS],
            within_8_days=counts[SlaBand.WITHIN_8_DAYS],
            beyond_8_days=counts[SlaBand.BEYOND_8_DAYS],
        )
        for ods_code, counts in practice_counts.items()
    )


def filter_practices(
    summaries: Iterable[PracticeSlaMetrics], ods_codes: Set[str]
) -> Iterator[PracticeSlaMetrics]:
    return (summary for summary in summaries if summary.ods_code in ods_codes)
