import pytest
import subprocess

def test_sanity():
    subprocess.check_call(['bento'])

def test_options():
    subprocess.check_call(['bento', 'options'])

def test_runtimes():
    subprocess.check_call(['bento', 'runtimes'])

def test_loaders():
    subprocess.check_call(['bento', 'loaders'])

def test_errors():
    subprocess.check_call(['bento', 'errors'])

