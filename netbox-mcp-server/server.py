from mcp.server.fastmcp import FastMCP #type: ignore
from netbox_client import NetBoxRestClient #type: ignore
import os
import json
# Mapping of simple object names to API endpoints
NETBOX_OBJECT_TYPES = {
    # DCIM (Device and Infrastructure)
    "cables": "dcim/cables",
    "console-ports": "dcim/console-ports",
    "console-server-ports": "dcim/console-server-ports",
    "devices": "dcim/devices",
    "device-bays": "dcim/device-bays",
    "device-roles": "dcim/device-roles",
    "device-types": "dcim/device-types",
    "dcim.device-types": "dcim/device-types",
    "dcim.device-type": "dcim/device-types",
    "front-ports": "dcim/front-ports",
    "interfaces": "dcim/interfaces",
    "inventory-items": "dcim/inventory-items",
    "locations": "dcim/locations",
    "manufacturers": "dcim/manufacturers",
    "modules": "dcim/modules",
    "module-bays": "dcim/module-bays",
    "module-types": "dcim/module-types",
    "platforms": "dcim/platforms",
    "power-feeds": "dcim/power-feeds",
    "power-outlets": "dcim/power-outlets",
    "power-panels": "dcim/power-panels",
    "power-ports": "dcim/power-ports",
    "racks": "dcim/racks",
    "rack-reservations": "dcim/rack-reservations",
    "rack-roles": "dcim/rack-roles",
    "regions": "dcim/regions",
    "sites": "dcim/sites",
    "site-groups": "dcim/site-groups",
    "virtual-chassis": "dcim/virtual-chassis",

    # IPAM (IP Address Management)
    "asns": "ipam/asns",
    "asn-ranges": "ipam/asn-ranges",
    "aggregates": "ipam/aggregates",
    "fhrp-groups": "ipam/fhrp-groups",
    "ip-addresses": "ipam/ip-addresses",
    "ip-ranges": "ipam/ip-ranges",
    "prefixes": "ipam/prefixes",
    "rirs": "ipam/rirs",
    "roles": "ipam/roles",
    "route-targets": "ipam/route-targets",
    "services": "ipam/services",
    "vlans": "ipam/vlans",
    "vlan-groups": "ipam/vlan-groups",
    "vrfs": "ipam/vrfs",

    # Circuits
    "circuits": "circuits/circuits",
    "circuit-types": "circuits/circuit-types",
    "circuit-terminations": "circuits/circuit-terminations",
    "providers": "circuits/providers",
    "provider-networks": "circuits/provider-networks",

    # Virtualization
    "clusters": "virtualization/clusters",
    "cluster-groups": "virtualization/cluster-groups",
    "cluster-types": "virtualization/cluster-types",
    "virtual-machines": "virtualization/virtual-machines",
    "vm-interfaces": "virtualization/interfaces",

    # Tenancy
    "tenants": "tenancy/tenants",
    "tenant-groups": "tenancy/tenant-groups",
    "contacts": "tenancy/contacts",
    "contact-groups": "tenancy/contact-groups",
    "contact-roles": "tenancy/contact-roles",

    # VPN
    "ike-policies": "vpn/ike-policies",
    "ike-proposals": "vpn/ike-proposals",
    "ipsec-policies": "vpn/ipsec-policies",
    "ipsec-profiles": "vpn/ipsec-profiles",
    "ipsec-proposals": "vpn/ipsec-proposals",
    "l2vpns": "vpn/l2vpns",
    "tunnels": "vpn/tunnels",
    "tunnel-groups": "vpn/tunnel-groups",

    # Wireless
    "wireless-lans": "wireless/wireless-lans",
    "wireless-lan-groups": "wireless/wireless-lan-groups",
    "wireless-links": "wireless/wireless-links",

    # Extras
    "config-contexts": "extras/config-contexts",
    "custom-fields": "extras/custom-fields",
    "export-templates": "extras/export-templates",
    "image-attachments": "extras/image-attachments",
    "jobs": "extras/jobs",
    "saved-filters": "extras/saved-filters",
    "scripts": "extras/scripts",
    "tags": "extras/tags",
    "webhooks": "extras/webhooks",
}

mcp = FastMCP("NetBox", log_level="DEBUG")
netbox = None

def normalize_object_type(object_type: str) -> str:
    """Normalize object type by removing namespace prefix."""
    if "." in object_type:
        object_type = object_type.split(".", 1)[1]
    return object_type

def parse_filters(filters: dict | str) -> dict:
    """Parse filters from string to dict if needed."""
    if isinstance(filters, str):
        try:
            # First try standard JSON parsing
            try:
                return json.loads(filters)
            except json.JSONDecodeError:
                # Fallback: Replace single quotes if present
                return json.loads(filters.replace("'", '"'))
        except Exception as e:
            raise ValueError(f"Invalid filters format: {str(e)}")
    return filters

def validate_object_type(object_type: str):
    """Validate that object_type exists in mapping."""
    if object_type not in NETBOX_OBJECT_TYPES:
        valid_types = "\n".join(f"- {t}" for t in sorted(NETBOX_OBJECT_TYPES.keys()))
        raise ValueError(f"Invalid object_type. Must be one of:\n{valid_types}")

def resolve_tenant_identifier(tenant_name: str):
    """
    Resolve a tenant name to its slug or ID.
    Returns (identifier_type, identifier_value) where identifier_type is either 'tenant' or 'tenant_id'
    """
    # Handle cases where the LLM might try to pass "tenant_id_X" directly
    if tenant_name.startswith('tenant_id_'):
        # Extract the actual tenant name or ID from the malformed input
        actual_identifier = tenant_name.replace('tenant_id_', '')

        # Try to parse as integer (ID)
        try:
            tenant_id = int(actual_identifier)
            return 'tenant_id', tenant_id
        except ValueError:
            # If not an integer, treat as name
            tenant_name = actual_identifier

    # First try to find by exact name
    tenants = netbox.get("tenancy/tenants", params={"name": tenant_name})

    if tenants and len(tenants) > 0:
        tenant = tenants[0]
        # Prefer slug if available, otherwise use ID
        if tenant.get('slug'):
            return 'tenant', tenant['slug']
        else:
            return 'tenant_id', tenant['id']

    # If not found by exact name, try case-insensitive search
    tenants = netbox.get("tenancy/tenants", params={"q": tenant_name})
    if tenants and len(tenants) > 0:
        tenant = tenants[0]
        if tenant.get('slug'):
            return 'tenant', tenant['slug']
        else:
            return 'tenant_id', tenant['id']

    # If still not found, try by slug directly
    tenants = netbox.get("tenancy/tenants", params={"slug": tenant_name})
    if tenants and len(tenants) > 0:
        return 'tenant', tenant_name

    # If still not found, return the original name (will let NetBox handle the error)
    return 'tenant', tenant_name

def preprocess_filters(object_type: str, filters: dict) -> dict:
    """
    Preprocess filters to handle special cases like tenant name resolution.
    """
    processed_filters = filters.copy()

    # Handle tenant resolution
    if object_type in ["devices", "virtual-machines", "ip-addresses", "prefixes", "vlans", "vrfs"]:
        if "tenant" in processed_filters:
            tenant_value = processed_filters.pop("tenant")

            tenant_ids = []
            tenant_slugs = []

            # Accept string like "1,2" or a list
            if isinstance(tenant_value, str):
                tenant_list = [t.strip() for t in tenant_value.split(",")]
            elif isinstance(tenant_value, (list, tuple)):
                tenant_list = tenant_value
            else:
                tenant_list = [tenant_value]

            for t in tenant_list:
                identifier_type, identifier_value = resolve_tenant_identifier(str(t))
                if identifier_type == "tenant_id":
                    tenant_ids.append(identifier_value)
                else:
                    tenant_slugs.append(identifier_value)

            # Add back into filters
            if tenant_ids:
                processed_filters["tenant_id"] = tenant_ids
            if tenant_slugs:
                processed_filters["tenant"] = tenant_slugs

    # Manufacturer resolution
    if object_type == "device-types" and "manufacturer" in processed_filters and isinstance(processed_filters["manufacturer"], str):
        manufacturers = netbox.get("dcim/manufacturers", params={"name": processed_filters["manufacturer"]})
        if manufacturers and len(manufacturers) > 0:
            processed_filters["manufacturer_id"] = manufacturers[0]["id"]
            del processed_filters["manufacturer"]

    return processed_filters

@mcp.tool()
def netbox_get_objects(object_type: str, filters: dict | str):
    """
    Get objects from NetBox based on their type and filters
    Args:
        object_type: String representing the NetBox object type (e.g. "devices", "ip-addresses")
        filters: dict of filters to apply to the API call based on the NetBox API filtering options

    Valid object_type values:

    DCIM (Device and Infrastructure):
    - cables
    - console-ports
    - console-server-ports
    - devices
    - device-bays
    - device-roles
    - device-types
    - front-ports
    - interfaces
    - inventory-items
    - locations
    - manufacturers
    - modules
    - module-bays
    - module-types
    - platforms
    - power-feeds
    - power-outlets
    - power-panels
    - power-ports
    - racks
    - rack-reservations
    - rack-roles
    - regions
    - sites
    - site-groups
    - virtual-chassis

    IPAM (IP Address Management):
    - asns
    - asn-ranges
    - aggregates
    - fhrp-groups
    - ip-addresses
    - ip-ranges
    - prefixes
    - rirs
    - roles
    - route-targets
    - services
    - vlans
    - vlan-groups
    - vrfs

    Circuits:
    - circuits
    - circuit-types
    - circuit-terminations
    - providers
    - provider-networks

    Virtualization:
    - clusters
    - cluster-groups
    - cluster-types
    - virtual-machines
    - vm-interfaces

    Tenancy:
    - tenants
    - tenant-groups
    - contacts
    - contact-groups
    - contact-roles

    VPN:
    - ike-policies
    - ike-proposals
    - ipsec-policies
    - ipsec-profiles
    - ipsec-proposals
    - l2vpns
    - tunnels
    - tunnel-groups

    Wireless:
    - wireless-lans
    - wireless-lan-groups
    - wireless-links

    See NetBox API documentation for filtering options for each object type.
    """
    # Parse and normalize inputs
    filters = parse_filters(filters)
    object_type = normalize_object_type(object_type)
    validate_object_type(object_type)

    # Preprocess filters (e.g., resolve tenant names to slugs/IDs)
    filters = preprocess_filters(object_type, filters)

    # Get API endpoint from mapping
    endpoint = NETBOX_OBJECT_TYPES[object_type]

    # Make API call
    return netbox.get(endpoint, params=filters)

@mcp.tool()
def netbox_get_object_by_id(object_type: str, object_id: int):
    """
    Get detailed information about a specific NetBox object by its ID.
    """
    # Normalize and validate object_type
    object_type = normalize_object_type(object_type)
    validate_object_type(object_type)

    endpoint = f"{NETBOX_OBJECT_TYPES[object_type]}/{object_id}"
    return netbox.get(endpoint)


@mcp.tool()
def netbox_get_changelogs(filters: dict):
    """
    Get object change records (changelogs) from NetBox based on filters.

    Args:
        filters: dict of filters to apply to the API call based on the NetBox API filtering options

    Returns:
        List of changelog objects matching the specified filters

    Filtering options include:
    - user_id: Filter by user ID who made the change
    - user: Filter by username who made the change
    - changed_object_type_id: Filter by ContentType ID of the changed object
    - changed_object_id: Filter by ID of the changed object
    - object_repr: Filter by object representation (usually contains object name)
    - action: Filter by action type (created, updated, deleted)
    - time_before: Filter for changes made before a given time (ISO 8601 format)
    - time_after: Filter for changes made after a given time (ISO 8601 format)
    - q: Search term to filter by object representation

    Example:
    To find all changes made to a specific device with ID 123:
    {"changed_object_type_id": "dcim.device", "changed_object_id": 123}

    To find all deletions in the last 24 hours:
    {"action": "delete", "time_after": "2023-01-01T00:00:00Z"}

    Each changelog entry contains:
    - id: The unique identifier of the changelog entry
    - user: The user who made the change
    - user_name: The username of the user who made the change
    - request_id: The unique identifier of the request that made the change
    - action: The type of action performed (created, updated, deleted)
    - changed_object_type: The type of object that was changed
    - changed_object_id: The ID of the object that was changed
    - object_repr: String representation of the changed object
    - object_data: The object's data after the change (null for deletions)
    - object_data_v2: Enhanced data representation
    - prechange_data: The object's data before the change (null for creations)
    - postchange_data: The object's data after the change (null for deletions)
    - time: The timestamp when the change was made
    """
    endpoint = "core/object-changes"

    # Make API call
    return netbox.get(endpoint, params=filters)

if __name__ == "__main__":
    # Load NetBox configuration from environment variables
    netbox_url = os.getenv("NETBOX_URL")
    netbox_token = os.getenv("NETBOX_TOKEN")

    if not netbox_url or not netbox_token:
        raise ValueError("NETBOX_URL and NETBOX_TOKEN environment variables must be set")

    # Initialize NetBox client
    netbox = NetBoxRestClient(url=netbox_url, token=netbox_token)

    mcp.run(transport="stdio")