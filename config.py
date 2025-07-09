from neo4j import GraphDatabase

NEO4J_URI = "neo4j+s://87f62873.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "ZFtcPiMpPukiNASkJhXPsBwewscNFDG0xnm3VIp-wx4"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
