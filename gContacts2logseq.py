import os.path
import json
from pprint import pprint 
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from mdutils.mdutils import MdUtils


class md_person:
    def __init__(self, person) -> None:
        self.path = "/mnt/c/tmp/logseq/pages/People/"
        self.person = person
        self.name = f'{person["names"][0]["displayName"]}'
        self.md = MdUtils(file_name=f'{self.path}{self.name}.md')


    def md_print_name(self):
        if 'names' in self.person:
            self.md.new_header( level=1, title=f'[[{self.name}]]' )
            self.md.write(f'type:: google-contact\n')
            self.md.write(f'page-type:: google-contact\n')
            self.md.write(f'icon:: \n')

        else:
            pass

    def md_print_phones(self):
        if 'phoneNumbers' in self.person:
            for phone in self.person['phoneNumbers']:
                if 'canonicalForm' in phone:
                    if 'type' in phone:
                        self.md.write(f'{phone["type"]}-phone:: {phone["canonicalForm"]}\n')
                    else:
                        self.md.write(f'phone:: {phone["canonicalForm"]}\n')
                    

    def md_print_emails(self):
        if 'emailAddresses' in self.person:
            for email in self.person['emailAddresses']:
                if 'type' in email:
                    self.md.write(f'{email["type"]}-email:: {email["value"]}\n')
                else:
                    self.md.write(f'email:: {email["value"]}\n')

    def md_print_groups(self):
        if 'memberships' in self.person:
            values = list()
            for membership in self.person['memberships']:
                id = membership["contactGroupMembership"]["contactGroupResourceName"]
                if  id == "contactGroups/myContacts":
                    continue
                values.append(f'[[{groups[id]}]]')

            gs = ", ".join(values)
            if (gs != ""):
                self.md.write(f'group:: {gs}\n')

    def print(self):
        self.md_print_name()
        self.md_print_phones()
        self.md_print_emails()
        self.md_print_groups()
        print(self.md.get_md_text())

    def write(self):
        self.md.create_md_file()



# https://developers.google.com/people/quickstart/python


# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/contacts.readonly']

"""Shows basic usage of the People API.
Prints the name of the first 10 connections.
"""

def login():
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds


def populate_groups(service):
    groups = service.contactGroups().list().execute()
    g=dict()
    for group in groups['contactGroups']:
        g.__setitem__(group['resourceName'],group['formattedName'])

    pprint(g)
    return g


try:
    peoples = []


    creds = login()

    service = build('people', 'v1', credentials=creds)

    global groups
    groups = populate_groups(service)

    results = service.people().connections().list(
        resourceName='people/me',
        pageSize=300,
        personFields='names,phoneNumbers,emailAddresses,memberships',
        sortOrder='LAST_NAME_ASCENDING').execute()
    connections = results.get('connections', [])

    index_md = MdUtils(file_name="/mnt/c/tmp/logseq/pages/People/People.md")
    for person in connections:
        #print(json.dumps(person, indent=4, ensure_ascii=False))
#        pprint(person)
#        index_md.new_header( level=1, title=f'[[{person["names"][0]["displayName"]}]]' )
        p = md_person(person)
        p.print()
        p.write()
#        print("===================================")
        names = person.get('names', [])
        if names:
            name = names[0].get('displayName')
            try:
                peoples.append(name)
            except:
                pass

    #print(index_md.get_md_text())
    index_md.create_md_file()

    peoples.sort()

#    pprint(people)

    #md = MdUtils(file_name="People.md")

    #for people in peoples:
        #md.new_paragraph(f'[[{people}]]')
        #smd.new_header(level=1,title=f'[[{people}]]')
#        print(people)

#    md.create_md_file()


except HttpError as err:
    print(err)