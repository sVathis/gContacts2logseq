"""Module for storing user-defined config values."""

from pathlib import Path

"""Paths & Directories"""
LOGSEQ_ROOT_DIR = "C:/Your/Logseq/Directory"  # Path to your Logseq directory
LOGSEQ_CONTACTS_DIR = (
    LOGSEQ_ROOT_DIR + "/pages/Contacts/"
)  # Path where pages from Google Contacts will be generated
LOGSEQ_CONTACTS_INDEX_FILE = (
    LOGSEQ_CONTACTS_DIR + "Contacts.md"
)  # Path of the index file for your Google Contacts
