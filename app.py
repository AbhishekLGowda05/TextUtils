from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "PDF to Word Converter - Kannada"

if __name__ == "__main__":
    app.run(debug=True)
