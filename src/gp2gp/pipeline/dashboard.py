import sys
from dataclasses import asdict
from datetime import datetime

from argparse import ArgumentParser

from dateutil.relativedelta import relativedelta
from dateutil.tz import tzutc

from gp2gp.io.csv import read_gzip_csv_files
from gp2gp.io.dictionary import camelize_dict
from gp2gp.io.json import write_json_file, read_json_file
from gp2gp.odsportal.sources import construct_practice_list_from_dict
from gp2gp.spine.sources import construct_messages_from_splunk_items
from gp2gp.spine.transformers import (
    group_into_conversations,
    parse_conversation,
    filter_conversations_by_request_started_time,
)
from gp2gp.service.transformers import (
    derive_transfers,
    filter_for_successful_transfers,
    calculate_sla_by_practice,
)
from gp2gp.dashboard.transformers import construct_service_dashboard_data


def _list_str(values):
    return values.split(",")


def parse_dashboard_pipeline_arguments(args):
    parser = ArgumentParser(description="GP2GP Service dashboard data pipeline")
    parser.add_argument("--month", type=int)
    parser.add_argument("--year", type=int)
    parser.add_argument("--practice-list-file", type=str)
    parser.add_argument("--input-files", type=_list_str)
    parser.add_argument("--practice-metrics-output-file", type=str)
    parser.add_argument("--practice-metadata-output-file", type=str)
    return parser.parse_args(args)


def parse_conversations(conversations):
    for conversation in conversations:
        gp2gp_conversation = parse_conversation(conversation)
        if gp2gp_conversation is not None:
            yield gp2gp_conversation


def process_messages(messages, start, end, practice_list):
    conversations = group_into_conversations(messages)
    parsed_conversations = parse_conversations(conversations)
    conversations_started_in_range = filter_conversations_by_request_started_time(
        parsed_conversations, start, end
    )
    transfers = derive_transfers(conversations_started_in_range)
    completed_transfers = filter_for_successful_transfers(transfers)
    sla_metrics = calculate_sla_by_practice(practice_list, completed_transfers)
    dashboard_data = construct_service_dashboard_data(
        sla_metrics, year=start.year, month=start.month
    )
    return dashboard_data


def write_service_dashboard_json_file(dashboard_data, output_file_path):
    content_dict = asdict(dashboard_data)
    camelized_dict = camelize_dict(content_dict)
    write_json_file(camelized_dict, output_file_path)


def read_spine_csv_gz_files(file_paths):
    items = read_gzip_csv_files(file_paths)
    return construct_messages_from_splunk_items(items)


def main():
    args = parse_dashboard_pipeline_arguments(sys.argv[1:])

    metric_month = datetime(args.year, args.month, 1, tzinfo=tzutc())
    next_month = metric_month + relativedelta(months=1)

    practice_metrics_output_file_path = args.practice_metrics_output_file
    practice_metadata_output_file_path = args.practice_metadata_output_file

    practice_data = read_json_file(args.practice_list_file)
    practice_metadata = construct_practice_list_from_dict(practice_data)

    write_service_dashboard_json_file(practice_metadata, practice_metadata_output_file_path)

    spine_messages = read_spine_csv_gz_files(args.input_files)
    service_dashboard_data = process_messages(
        spine_messages, metric_month, next_month, practice_metadata.practices
    )

    write_service_dashboard_json_file(service_dashboard_data, practice_metrics_output_file_path)
