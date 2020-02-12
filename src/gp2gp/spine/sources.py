import csv
import gzip
from typing import BinaryIO, Iterator, List

from dateutil import parser

from gp2gp.spine.models import Message


def _parse_error_code(error):
    return None if error == "NONE" else int(error)


def _parse_message_ref(ref):
    return None if ref == "NotProvided" else ref


def read_spine_csv_gz_files(input_file_paths: List[str]) -> Iterator[Message]:
    for file_path in input_file_paths:
        with open(file_path, "rb") as f:
            yield from _read_spine_csv_gz(f)


def _read_spine_csv_gz(input_file: BinaryIO) -> Iterator[Message]:
    with gzip.open(input_file, "rt") as f:
        input_csv = csv.DictReader(f)
        for row in input_csv:
            yield Message(
                time=parser.isoparse(row["_time"]),
                conversation_id=row["conversationID"],
                guid=row["GUID"],
                interaction_id=row["interactionID"],
                from_party_ods_code=row["fromNACS"],
                to_party_ods_code=row["toNACS"],
                message_ref=_parse_message_ref(row["messageRef"]),
                error_code=_parse_error_code(row["jdiEvent"]),
            )
