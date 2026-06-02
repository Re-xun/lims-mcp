"""Configuration defaults for MCP agent documentation generation."""

DEFAULT_CANDIDATES = "dist/list_query_mcp_candidates.csv"
DEFAULT_INVENTORY = "dist/list_query_inventory.json"
DEFAULT_OUTPUT_DIR = "docs/mcpagent"
DEFAULT_FRONTEND_ROOT = r"C:\Users\cwx20\WebstormProjects\lims-client-pc-v3\lims-base"

TEXT_TYPES = {"textField", "textfield", "textArea", "textarea", "fastSearch", "fastsearch"}
DATE_TYPES = {"dateField", "datefield", "timehorizonfield", "datetimefield"}
EXACT_TYPES = {"comboBox", "combobox", "numberfield", "checkbox", "radio", "hidden"}
EXCLUDED_GRID_NAMES = {"toolbar"}
FILTER_CANDIDATE_CTYPES = {
    "textfield",
    "textField",
    "comboBox",
    "combobox",
    "numberfield",
    "timehorizonfield",
    "datefield",
}
DATE_CANDIDATE_CTYPES = {"timehorizonfield", "datefield", "datetimefield"}
