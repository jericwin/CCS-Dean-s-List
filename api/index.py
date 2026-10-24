import os
import sys

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app
from flask import request, redirect

@app.route('/api/index.py')
@app.route('/api/index')
def vercel_entry():
    real_path = request.args.get('__path__', '/')
    query = request.query_string.decode('utf-8')
    return f"MATCHED VERCEL ENTRY! real_path={real_path} | raw_path={request.path} | query={query}"
