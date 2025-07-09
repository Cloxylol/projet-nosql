from flask import Flask
from routes.points import points_bp

app = Flask(__name__)
app.register_blueprint(points_bp)

@app.route('/test', methods=['GET'])
def test_route():
    return {"message": "Tout fonctionne !"}, 200

if __name__ == '__main__':
    app.run(debug=True, port=8080)
