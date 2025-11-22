# https://www.codingforentrepreneurs.com/shorts/django-setup-for-use-in-jupyter-notebooks/
'''import os, sys

DJANGO_PROJECT = os.environ.get("DJANGO_PROJECT")
DJANGO_ROOT_DIR =  os.environ.get("DJANGO_ROOT_DIR")

PROJ_MISSING_MSG = """Set an enviroment variable:\n
`DJANGO_PROJECT=your_project_name`\n
or call:\n
`init_django(project_name=your_project_name)`
"""

def init_django(project_name=None):
    PWD = os.getcwd()
    if not PWD.endswith(f"/{DJANGO_ROOT_DIR}"):
    # src is the django-root
        PWD = os.path.join(PWD, DJANGO_ROOT_DIR)
    if PWD and PWD.endswith("src"):
        PWD = os.path.dirname(PWD)
    os.chdir(PWD)
    dj_project_name = project_name or DJANGO_PROJECT
    if dj_project_name == None:
        raise Exception(PROJ_MISSING_MSG)
    
    # FIXED: Use os.getcwd() instead of os.getenv('PWD') which returns None on Windows
    current_dir = os.getcwd()
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'{project_name}.settings')
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    import django
    django.setup()'''


import os, sys
PWD = os.path.dirname(os.getcwd())

PROJ_MISSING_MSG = """Set an enviroment variable:\n
`DJANGO_PROJECT=your_project_name`\n
or call:\n
`init_django(your_project_name)`
"""

def init_django(project_name=None):
    os.chdir(PWD)
    project_name = project_name or os.environ.get('DJANGO_PROJECT') or None
    if project_name == None:
        raise Exception(PROJ_MISSING_MSG)
    sys.path.insert(0, PWD)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'{project_name}.settings')
    os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"
    import django
    django.setup()