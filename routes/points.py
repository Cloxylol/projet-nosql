from flask import Blueprint, request, jsonify
from config import driver
import networkx as nx

points_bp = Blueprint('points', __name__)

def build_graph_from_neo4j():
    G = nx.Graph()
    with driver.session() as session:
        # Récupérer tous les noeuds Point (id)
        nodes = session.run("MATCH (p:Point) RETURN p.id AS id")
        for record in nodes:
            G.add_node(record["id"])

        # Récupérer toutes les relations ROUTE avec la distance
        edges = session.run("MATCH (a:Point)-[r:ROUTE]-(b:Point) RETURN a.id AS from, b.id AS to, r.distance AS dist")
        for record in edges:
            G.add_edge(record["from"], record["to"], weight=record["dist"])

    return G

@points_bp.route("/nodes", methods=["GET"])
def list_nodes():
    with driver.session() as session:
        result = session.run("MATCH (p:Point) RETURN p.id AS id, p.lat AS lat, p.lon AS lon")
        nodes = [{"id": record["id"], "lat": record["lat"], "lon": record["lon"]} for record in result]
    return jsonify(nodes)

@points_bp.route('/routes-around/<int:node_id>', methods=['GET'])
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

@points_bp.route('/shortest-path', methods=['GET'])
def shortest_path():
    start_id = request.args.get('start', type=int)
    end_id = request.args.get('end', type=int)

    if start_id is None or end_id is None:
        return jsonify({"error": "Paramètres 'start' et 'end' requis"}), 400

    try:
        G = build_graph_from_neo4j()
        path = nx.dijkstra_path(G, start_id, end_id, weight='weight')
        total_cost = nx.dijkstra_path_length(G, start_id, end_id, weight='weight')
        return jsonify({
            "path": path,
            "totalCost": total_cost
        })
    except nx.NetworkXNoPath:
        return jsonify({"error": "Aucun chemin trouvé entre ces points"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# T'as toujours la fonction get_surrounding_routes à définir ou migrer si besoin
def get_surrounding_routes(tx, node_id):
    query = """
    MATCH (p:Point {id: $node_id})-[r:ROUTE]-(other:Point)
    RETURN other.id AS neighbor_id, r.distance AS distance, r.Name AS name
    """
    result = tx.run(query, node_id=node_id)
    return [record.data() for record in result]

from flask import Blueprint, request, jsonify
from config import driver

points_bp = Blueprint('points', __name__)

### ----------------- CREATE -----------------
@points_bp.route('/points', methods=['POST'])
def create_point():
    data = request.get_json()
    if not data or 'id' not in data or 'lat' not in data or 'lon' not in data:
        return jsonify({"error": "Champs requis : id, lat, lon"}), 400

    query = """
    CREATE (p:Point {id: $id, lat: $lat, lon: $lon})
    RETURN p
    """
    with driver.session() as session:
        try:
            session.run(query, id=data['id'], lat=data['lat'], lon=data['lon'])
            return jsonify({"message": "Point créé avec succès"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500

### ----------------- READ -----------------
@points_bp.route('/points/<int:point_id>', methods=['GET'])
def get_point(point_id):
    query = "MATCH (p:Point {id: $id}) RETURN p.id AS id, p.lat AS lat, p.lon AS lon"
    with driver.session() as session:
        record = session.run(query, id=point_id).single()
        if record:
            return jsonify(record.data())
        else:
            return jsonify({"error": "Point non trouvé"}), 404

### ----------------- UPDATE -----------------
@points_bp.route('/points/<int:point_id>', methods=['PUT'])
def update_point(point_id):
    data = request.get_json()
    updates = []
    if 'lat' in data:
        updates.append("p.lat = $lat")
    if 'lon' in data:
        updates.append("p.lon = $lon")

    if not updates:
        return jsonify({"error": "Aucune donnée à mettre à jour"}), 400

    query = f"""
    MATCH (p:Point {{id: $id}})
    SET {', '.join(updates)}
    RETURN p
    """
    with driver.session() as session:
        result = session.run(query, id=point_id, lat=data.get('lat'), lon=data.get('lon')).single()
        if result:
            return jsonify({"message": "Point mis à jour"}), 200
        else:
            return jsonify({"error": "Point non trouvé"}), 404

### ----------------- DELETE -----------------
@points_bp.route('/points/<int:point_id>', methods=['DELETE'])
def delete_point(point_id):
    query = "MATCH (p:Point {id: $id}) DETACH DELETE p"
    with driver.session() as session:
        try:
            session.run(query, id=point_id)
            return jsonify({"message": "Point supprimé"}), 200
        except Exception as e:
            return jsonify({"error": str(e)}), 500
