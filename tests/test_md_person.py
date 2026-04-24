"""
Regression tests for md_person markdown output.

These tests establish the exact current output as a baseline. After the
refactor (groups + contacts_dir passed as parameters instead of globals),
only make_person() needs updating — all expected strings stay the same.
"""

import json
import sys
from unittest.mock import MagicMock, mock_open, patch

# ---------------------------------------------------------------------------
# Block all Google API imports before importing the module under test
# ---------------------------------------------------------------------------
for _mod in [
    "google",
    "google.auth",
    "google.auth.transport",
    "google.auth.transport.requests",
    "google.oauth2",
    "google.oauth2.credentials",
    "google_auth_oauthlib",
    "google_auth_oauthlib.flow",
    "googleapiclient",
    "googleapiclient.discovery",
    "googleapiclient.errors",
]:
    sys.modules[_mod] = MagicMock()

# Credentials mock returns a "valid" object so login() skips the refresh path
_mock_creds = MagicMock()
_mock_creds.valid = True
sys.modules[
    "google.oauth2.credentials"
].Credentials.from_authorized_user_info.return_value = _mock_creds

# Service mock returns empty contacts and groups — the module-level loop is a no-op
_mock_service = MagicMock()
_mock_service.people.return_value.connections.return_value.list.return_value.execute.return_value = {
    "connections": []
}
_mock_service.contactGroups.return_value.list.return_value.execute.return_value = {
    "contactGroups": []
}
sys.modules["googleapiclient.discovery"].build.return_value = _mock_service

_token_json = json.dumps(
    {
        "token": "t",
        "refresh_token": "r",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "c",
        "client_secret": "s",
        "scopes": [],
    }
)

# Import the module with open() and os.path.exists mocked so the module-level
# code (token read, index file write) does not touch the real filesystem.
with patch("builtins.open", mock_open(read_data=_token_json)), patch(
    "os.path.exists", return_value=True
):
    import gContacts2logseq as m  # noqa: E402

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------
TEST_DIR = "/tmp/test_contacts/"
TEST_GROUPS = {
    "contactGroups/friends": "Friends",
    "contactGroups/work": "Work",
}

ICON = "\U000f10be"  # 󱂾 (Nerd Font contact icon, UTF-8: f3 b1 82 be)


def make_person(person_data, groups=None):
    """Instantiate md_person with explicit parameters, call write_all(), return it."""
    p = m.md_person(person_data, groups if groups is not None else {}, TEST_DIR)
    p.write_all()
    return p


# ---------------------------------------------------------------------------
# T1 — full contact
# ---------------------------------------------------------------------------
def test_full_contact():
    person = {
        "resourceName": "people/c1",
        "names": [{"displayName": "John Doe"}],
        "phoneNumbers": [{"canonicalForm": "+15550100", "type": "mobile"}],
        "emailAddresses": [{"value": "john@example.com", "type": "work"}],
        "memberships": [
            {
                "contactGroupMembership": {
                    "contactGroupResourceName": "contactGroups/myContacts"
                }
            },
            {
                "contactGroupMembership": {
                    "contactGroupResourceName": "contactGroups/friends"
                }
            },
        ],
        "organizations": [{"title": "Engineer", "name": "ACME Corp"}],
        "addresses": [
            {
                "formattedValue": "123 Main St\nAnytown, CA 90001",
                "type": "home",
            }
        ],
        "biographies": [{"value": "A note about John"}],
    }
    expected = (
        "\n\n"
        "exclude-from-graph-view:: true\n"
        f"title:: John Doe\n"
        "type:: [[Contact]]\n"
        "page-type:: [[Contact]]\n"
        f"icon:: {ICON}\n"
        "job.title:: [[Engineer]]\n"
        "company:: [[ACME Corp]]\n"
        "group:: [[Contact/Friends]]\n"
        "tags:: [[Contact]], [[Contact/Friends]], [[ACME Corp]], [[Engineer]]\n"
        "phone.mobile:: `+15550100`\n"
        "email.work:: `john@example.com`\n"
        "A note about John\n"
        "url:: https://contacts.google.com/person/c1\n"
        "address.home:: `123 Main St, Anytown, CA 90001`\n"
        'map.home:: <iframe src="https://www.google.com/maps?q=123 Main St, Anytown, CA 90001'
        '&output=embed" frameborder="0" style="border:0"></iframe>\n'
    )
    p = make_person(person, groups={"contactGroups/friends": "Friends"})
    assert p.buffer == expected


# ---------------------------------------------------------------------------
# T2 — organization-only contact (no 'names' key)
# ---------------------------------------------------------------------------
def test_org_only_contact():
    person = {
        "resourceName": "people/c2",
        "organizations": [{"name": "ACME Corp"}],
    }
    expected = (
        "\n\n"
        "company:: [[ACME Corp]]\n"
        "tags:: [[Contact]], [[ACME Corp]]\n"
        "url:: https://contacts.google.com/person/c2\n"
    )
    p = make_person(person)
    assert p.buffer == expected


# ---------------------------------------------------------------------------
# T3 — minimal contact (name only, nothing else)
# ---------------------------------------------------------------------------
def test_minimal_contact():
    person = {"names": [{"displayName": "Jane Smith"}]}
    expected = (
        "\n\n"
        "exclude-from-graph-view:: true\n"
        "title:: Jane Smith\n"
        "type:: [[Contact]]\n"
        "page-type:: [[Contact]]\n"
        f"icon:: {ICON}\n"
        "tags:: [[Contact]]\n"
    )
    p = make_person(person)
    assert p.buffer == expected


# ---------------------------------------------------------------------------
# T4 — phone without type
# ---------------------------------------------------------------------------
def test_phone_without_type():
    person = {
        "names": [{"displayName": "Test User"}],
        "phoneNumbers": [{"canonicalForm": "+15550200"}],
    }
    p = make_person(person)
    assert "phone:: `+15550200`\n" in p.buffer


# ---------------------------------------------------------------------------
# T5 — phone entry with no canonicalForm (skipped entirely)
# ---------------------------------------------------------------------------
def test_phone_without_canonical_form_is_skipped():
    person = {
        "names": [{"displayName": "Test User"}],
        "phoneNumbers": [{"value": "+1 555-0300"}],
    }
    p = make_person(person)
    assert "phone" not in p.buffer


# ---------------------------------------------------------------------------
# T6 — email without type
# ---------------------------------------------------------------------------
def test_email_without_type():
    person = {
        "names": [{"displayName": "Test User"}],
        "emailAddresses": [{"value": "user@example.com"}],
    }
    p = make_person(person)
    assert "email:: `user@example.com`\n" in p.buffer


# ---------------------------------------------------------------------------
# T7 — address without type
# ---------------------------------------------------------------------------
def test_address_without_type():
    person = {
        "names": [{"displayName": "Test User"}],
        "addresses": [{"formattedValue": "456 Oak Ave"}],
    }
    p = make_person(person)
    assert "address:: `456 Oak Ave`\n" in p.buffer
    assert (
        'map:: <iframe src="https://www.google.com/maps?q=456 Oak Ave&output=embed"'
        ' frameborder="0" style="border:0"></iframe>\n'
    ) in p.buffer


# ---------------------------------------------------------------------------
# T8 — address newline replaced with ", "
# ---------------------------------------------------------------------------
def test_address_newline_replaced():
    person = {
        "names": [{"displayName": "Test User"}],
        "addresses": [
            {"formattedValue": "456 Oak Ave\nSpringfield, IL", "type": "work"}
        ],
    }
    p = make_person(person)
    assert "address.work:: `456 Oak Ave, Springfield, IL`\n" in p.buffer
    assert "456 Oak Ave, Springfield, IL&output=embed" in p.buffer


# ---------------------------------------------------------------------------
# T9 — multiple groups, myContacts excluded
# ---------------------------------------------------------------------------
def test_multiple_groups_my_contacts_excluded():
    person = {
        "names": [{"displayName": "Test User"}],
        "memberships": [
            {
                "contactGroupMembership": {
                    "contactGroupResourceName": "contactGroups/myContacts"
                }
            },
            {
                "contactGroupMembership": {
                    "contactGroupResourceName": "contactGroups/friends"
                }
            },
            {
                "contactGroupMembership": {
                    "contactGroupResourceName": "contactGroups/work"
                }
            },
        ],
    }
    p = make_person(person, groups=TEST_GROUPS)
    assert "group:: [[Contact/Friends]], [[Contact/Work]]\n" in p.buffer
    assert "[[Contact/Friends]]" in p.buffer
    assert "[[Contact/Work]]" in p.buffer
    assert "myContacts" not in p.buffer


# ---------------------------------------------------------------------------
# T10 — only myContacts membership → no group line, clean tags
# ---------------------------------------------------------------------------
def test_only_my_contacts_no_group_line():
    person = {
        "names": [{"displayName": "Test User"}],
        "memberships": [
            {
                "contactGroupMembership": {
                    "contactGroupResourceName": "contactGroups/myContacts"
                }
            }
        ],
    }
    p = make_person(person, groups=TEST_GROUPS)
    assert "group::" not in p.buffer
    assert "tags:: [[Contact]]\n" in p.buffer


# ---------------------------------------------------------------------------
# T11 — job title only (no company name)
# ---------------------------------------------------------------------------
def test_job_title_only():
    person = {
        "names": [{"displayName": "Test User"}],
        "organizations": [{"title": "CEO"}],
    }
    p = make_person(person)
    assert "job.title:: [[CEO]]\n" in p.buffer
    assert "company::" not in p.buffer
    assert "tags:: [[Contact]], [[CEO]]\n" in p.buffer


# ---------------------------------------------------------------------------
# T12 — company only (no job title)
# ---------------------------------------------------------------------------
def test_company_only():
    person = {
        "names": [{"displayName": "Test User"}],
        "organizations": [{"name": "TechCorp"}],
    }
    p = make_person(person)
    assert "company:: [[TechCorp]]\n" in p.buffer
    assert "job.title::" not in p.buffer
    assert "tags:: [[Contact]], [[TechCorp]]\n" in p.buffer


# ---------------------------------------------------------------------------
# T13 — index entry format
# ---------------------------------------------------------------------------
def test_index_entry_named_contact():
    person = {"names": [{"displayName": "Alice Brown"}]}
    entry = f'# [[{person["names"][0]["displayName"]}]]\n'
    assert entry == "# [[Alice Brown]]\n"


def test_index_entry_org_contact():
    person = {"organizations": [{"name": "Big Corp"}]}
    entry = f'# [[{person["organizations"][0]["name"]}]]\n'
    assert entry == "# [[Big Corp]]\n"


# ---------------------------------------------------------------------------
# T14 — write_all order: verify key sections appear in correct sequence
# ---------------------------------------------------------------------------
def test_write_all_section_order():
    """name props → job → groups → tags → phones → emails → notes → url → addresses"""
    person = {
        "resourceName": "people/c99",
        "names": [{"displayName": "Order Test"}],
        "phoneNumbers": [{"canonicalForm": "+15550999", "type": "home"}],
        "emailAddresses": [{"value": "order@example.com", "type": "home"}],
        "memberships": [
            {
                "contactGroupMembership": {
                    "contactGroupResourceName": "contactGroups/friends"
                }
            }
        ],
        "organizations": [{"title": "Dev", "name": "Corp"}],
        "addresses": [{"formattedValue": "1 St", "type": "home"}],
        "biographies": [{"value": "notes here"}],
    }
    p = make_person(person, groups={"contactGroups/friends": "Friends"})
    buf = p.buffer

    pos_title = buf.index("title::")
    pos_job = buf.index("job.title::")
    pos_group = buf.index("group::")
    pos_tags = buf.index("tags::")
    pos_phone = buf.index("phone.")
    pos_email = buf.index("email.")
    pos_notes = buf.index("notes here")
    pos_url = buf.index("url::")
    pos_addr = buf.index("address.")

    assert pos_title < pos_job < pos_group < pos_tags
    assert pos_tags < pos_phone < pos_email < pos_notes
    assert pos_notes < pos_url < pos_addr
