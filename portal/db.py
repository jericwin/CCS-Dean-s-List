"""Pooled MySQL access with small, explicit helpers.

Every helper borrows a connection from the pool and returns it when done, so the
helpers are safe to call from HTTP requests and Socket.IO handlers alike.
"""
import threading
from contextlib import contextmanager

import mysql.connector
from mysql.connector import pooling
from flask import current_app

DatabaseError = mysql.connector.Error
IntegrityError = mysql.connector.IntegrityError

_pools = {}
_lock = threading.Lock()


def _connection_settings(app):
    cfg = app.config
    return {
        "host": cfg["DB_HOST"],
        "port": cfg["DB_PORT"],
        "user": cfg["DB_USER"],
        "password": cfg["DB_PASSWORD"],
        "database": cfg["DB_NAME"],
        "charset": "utf8mb4",
        "collation": "utf8mb4_general_ci",
        "autocommit": False,
    }


def _get_pool():
    app = current_app._get_current_object()
    key = (app.config["DB_HOST"], app.config["DB_PORT"], app.config["DB_NAME"])
    pool = _pools.get(key)
    if pool is None:
        with _lock:
            pool = _pools.get(key)
            if pool is None:
                pool = pooling.MySQLConnectionPool(
                    pool_name=f"portal_{len(_pools)}",
                    pool_size=app.config["DB_POOL_SIZE"],
                    pool_reset_session=True,
                    **_connection_settings(app),
                )
                _pools[key] = pool
    return pool


def get_connection():
    conn = _get_pool().get_connection()
    try:
        conn.ping(reconnect=True, attempts=2, delay=0)
    except DatabaseError:
        conn.close()
        raise
    return conn


@contextmanager
def transaction():
    """Yield a dictionary cursor inside a transaction that commits on success."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def fetch_all(sql, params=()):
    with transaction() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def fetch_one(sql, params=()):
    with transaction() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        cur.fetchall()  # drain any remaining rows so the connection is reusable
        return row


def fetch_value(sql, params=(), default=0):
    row = fetch_one(sql, params)
    if not row:
        return default
    value = next(iter(row.values()))
    return default if value is None else value


def execute(sql, params=()):
    """Run a write statement; returns (lastrowid, rowcount)."""
    with transaction() as cur:
        cur.execute(sql, params)
        return cur.lastrowid, cur.rowcount
