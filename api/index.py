import os
import sys
import urllib.parse

# Add project root directory to Python path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app import app as flask_app

class VercelPathFix:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        query_string = environ.get('QUERY_STRING', '')
        # Check if rewrite passed the original matched path via __path__
        if '__path__' in query_string:
            params = urllib.parse.parse_qs(query_string, keep_blank_values=True)
            if '__path__' in params and params['__path__']:
                req_path = params['__path__'][0]
                if not req_path.startswith('/'):
                    req_path = '/' + req_path
                environ['PATH_INFO'] = req_path
                # Remove __path__ so the Flask application doesn't see internal rewrite params
                params.pop('__path__', None)
                environ['QUERY_STRING'] = urllib.parse.urlencode(params, doseq=True)
        else:
            path_info = environ.get('PATH_INFO', '')
            if path_info in ('/api/index', '/api/index.py', '/api/index/', '/api') or path_info.startswith('/api/index'):
                original_path = (
                    environ.get('HTTP_X_MATCHED_PATH') or
                    environ.get('HTTP_X_FORWARDED_URI') or
                    environ.get('HTTP_X_ORIGINAL_URI') or
                    environ.get('REQUEST_URI')
                )
                if original_path and not original_path.startswith('/api/index'):
                    clean_path = original_path.split('?')[0]
                    environ['PATH_INFO'] = clean_path if clean_path else '/'
                else:
                    environ['PATH_INFO'] = '/'

        return self.wsgi_app(environ, start_response)

app = VercelPathFix(flask_app)
