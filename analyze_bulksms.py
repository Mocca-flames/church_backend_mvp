#!/usr/bin/env python3
"""
BulkSMS Data Analyzer

This script reads and analyzes data from bulksms_stats.txt file.
It provides functions to:
1. Parse the data file
2. Map status codes to their meanings
3. Generate summary statistics
4. Identify phone numbers by status
"""

import sys
from collections import defaultdict
from typing import Dict, List, Tuple

# Status code mappings as provided in the task description
STATUS_CODES = {
    0: "In progress (a normal message submission, with no error encountered so far)",
    10: "Delivered upstream (no longer on BulkSMS servers), with no further status yet available",
    11: "Successfully delivered",
    31: "Unroutable: message could not be delivered because of an internal routing decision. Please contact Support for further information",
    32: "Failed: blocked - typically because of a previous complaint or opt-out by the recipient",
    33: "Failed: censored based on message content",
    34: "Failed: censored based on message content",
    50: "Delivery failed - generic failure",
    51: "Delivery failed - generic failure",
    52: "Delivery failed - generic failure",
    53: "Failed: message expired (the phone was unavailable during the entire delivery retry period)",
    54: "Delivery failed - generic failure",
    55: "Delivery failed - generic failure",
    56: "Failed: censored based on message content",
    57: "Failed due to fault on the phone (e.g. SIM card or phone out of message storage space)"
}

def read_bulksms_data(file_path: str) -> List[Tuple[str, str, int]]:
    """
    Read and parse the bulksms_stats.txt file

    Args:
        file_path: Path to the bulksms_stats.txt file

    Returns:
        List of tuples containing (created_time, msisdn, status)
    """
    data = []

    try:
        with open(file_path, 'r') as file:
            # Skip header line
            next(file)

            for line in file:
                # Strip whitespace and split by tabs
                parts = line.strip().split('\t')
                if len(parts) == 3:
                    created_time, msisdn, status_str = parts
                    try:
                        status = int(status_str)
                        data.append((created_time, msisdn, status))
                    except ValueError:
                        print(f"Warning: Invalid status code '{status_str}' in line: {line.strip()}", file=sys.stderr)
                else:
                    print(f"Warning: Malformed line: {line.strip()}", file=sys.stderr)

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found", file=sys.stderr)
        sys.exit(1)

    return data

def get_status_distribution(data: List[Tuple[str, str, int]]) -> Dict[int, int]:
    """
    Get distribution of status codes

    Args:
        data: List of parsed data tuples

    Returns:
        Dictionary mapping status codes to their counts
    """
    distribution = defaultdict(int)

    for _, _, status in data:
        distribution[status] += 1

    return dict(distribution)

def get_phone_numbers_by_status(data: List[Tuple[str, str, int]], status_code: int) -> List[str]:
    """
    Get all phone numbers with a specific status code

    Args:
        data: List of parsed data tuples
        status_code: Status code to filter by

    Returns:
        List of phone numbers with the specified status
    """
    return [msisdn for _, msisdn, status in data if status == status_code]

def get_status_meaning(status_code: int) -> str:
    """
    Get the meaning of a status code

    Args:
        status_code: The status code to look up

    Returns:
        The meaning of the status code, or "Unknown status code" if not found
    """
    return STATUS_CODES.get(status_code, "Unknown status code")

def print_summary(data: List[Tuple[str, str, int]]):
    """
    Print a summary of the bulksms data

    Args:
        data: List of parsed data tuples
    """
    distribution = get_status_distribution(data)
    total_messages = len(data)

    print(f"Total messages: {total_messages}")
    print("\nStatus Code Distribution:")
    for status, count in sorted(distribution.items()):
        percentage = (count / total_messages) * 100
        meaning = get_status_meaning(status)
        print(f"  {status}: {count} ({percentage:.2f}%) - {meaning}")

    # Show example phone numbers for each status
    print("\nExample phone numbers by status:")
    for status in sorted(distribution.keys()):
        examples = get_phone_numbers_by_status(data, status)[:3]  # Get first 3 examples
        print(f"  Status {status}: {', '.join(examples)}")

def main():
    """Main function to run the analysis"""
    if len(sys.argv) != 2:
        print("Usage: python analyze_bulksms.py <path_to_bulksms_stats.txt>")
        sys.exit(1)

    file_path = sys.argv[1]
    data = read_bulksms_data(file_path)
    print_summary(data)

if __name__ == "__main__":
    main()