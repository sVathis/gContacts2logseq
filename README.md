# gContacts2logseq

One-way sync Google Contacts to logseq



## 

A Python script that uses [Google People API](https://developers.google.com/people/quickstart/python) to generate a `.md` file to be consumed by [logseq](https://logseq.com)


## Authentication
The first time you will run `gContacts2logseq` you will be asked to authorize this application to access your Google contacts. 

`gContacts2logseq` will print a URL that you need to copy/paste it to your browser and follow the instrucions from there.

When, the authentication flow has completed, you may close this window.


```
Please visit this URL to authorize this application: https://accounts.google.com/o/oauth2/auth?response_type=code&client_id=772680894138-om5gu5sbpjj8p2im9f6f1p30uc9u1j5l.apps.googleusercontent.com&redirect_uri=http%3A%2F%2Flocalhost%3A33599%2F&scope=https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fcontacts.readonly+https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuser.addresses.read&state=b2QYSUuv4Q0jmKjd4BzG2RCPe4Jmmg&code_challenge=dXmZdIenosQn7B2wgIt021LPKb77lNfSa1NSqRi_xsM&code_challenge_method=S256&access_type=offline
```



Periotically you may get the following error message when running `gContacts2logseq`:

```
('invalid_grant: Token has been expired or revoked.', {'error': 'invalid_grant', 'error_description': 'Token has been expired or revoked.'})
```

In this case you need delete the `token.json` file and rerun the authentication procedure, above.