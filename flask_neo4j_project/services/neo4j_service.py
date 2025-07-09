def get_shortest_path(tx, start_id, end_id):
    query_ids = """
    MATCH (start:Point {id: $start_id}), (end:Point {id: $end_id})
    RETURN id(start) AS startNodeId, id(end) AS endNodeId
    """
    record = tx.run(query_ids, start_id=start_id, end_id=end_id).single()
    if not record:
        return None

    start_node_id = record["startNodeId"]
    end_node_id = record["endNodeId"]

    query_path = """
    CALL gds.shortestPath.dijkstra.stream({
        nodeProjection: 'Point',
        relationshipProjection: {
            ROUTE: {
                type: 'ROUTE',
                properties: 'distance',
                orientation: 'UNDIRECTED'
            }
        },
        startNode: $startNodeId,
        endNode: $endNodeId,
        relationshipWeightProperty: 'distance'
    })
    YIELD index, sourceNode, targetNode, totalCost, nodeIds
    RETURN [nodeId IN nodeIds | gds.util.asNode(nodeId).id] AS path, totalCost
    """
    result = tx.run(query_path, startNodeId=start_node_id, endNodeId=end_node_id)
    return result.single()

def get_surrounding_routes(tx, node_id):
    query = """
    MATCH (p:Point {id: $node_id})-[r:ROUTE]-(other:Point)
    RETURN other.id AS neighbor_id, r.distance AS distance, r.Name AS name
    """
    result = tx.run(query, node_id=node_id)
    return [record.data() for record in result]
