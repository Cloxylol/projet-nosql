from flask import Blueprint, request, jsonify
from config import driver
from services.neo4j_service import get_shortest_path, get_surrounding_routes

points_bp = Blueprint('points', __name__)

@points_bp.route('/shortest-path', methods=['GET'])
def shortest_path():
    start_id = request.args.get('start')
    end_id = request.args.get('end')
    if not start_id or not end_id:
        return jsonify({"error": "ID valide svp"}), 400

    with driver.session() as session:
        try:
            result = session.read_transaction(get_shortest_path, start_id, end_id)
            if result:
                return jsonify(result)
            else:
                return jsonify({"error": "Chemin introuvable"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

@points_bp.route("/nodes", methods=["GET"])
def list_nodes():
    with driver.session() as session:
        result = session.run("MATCH (p:Point) RETURN p.id AS id, p.lat AS lat, p.lon AS lon")
        nodes = [{"id": record["id"], "lat": record["lat"], "lon": record["lon"]} for record in result]
    return jsonify(nodes)

@points_bp.route('/routes-around/<node_id>', methods=['GET'])
def routes_around(node_id):
    with driver.session() as session:
        try:
            result = session.read_transaction(get_surrounding_routes, node_id)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
@points_bp.route('/subgraph', methods=['GET'])
def get_subgraph():
    start_id = request.args.get('start')
    end_id = request.args.get('end')
    if not start_id or not end_id:
        return jsonify({"error": "Paramètres 'start' et 'end' requis"}), 400

    query = """
    MATCH path = (start:Point {id: toInteger($start_id)})-[:ROUTE*1..3]-(end:Point {id: toInteger($end_id)})
    RETURN 
      [node IN nodes(path) | node.id] AS nodes,
      [rel IN relationships(path) | {
          from: startNode(rel).id,
          to: endNode(rel).id,
          name: rel.Name,
          distance: rel.distance
      }] AS routes
    LIMIT 1
    """

    with driver.session() as session:
        try:
            result = session.run(query, start_id=start_id, end_id=end_id).single()
            if result:
                return jsonify({
                    "nodes": result["nodes"],
                    "routes": result["routes"]
                })
            else:
                return jsonify({"error": "Aucun chemin trouvé entre les deux points"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500


@points_bp.route('/all-edges', methods=['GET'])
def all_edges():
    query = """
    MATCH ()-[r:ROUTE]->()
    RETURN startNode(r).id AS from, endNode(r).id AS to, r.Name AS name, r.distance AS distance
    """
    with driver.session() as session:
        try:
            result = session.run(query)
            edges = []
            for record in result:
                edges.append({
                    "from": record["from"],
                    "to": record["to"],
                    "name": record["name"],
                    "distance": record["distance"]
                })
            return jsonify(edges)
        except Exception as e:
            return jsonify({"error": str(e)}), 500
