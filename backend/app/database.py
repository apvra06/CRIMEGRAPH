import logging
from neo4j import GraphDatabase, Driver
from app.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

logger = logging.getLogger("crime_analyst.database")

_driver: Driver | None = None


def get_driver() -> Driver:
    global _driver
    if _driver is None:
        try:
            _driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
            _driver.verify_connectivity()
            logger.info("Connected to Neo4j successfully at %s", NEO4J_URI)
        except Exception as e:
            logger.warning("Failed to connect to Neo4j at %s: %s", NEO4J_URI, e)
            _driver = None
            raise
    return _driver


def check_connection() -> bool:
    try:
        driver = get_driver()
        driver.verify_connectivity()
        return True
    except Exception:
        return False


def close_driver():
    global _driver
    if _driver is not None:
        try:
            _driver.close()
            logger.info("Closed Neo4j driver connection")
        except Exception as e:
            logger.error("Error closing Neo4j driver: %s", e)
        finally:
            _driver = None


def run_query(query: str, params: dict | None = None):
    driver = get_driver()
    with driver.session() as session:
        result = session.run(query, params or {})
        return [record.data() for record in result]


def run_query_raw(query: str, params: dict | None = None):
    driver = get_driver()
    with driver.session() as session:
        return list(session.run(query, params or {}))

