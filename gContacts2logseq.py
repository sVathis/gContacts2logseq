import os.path
import json
import difflib
from pprint import pprint
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from os.path import exists


class md_person:
    def __init__(self, person) -> None:
        self.path = logseq_contacts_dir
        self.person = person

        if "names" in person.keys():
            n = f'{person["names"][0]["displayName"]}'
        else:
            n = f'{person["organizations"][0]["name"]}'

        #        self.name = f'{person["names"][0]["displayName"]}'
        self.name = n
        self.file_name = f"{self.path}{self.name}.md"
        self.buffer = ""

    def write(self, s):
        self.buffer += s

    def save(self):
        with open(self.file_name, "w") as f:
            f.write(self.buffer)
            f.close()

    def md_write_name(self):
        if "names" in self.person:
            self.write("exclude-from-graph-view:: true\n")
            self.write(f"title:: {self.name}\n")
            self.write(f"type:: [[Contact]]\n")
            self.write(f"page-type:: [[Contact]]\n")
            # self.write(f'icon:: \n') #People icon
            self.write(f"icon:: 󱂾\n")  # Contact icon

    def md_write_phones(self):
        if "phoneNumbers" in self.person:
            for phone in self.person["phoneNumbers"]:
                if "canonicalForm" in phone:
                    if "type" in phone:
                        self.write(
                            f'phone.{phone["type"]}:: `{phone["canonicalForm"]}`\n'
                        )
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
            values = list()
            for membership in self.person["memberships"]:
                id = membership["contactGroupMembership"]["contactGroupResourceName"]
                if id != "contactGroups/myContacts":
                    values.append(f"[[Contact/{groups[id]}]]")
            gs = ", ".join(values)
            self.groups = gs
            if gs != "":
                self.write(f"group:: {gs}\n")

    def md_write_link(self):
        if "resourceName" in self.person:
            self.write(
                f"url:: https://contacts.google.com/{self.person['resourceName'].replace('people','person')}\n"
            )

    def md_write_job(self):
        if "organizations" in self.person:
            org = self.person["organizations"][0]
            jobs = list()
            if "title" in org:
                #                jobs.append(f"[[{org['title']}]]")
                jobtitle = f"[[{org['title']}]]"
                self.jobtitle = jobtitle
                self.write(f"job.title:: {jobtitle}\n")
            if "name" in org:
                # jobs.append(f"[[{org['name']}]]")
                company = f"[[{org['name']}]]"
                self.company = company
                self.write(f"company:: {company}\n")
            j = ",".join(jobs)
            self.jobs = j
            if j != "":
                self.write(f"jobs:: {j}\n")

    def md_write_tags(self):
        g = hasattr(self, "groups")
        j = hasattr(self, "jobtitle")
        c = hasattr(self, "company")

        tags_list = ["[[Contact]]"]
        if g and self.groups != "":
            tags_list.append(self.groups)
        if c:
            tags_list.append(self.company)
        if j:
            tags_list.append(self.jobtitle)

        tags = ", ".join(tags_list)

        self.write(f"tags:: {tags}\n")

    def md_write_notes(self):
        if "biographies" in self.person:
            self.write(f'{self.person["biographies"][0]["value"]}\n')

    def md_write_addresses(self):
        if "addresses" in self.person:
            for address in self.person["addresses"]:
                if "formattedValue" in address:
                    a = address["formattedValue"].replace("\n", ", ")
                    map_iframe = f'<iframe src="https://www.google.com/maps?q={a}&output=embed" frameborder="0" style="border:0"></iframe>'
                    if "type" in address:
                        self.write(f'address.{address["type"]}:: `{a}`\n')
                        self.write(f'map.{address["type"]}:: {map_iframe}\n')
                    else:
                        self.write(f"address:: `{a}`\n")
                        self.write(f"map:: {map_iframe}\n")

    def write_all(self):
        # Logseq requires a double newline on the begining of each .md file
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

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/contacts.readonly",
    "https://www.googleapis.com/auth/user.addresses.read",
]


def login():
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=8081, open_browser=False)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def populate_groups(service):
    groups = service.contactGroups().list().execute()
    g = dict()
    for group in groups["contactGroups"]:
        g.__setitem__(group["resourceName"], group["formattedName"])

    #    pprint(g)
    return g


# try:
creds = login()

service = build("people", "v1", credentials=creds)

global groups
groups = populate_groups(service)

results = (
    service.people()
    .connections()
    .list(
        resourceName="people/me",
        pageSize=300,
        personFields="names,phoneNumbers,emailAddresses,memberships,metadata,organizations,addresses,biographies,addresses",
        sortOrder="LAST_NAME_ASCENDING",
    )
    .execute()
)
connections = results.get("connections", [])

index_md = list()

for person in connections:

    if "names" in person.keys():
        index_md_entry = f'# [[{person["names"][0]["displayName"]}]]\n'
    else:
        index_md_entry = f'# [[{person["organizations"][0]["name"]}]]\n'

    index_md.append(index_md_entry)

    p = md_person(person)
    p.write_all()

    existing_md = ""
    if exists(p.file_name):
        with open(p.file_name, "r") as f:
            #                print(f"Reading {p.file_name}")
            existing_md = f.read()
            f.close()

        if p.buffer != existing_md:
            # Compare the strings
            differences = []
            for c1, c2 in zip(existing_md, p.buffer):
                if c1 != c2:
                    differences.append((c1, c2))

            # Print out the differences
            if len(differences) > 0:
                print(f"{p.name} modified")
                p.save()

    #                    for d in differences:
    #                        print(d[0], "->", d[1])
    #            else:
    #                print(f"{p.name} unchanged")
    else:
        print(f"{p.name} added")
        p.save()


with open(logseq_contacts_index_file, "w") as index_md_file:
    # index_md_file.write(f'icon:: \n') #People icon
    index_md_file.write(f"icon:: 󱂾\n")  # Contact icon
    index_md_file.writelines(index_md)
    index_md_file.close()

# except Exception as err:
#    print(err)
