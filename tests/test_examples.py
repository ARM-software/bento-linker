import pytest
import os
import subprocess

EXAMPLES_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(__file__),
        '../examples'))
EXAMPLES = []
for name in os.listdir(EXAMPLES_PATH):
    path = os.path.join(EXAMPLES_PATH, name)
    if os.path.isdir(path):
        EXAMPLES.append((name, path))
EXAMPLES = sorted(EXAMPLES)
EXAMPLES_IDS = list(zip(*EXAMPLES))[0]

def test_sanity():
    subprocess.check_call(['bento'])

def test_options():
    subprocess.check_call(['bento', 'options'])

@pytest.mark.parametrize('name, path', EXAMPLES, ids=EXAMPLES_IDS)
def test_boxes_scan(name, path):
    os.chdir(path)
    subprocess.check_call(['bento', 'boxes', '-B', '-L'])

@pytest.mark.parametrize('name, path', EXAMPLES, ids=EXAMPLES_IDS)
def test_boxes_box(name, path):
    os.chdir(path)
    subprocess.check_call(['bento', 'boxes', '-L'])
    
@pytest.mark.parametrize('name, path', EXAMPLES, ids=EXAMPLES_IDS)
def test_boxes(name, path):
    os.chdir(path)
    subprocess.check_call(['bento', 'boxes'])

@pytest.mark.parametrize('name, path', EXAMPLES, ids=EXAMPLES_IDS)
def test_hooks(name, path):
    os.chdir(path)
    subprocess.check_call(['bento', 'hooks'])

@pytest.mark.parametrize('name, path', EXAMPLES, ids=EXAMPLES_IDS)
def test_links(name, path):
    os.chdir(path)
    subprocess.check_call(['bento', 'links'])

@pytest.mark.parametrize('name, path', EXAMPLES, ids=EXAMPLES_IDS)
def test_build(name, path):
    os.chdir(path)
    # build artifacts
    subprocess.check_call(['bento', 'build'])

@pytest.mark.parametrize('name, path', EXAMPLES, ids=EXAMPLES_IDS)
def test_build_make(name, path):
    os.chdir(path)
    # build artifacts
    subprocess.check_call(['bento', 'build'])
    # try to compile
    subprocess.check_call(['make', 'clean', 'build', 'CFLAGS+=-Werror'])

@pytest.mark.parametrize('name, path', EXAMPLES, ids=EXAMPLES_IDS)
def test_build_make_nolto(name, path):
    os.chdir(path)
    # build artifacts
    subprocess.check_call(['bento', 'build', '--all.lto=false'])
    # try to compile
    subprocess.check_call(['make', 'clean', 'build', 'CFLAGS+=-Werror'])

@pytest.mark.parametrize('name, path', EXAMPLES, ids=EXAMPLES_IDS)
def test_build_make_debug(name, path):
    os.chdir(path)
    # build artifacts
    subprocess.check_call(['bento', 'build', '--all.debug=true'])
    # try to compile
    subprocess.check_call(['make', 'clean', 'build', 'CFLAGS+=-Werror'])