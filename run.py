from app import create_app

app = create_app()

if __name__ == '__main__':
    # debug=True means the server will auto-restart when you save changes!
    app.run(debug=True)