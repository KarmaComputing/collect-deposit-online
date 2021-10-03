from app.app import app
from livereload import Server

if __name__ == '__main__':
    app.debug = 1
    server = Server(app.wsgi_app)
    server.serve()
else:
  application = app
