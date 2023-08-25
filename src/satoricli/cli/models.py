from dataclasses import dataclass


@dataclass
class BootstrapTable:
    """Based on https://bootstrap-table.com/docs/api/table-options/#url"""

    total: int
    totalNotFiltered: int
    rows: list[dict]
