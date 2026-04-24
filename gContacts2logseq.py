import json
import logging
import os
import signal
import sys
import time

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/user.addresses.read",
]

_shutdown = False


def _handle_sigterm(signum, frame):
    global _shutdown
    log.info("SIGTERM received, shutting down after current sync")
    _shutdown = True


signal.signal(signal.SIGTERM, _handle_sigterm)


def load_config() -> dict:
    contacts_dir = os.environ.get("LOGSEQ_CONTACTS_DIR")
    if not contacts_dir:
        raise RuntimeError("LOGSEQ_CONTACTS_DIR environment variable is required")
    contacts_dir = os.path.join(contacts_dir, "")
    return {
        "contacts_dir": contacts_dir,
        "index_file": os.path.join(contacts_dir, "Contacts.md"),
        "token_file": os.environ.get("TOKEN_FILE", "token.json"),
        "credentials_file": os.environ.get("CREDENTIALS_FILE", "credentials.json"),
    }


class md_person:
    def __init__(self, person: dict, groups: dict, contacts_dir: str) -> None:
        self.person = person
        self.groups_map = groups
        self.path = contacts_dir

        if "names" in person:
            self.name = person["names"][0]["displayName"]
        elif "organizations" in person:
            self.name = person["organizations"][0]["name"]
        else:
            resource = person.get("resourceName", "unknown")
            raise ValueError(f"Contact {resource} has neither names nor organizations")

        self.file_name = os.path.join(self.path, f"{self.name}.md")
        self.buffer = ""

    def write(self, s):
        self.buffer += s

    def save(self):
        with open(self.file_name, "w") as f:
            f.write(self.buffer)

    def md_write_name(self):
        if "names" in self.person:
            self.write("exclude-from-graph-view:: true\n")
            self.write(f"title:: {self.name}\n")
            self.write("type:: [[Contact]]\n")
            self.write("page-type:: [[Contact]]\n")
            self.write("icon:: \U000f10be\n")

    def md_write_phones(self):
        if "phoneNumbers" in self.person:
            for phone in self.person["phoneNumbers"]:
                if "canonicalForm" in phone:
                    if "type" in phone:
                        self.write(f'phone.{phone["type"]}:: `{phone["canonicalForm"]}`\n')
                    else:
                        self.write(f'phone:: `{phone["canonicalForm"]}`\n')

    def md_write_emails(self):
        if "emailAddresses" in self.person:
            for email in self.person["emailAddresses"]:
                if "type" in email:
                    self.write(f'email.{email["type"]}:: `{email["value"]}`\n')
                else:
                    self.write(f'email:: `{email["value"]}`\n')

    def md_write_groups(self):
        if "memberships" in self.person:
            values = [
                f'[[Contact/{self.groups_map[m["contactGroupMembership"]["contactGroupResourceName"]]}]]'
                for m in self.person["memberships"]
                if m["contactGroupMembership"]["contactGroupResourceName"] != "contactGroups/myContacts"
                and m["contactGroupMembership"]["contactGroupResourceName"] in self.groups_map
            ]
            gs = ", ".join(values)
            self.groups = gs
            if gs:
                self.write(f"group:: {gs}\n")

    def md_write_link(self):
        if "resourceName" in self.person:
            self.write(
                f"url:: https://contacts.google.com/"
                f"{self.person['resourceName'].replace('people', 'person')}\n"
            )

    def md_write_job(self):
        if "organizations" not in self.person:
            return
        org = self.person["organizations"][0]
        if "title" in org:
            self.jobtitle = f"[[{org['title']}]]"
            self.write(f"job.title:: {self.jobtitle}\n")
        if "name" in org:
            self.company = f"[[{org['name']}]]"
            self.write(f"company:: {self.company}\n")

    def md_write_tags(self):
        tags_list = ["[[Contact]]"]
        if hasattr(self, "groups") and self.groups:
            tags_list.append(self.groups)
        if hasattr(self, "company"):
            tags_list.append(self.company)
        if hasattr(self, "jobtitle"):
            tags_list.append(self.jobtitle)
        self.write(f'tags:: {", ".join(tags_list)}\n')

    def md_write_notes(self):
        if "biographies" in self.person:
            self.write(f'{self.person["biographies"][0]["value"]}\n')

    def md_write_addresses(self):
        if "addresses" in self.person:
            for address in self.person["addresses"]:
                if "formattedValue" in address:
                    a = address["formattedValue"].replace("\n", ", ")
                    map_iframe = (
                        f'<iframe src="https://www.google.com/maps?q={a}&output=embed"'
                        f' frameborder="0" style="border:0"></iframe>'
                    )
                    if "type" in address:
                        self.write(f'address.{address["type"]}:: `{a}`\n')
                        self.write(f'map.{address["type"]}:: {map_iframe}\n')
                    else:
                        self.write(f"address:: `{a}`\n")
                        self.write(f"map:: {map_iframe}\n")

    def write_all(self):
        self.write("\n\n")
        self.md_write_name()
        self.md_write_job()
        self.md_write_groups()
        self.md_write_tags()
        self.md_write_phones()
        self.md_write_emails()
        self.md_write_notes()
        self.md_write_link()
        self.md_write_addresses()


# https://developers.google.com/people/quickstart/python
def login(config: dict) -> Credentials:
    creds = None
    token_path = config["token_file"]
    if os.path.exists(token_path):
        with open(token_path, "r") as token:
            creds = Credentials.from_authorized_user_info(json.load(token), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as token:
                token.write(creds.to_json())
        else:
            log.info("No valid token found — starting OAuth flow on port 8080")
            log.info("Open the URL below in your browser to authorize:")
            flow = InstalledAppFlow.from_client_secrets_file(
                config["credentials_file"], SCOPES
            )
            creds = flow.run_local_server(
                port=8080,
                authorization_prompt_message="\n{url}\n",
                open_browser=False,
            )
            with open(token_path, "w") as token:
                token.write(creds.to_json())
            log.info("Authorization complete — token saved to %s", token_path)
    return creds


def populate_groups(service) -> dict:
    result = service.contactGroups().list().execute()
    return {g["resourceName"]: g["formattedName"] for g in result["contactGroups"]}


def fetch_all_contacts(service) -> list:
    connections, page_token = [], None
    while True:
        kwargs = dict(
            resourceName="people/me",
            pageSize=1000,
            personFields=(
                "names,phoneNumbers,emailAddresses,memberships,"
                "metadata,organizations,addresses,biographies"
            ),
            sortOrder="LAST_NAME_ASCENDING",
        )
        if page_token:
            kwargs["pageToken"] = page_token
        result = service.people().connections().list(**kwargs).execute()
        connections.extend(result.get("connections", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    log.info("Fetched %d contacts", len(connections))
    return connections


def run_sync(config: dict, service, groups: dict) -> None:
    connections = fetch_all_contacts(service)
    index_md = []

    for person in connections:
        if "names" in person:
            index_md.append(f'# [[{person["names"][0]["displayName"]}]]\n')
        elif "organizations" in person:
            index_md.append(f'# [[{person["organizations"][0]["name"]}]]\n')

        try:
            p = md_person(person, groups, config["contacts_dir"])
        except ValueError as e:
            log.warning("Skipping contact: %s", e)
            continue

        p.write_all()

        existing_md = ""
        if os.path.exists(p.file_name):
            with open(p.file_name, "r") as f:
                existing_md = f.read()
            if p.buffer != existing_md:
                log.info("%s modified", p.name)
                p.save()
        else:
            log.info("%s added", p.name)
            p.save()

    with open(config["index_file"], "w") as index_md_file:
        index_md_file.write("icon:: \U000f10be\n")
        index_md_file.writelines(index_md)

    log.info("Sync complete: %d contacts written", len(connections))


def main():
    config = load_config()
    creds = login(config)
    service = build("people", "v1", credentials=creds)
    groups = populate_groups(service)

    interval = int(os.environ.get("SYNC_INTERVAL_SECONDS", "3600"))

    while True:
        try:
            run_sync(config, service, groups)
        except HttpError as e:
            log.error("Google API error: %s", e)
        except Exception:
            log.exception("Sync failed, will retry next interval")

        if interval == 0:
            break

        log.info("Next sync in %d seconds", interval)
        for _ in range(interval):
            if _shutdown:
                log.info("Shutting down")
                sys.exit(0)
            time.sleep(1)


if __name__ == "__main__":
    main()
