#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MEXICANA TROUBLESHOOTING SYSTEM
Clean application with 10 essential pages for fleet maintenance and diagnostics.
"""

import threading as _threading
from config import Config
from routes_analytics import analytics_bp
from werkzeug.security import check_password_hash, generate_password_hash
import os
import json
import socket
import textwrap
from io import BytesIO
from datetime import date, datetime, timezone
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    jsonify, send_from_directory, session, Response, send_file
)
from werkzeug.exceptions import RequestEntityTooLarge

# Instala pymysql como MySQLdb para compatibilidade
import pymysql
pymysql.install_as_MySQLdb()

try:
    import MySQLdb
except ModuleNotFoundError:
    MySQLdb = pymysql

# flask_mysqldb espera close() idempotente (mysqlclient); no pymysql isso pode
# levantar "Already closed" durante teardown. Este patch evita falso erro.
_PYMYSQL_CLOSE = pymysql.connections.Connection.close


def _safe_pymysql_close(self):
    try:
        _PYMYSQL_CLOSE(self)
    except Exception as exc:
        if 'Already closed' not in str(exc):
            raise


pymysql.connections.Connection.close = _safe_pymysql_close

try:
    from flask_mysqldb import MySQL
except ModuleNotFoundError:
    class MySQL:  # type: ignore[override]
        """Fallback minimal MySQL wrapper using pymysql directly."""

        def __init__(self, app_instance):
            self.app = app_instance
            self._connection = None

        @property
        def connection(self):
            if self._connection is None:
                self._connection = pymysql.connect(
                    host=self.app.config.get('MYSQL_HOST', 'localhost'),
                    user=self.app.config.get('MYSQL_USER', 'root'),
                    password=self.app.config.get('MYSQL_PASSWORD', ''),
                    database=self.app.config.get(
                        'MYSQL_DB', 'troubleshooting_db'),
                    charset='utf8mb4',
                    cursorclass=MySQLdb.cursors.DictCursor,
                    connect_timeout=4,
                    autocommit=False,
                )
            return self._connection

        def reconnect(self):
            try:
                if self._connection is not None:
                    self._connection.close()
            except Exception:
                pass
            self._connection = None


# ========== CONFIGURATION ==========

# ========== FLASK APP SETUP ==========
app = Flask(__name__)
app.config.from_object(Config)
app.register_blueprint(analytics_bp)

# ── Phase 4: warm up V10 engine in background on first request ────────────
_engine_warmed = False
_offline_snapshot_synced = False


@app.before_request
def _warmup_v10_engine():
    global _engine_warmed, _offline_snapshot_synced
    if not _engine_warmed:
        _engine_warmed = True

        def _warm():
            try:
                from routes_analytics import get_v10_engine
                get_v10_engine()
            except Exception:
                pass
        _threading.Thread(target=_warm, daemon=True).start()

    if not _offline_snapshot_synced:
        _offline_snapshot_synced = True
        try:
            _sync_offline_snapshots_from_db()
        except Exception as exc:
            app.logger.warning('Offline snapshot sync failed: %s', exc)
# ─────────────────────────────────────────────────────────────────────────────


@app.after_request
def _disable_client_cache(response):
    """Force fresh assets/pages during troubleshooting UI iterations."""
    if request.method == 'GET':
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


# MySQL via flask_mysqldb
mysql = MySQL(app)

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def _safe_schema_name(value, default):
    """Allow only schema names composed of letters, numbers and underscore."""
    candidate = (value or '').strip()
    if candidate and all(ch.isalnum() or ch == '_' for ch in candidate):
        return candidate
    return default


TS_DB = _safe_schema_name(app.config.get('MYSQL_DB'), 'troubleshooting_db')
FLEET_DB = _safe_schema_name(app.config.get('FLEET_DB_NAME'), 'fleet_db')
MEL_DB = _safe_schema_name(app.config.get('MEL_DB_NAME'), 'mel_db')
ETD_DB = _safe_schema_name(app.config.get('ETD_DB_NAME'), 'etds_db')
FALLBACK_USERS_FILE = os.path.join(
    os.path.dirname(__file__), 'users_fallback.json')
FALLBACK_RECORDS_FILE = os.path.join(
    os.path.dirname(__file__), 'records_fallback.json')
FALLBACK_TAILS_FILE = os.path.join(
    os.path.dirname(__file__), 'tails_fallback.json')
FALLBACK_MEL_FILE = os.path.join(
    os.path.dirname(__file__), 'mel_fallback.json')
FALLBACK_AOG_FILE = os.path.join(
    os.path.dirname(__file__), 'aog_fallback.json')
FALLBACK_ETD_FILE = os.path.join(
    os.path.dirname(__file__), 'etd_fallback.json')
FALLBACK_LRU_FILE = os.path.join(
    os.path.dirname(__file__), 'lru_fallback.json')


def _default_fallback_users():
    now = datetime.now(timezone.utc).isoformat()
    return {
        'admin': {
            'id': 1,
            'username': 'admin',
            'password': generate_password_hash('admin123'),
            'email': 'admin@mexicana.com',
            'access_level': 'Admin',
            'created_at': now,
        },
        'technician': {
            'id': 2,
            'username': 'technician',
            'password': generate_password_hash('tech123'),
            'email': 'technician@mexicana.com',
            'access_level': 'Technician',
            'created_at': now,
        },
    }


def _load_fallback_users():
    default_users = _default_fallback_users()
    users = {}
    should_save = False

    if os.path.exists(FALLBACK_USERS_FILE):
        try:
            with open(FALLBACK_USERS_FILE, 'r', encoding='utf-8') as file_obj:
                raw_users = json.load(file_obj)
        except Exception as exc:
            app.logger.warning('Fallback users file read error: %s', exc)
            raw_users = {}
            should_save = True
    else:
        raw_users = {}
        should_save = True

    for username, raw_user in raw_users.items():
        if not isinstance(raw_user, dict):
            should_save = True
            continue

        normalized = dict(raw_user)
        if 'password' not in normalized and normalized.get('password_hash'):
            normalized['password'] = normalized.get('password_hash')
            should_save = True

        placeholder_hash = str(normalized.get('password', ''))
        if not placeholder_hash or 'PLACEHOLDER' in placeholder_hash:
            default_user = default_users.get(username)
            if default_user:
                normalized['password'] = default_user['password']
                should_save = True

        normalized.setdefault('username', username)
        normalized.setdefault('access_level', raw_user.get('role', 'User'))
        normalized.setdefault('id', len(users) + 1)
        users[username] = normalized

    for username, default_user in default_users.items():
        if username not in users:
            users[username] = default_user
            should_save = True

    if should_save:
        try:
            with open(FALLBACK_USERS_FILE, 'w', encoding='utf-8') as file_obj:
                json.dump(users, file_obj, indent=2)
        except Exception as exc:
            app.logger.warning('Fallback users file write error: %s', exc)

    return users


def get_auth_user(username):
    try:
        cursor = get_db_cursor()
        cursor.execute(
            "SELECT id, username, password, email, access_level FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        if user:
            user['auth_source'] = 'mysql'
            return user
    except (pymysql.OperationalError, pymysql.InterfaceError) as exc:
        app.logger.warning(
            'MySQL connection error in login, using fallback auth: %s', exc)
    except Exception as exc:
        app.logger.error(
            'DB error in login (%s), using fallback auth: %s', type(exc).__name__, exc)

    fallback_user = _load_fallback_users().get(username)
    if fallback_user:
        fallback_user = dict(fallback_user)
        fallback_user['auth_source'] = 'fallback'
    return fallback_user


def _default_fallback_records():
    return [
        {
            'id': 1001,
            'tail': 'PR-E2A',
            'modelo': 'E195-E2',
            'prioridade': 'High',
            'categoria': 'Avionics',
            'problema': 'FMS generated intermittent position mismatch during descent.',
            'ata': '34',
            'localizacao': 'Flight Deck',
            'tecnico_responsavel': 'J. Silva',
            'tempo_estimado_horas': 3.5,
            'status_atual': 'Open',
            'troubleshooting': 'Performed BITE test, checked GPS antenna connectors and wiring continuity.',
            'solucao': 'Awaiting replacement of GPS receiver for confirmation test.',
            'data_cadastro': '2026-03-18 09:15:00',
            'data_criacao': '2026-03-18 09:15:00',
            'criado_por': 'admin',
        },
        {
            'id': 1002,
            'tail': 'PR-E1B',
            'modelo': 'EMB190',
            'prioridade': 'Medium',
            'categoria': 'Hydraulic',
            'problema': 'Hydraulic system B low pressure observed during pushback.',
            'ata': '29',
            'localizacao': 'Main Gear Bay',
            'tecnico_responsavel': 'M. Costa',
            'tempo_estimado_horas': 2.0,
            'status_atual': 'In Progress',
            'troubleshooting': 'Inspected reservoir quantity and pressure line fittings. Minor seepage found.',
            'solucao': 'Replacing pressure line seal and performing leak check.',
            'data_cadastro': '2026-03-17 14:40:00',
            'data_criacao': '2026-03-17 14:40:00',
            'criado_por': 'technician',
        },
        {
            'id': 1003,
            'tail': 'PR-ERJ',
            'modelo': 'ERJ145',
            'prioridade': 'Low',
            'categoria': 'Mechanical',
            'problema': 'Cabin service door damping action below standard.',
            'ata': '52',
            'localizacao': 'Forward Entry Door',
            'tecnico_responsavel': 'A. Lima',
            'tempo_estimado_horas': 1.5,
            'status_atual': 'Closed',
            'troubleshooting': 'Lubricated hinges and inspected door damper for wear.',
            'solucao': 'Door damper adjusted and operation restored within limits.',
            'data_cadastro': '2026-03-16 08:10:00',
            'data_criacao': '2026-03-16 08:10:00',
            'criado_por': 'admin',
        },
        {
            'id': 1004,
            'tail': 'PR-E2C',
            'modelo': 'E190-E2',
            'prioridade': 'Critical',
            'categoria': 'Electrical',
            'problema': 'Left AC bus tripped during engine start sequence.',
            'ata': '24',
            'localizacao': 'Electrical Bay',
            'tecnico_responsavel': 'R. Nunes',
            'tempo_estimado_horas': 4.0,
            'status_atual': 'Pending Review',
            'troubleshooting': 'Inspected contactor, insulation resistance and starter-generator related feeder.',
            'solucao': 'Temporary reset successful. Root cause analysis pending engineering review.',
            'data_cadastro': '2026-03-15 18:25:00',
            'data_criacao': '2026-03-15 18:25:00',
            'criado_por': 'admin',
        },
    ]


def _json_load_list(file_path, default_factory):
    should_save = False
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file_obj:
                data = json.load(file_obj)
        except Exception as exc:
            app.logger.warning(
                'Offline file read error for %s: %s', file_path, exc)
            data = []
            should_save = True
    else:
        data = []
        should_save = True

    if not isinstance(data, list):
        data = default_factory()
        should_save = True

    if should_save:
        _json_save_list(file_path, data)
    return data


def _json_save_list(file_path, data):
    try:
        with open(file_path, 'w', encoding='utf-8') as file_obj:
            json.dump(data, file_obj, indent=2, default=str)
    except Exception as exc:
        app.logger.warning(
            'Offline file write error for %s: %s', file_path, exc)


def _default_tail_metrics():
    return [
        {'id': 1, 'tail': 'PR-E2A', 'serial': '19020001',
            'fh': 12840.5, 'fc': 8421, 'data_cadastro': '2026-03-18'},
        {'id': 2, 'tail': 'PR-E1B', 'serial': '19000078',
            'fh': 9821.0, 'fc': 7023, 'data_cadastro': '2026-03-17'},
        {'id': 3, 'tail': 'PR-ERJ', 'serial': '14500881',
            'fh': 15444.2, 'fc': 11098, 'data_cadastro': '2026-03-16'},
        {'id': 4, 'tail': 'PR-E2C', 'serial': '19020007',
            'fh': 6430.8, 'fc': 3888, 'data_cadastro': '2026-03-15'},
    ]


def _load_tail_metrics():
    rows = _json_load_list(FALLBACK_TAILS_FILE, _default_tail_metrics)
    normalized = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        item = dict(row)
        item.setdefault('id', index)
        item.setdefault('tail', '')
        item.setdefault('serial', '')
        item.setdefault('fh', 0)
        item.setdefault('fc', 0)
        item.setdefault('data_cadastro', date.today().isoformat())
        item['total_fh'] = _to_float(item.get('fh'))
        item['total_fc'] = _to_int(item.get('fc'))
        normalized.append(item)
    return normalized


def _save_tail_metrics(rows):
    _json_save_list(FALLBACK_TAILS_FILE, rows)


def _default_mel_items():
    return [
        {
            'id': 1,
            'date_opened': '2026-03-12',
            'tail': 'PR-E2A',
            'logbook': 'LB-23014',
            'system_inop': 'Weather radar antenna heater intermittent',
            'category': 'B',
            'ata': '34',
            'chapter': 'Navigation',
            'due_date': '2026-03-22',
            'date_closed': None,
            'notes': '[REPLACED ITEM] Heater relay\n[SOLUTION RESPONSE] Awaiting ops check after replacement.',
            'created_at': '2026-03-12 08:00:00',
        },
        {
            'id': 2,
            'date_opened': '2026-03-08',
            'tail': 'PR-E2C',
            'logbook': 'LB-23002',
            'system_inop': 'Galley chiller inoperative',
            'category': 'C',
            'ata': '25',
            'chapter': 'Equipment/Furnishings',
            'due_date': '2026-03-28',
            'date_closed': None,
            'notes': '',
            'created_at': '2026-03-08 14:10:00',
        },
        {
            'id': 3,
            'date_opened': '2026-03-01',
            'tail': 'PR-E1B',
            'logbook': 'LB-22970',
            'system_inop': 'Cabin reading light row 12A',
            'category': 'D',
            'ata': '33',
            'chapter': 'Lights',
            'due_date': '2026-03-10',
            'date_closed': '2026-03-05',
            'notes': '[SOLUTION RESPONSE] Lamp replaced and tested serviceable.',
            'created_at': '2026-03-01 11:45:00',
        },
    ]


def _load_mel_items():
    return _json_load_list(FALLBACK_MEL_FILE, _default_mel_items)


def _save_mel_items(rows):
    _json_save_list(FALLBACK_MEL_FILE, rows)


def _default_aog_items():
    return [
        {
            'id': 1,
            'date': '2026-03-19',
            'tail': 'PR-E2C',
            'interruption_type': 'AOG',
            'ata': '24',
            'fail_code': 'ELEC-ACB-L',
            'location': 'Electrical Bay',
            'event_description': 'Left AC bus trip during start.',
            'maintenance_actions': 'Inspected contactor and isolation wiring. Awaiting replacement unit.',
            'expected_return': '2026-03-21',
            'release_date': None,
        },
        {
            'id': 2,
            'date': '2026-03-11',
            'tail': 'PR-ERJ',
            'interruption_type': 'Operational Hold',
            'ata': '52',
            'fail_code': 'DOOR-DAMP',
            'location': 'Forward Entry Door',
            'event_description': 'Service door damping out of limits.',
            'maintenance_actions': 'Damper adjusted and lubricated.',
            'expected_return': '2026-03-12',
            'release_date': '2026-03-12',
        },
    ]


def _load_aog_items():
    return _json_load_list(FALLBACK_AOG_FILE, _default_aog_items)


def _save_aog_items(rows):
    _json_save_list(FALLBACK_AOG_FILE, rows)


def _default_etd_items():
    return [
        {
            'id': 1,
            'tail': 'PR-E2A',
            'serial': '19020001',
            'etrack': 'ETR-1045',
            'data_cadastro': '2026-03-14',
            'subject': 'FMS database mismatch follow-up',
            'hours_at_creation': 12830.4,
            'cycles_at_creation': 8413,
            'created_by': 'Engineering',
            'created_at': '2026-03-14 09:00:00',
            'attachment': None,
            'safety': 1,
            'hotline': 0,
            'systemas': 1,
            'estruturas': 0,
            'outros': 0,
            'etd_emitida': 'NO',
        },
        {
            'id': 2,
            'tail': 'PR-E1B',
            'serial': '19000078',
            'etrack': 'ETR-1038',
            'data_cadastro': '2026-03-10',
            'subject': 'Hydraulic line seal replacement disposition',
            'hours_at_creation': 9800.0,
            'cycles_at_creation': 7001,
            'created_by': 'Engineering',
            'created_at': '2026-03-10 16:20:00',
            'attachment': None,
            'safety': 0,
            'hotline': 1,
            'systemas': 1,
            'estruturas': 0,
            'outros': 0,
            'etd_emitida': 'YES',
        },
    ]


def _load_etd_items():
    return _json_load_list(FALLBACK_ETD_FILE, _default_etd_items)


def _save_etd_items(rows):
    _json_save_list(FALLBACK_ETD_FILE, rows)


def _default_lru_items():
    return []


def _load_lru_items():
    return _json_load_list(FALLBACK_LRU_FILE, _default_lru_items)


def _save_lru_items(rows):
    _json_save_list(FALLBACK_LRU_FILE, rows)


def _sync_offline_snapshots_from_db(max_rows=2000):
    """Best-effort sync of offline JSON snapshots from MySQL data."""
    try:
        cursor = get_db_cursor()
    except Exception as exc:
        app.logger.warning(
            'Offline snapshot sync skipped (no DB cursor): %s', exc)
        return

    try:
        cursor.execute(
            f"""
            SELECT
                id,
                tail,
                modelo,
                prioridade,
                categoria,
                problema,
                ata,
                localizacao,
                tecnico_responsavel,
                tempo_estimado_horas,
                status_atual,
                troubleshooting,
                solucao,
                data_cadastro,
                data_cadastro AS data_criacao,
                'db-sync' AS criado_por
            FROM {TS_DB}.falhas
            ORDER BY data_cadastro DESC, id DESC
            LIMIT %s
            """,
            (max_rows,)
        )
        _save_fallback_records(cursor.fetchall())
    except Exception as exc:
        app.logger.warning('Offline snapshot sync falhas failed: %s', exc)

    try:
        cursor.execute(
            f"""
            SELECT
                tail,
                MAX(serial) AS serial,
                SUM(COALESCE(fh, 0)) AS fh,
                SUM(COALESCE(fc, 0)) AS fc,
                MAX(data_cadastro) AS data_cadastro
            FROM {FLEET_DB}.tail_metrics
            WHERE tail IS NOT NULL AND tail <> ''
            GROUP BY tail
            ORDER BY tail
            """
        )
        _save_tail_metrics(cursor.fetchall())
    except Exception as exc:
        app.logger.warning(
            'Offline snapshot sync tail_metrics failed: %s', exc)

    try:
        cursor.execute(
            f"""
            SELECT id, date_opened, tail, logbook, system_inop, category, ata, chapter,
                   due_date, date_closed, notes, created_at
            FROM {MEL_DB}.mel_items
            ORDER BY COALESCE(created_at, date_opened, due_date) DESC, id DESC
            LIMIT %s
            """,
            (max_rows,)
        )
        _save_mel_items(cursor.fetchall())
    except Exception as exc:
        app.logger.warning('Offline snapshot sync mel_items failed: %s', exc)

    try:
        cursor.execute(
            f"""
            SELECT id, tail, serial, etrack, data_cadastro, subject,
                   hours_at_creation, cycles_at_creation, created_by, created_at,
                   attachment, safety, hotline, systemas, estruturas, outros, etd_emitida
            FROM {ETD_DB}.etds
            ORDER BY created_at DESC, id DESC
            LIMIT %s
            """,
            (max_rows,)
        )
        _save_etd_items(cursor.fetchall())
    except Exception as exc:
        app.logger.warning('Offline snapshot sync etds failed: %s', exc)

    try:
        cursor.execute(
            f"""
            SELECT id, date, tail, interruption_type, ata, fail_code, location,
                   event_description, maintenance_actions, expected_return, release_date
            FROM {TS_DB}.out_of_service
            ORDER BY date DESC, id DESC
            LIMIT %s
            """,
            (max_rows,)
        )
        _save_aog_items(cursor.fetchall())
    except Exception as exc:
        app.logger.warning(
            'Offline snapshot sync out_of_service failed: %s', exc)

    try:
        cursor.execute(
            f"""
            SELECT id, acft_registration, pn_off, sn_off, pn_on, sn_on,
                   removal_classification, tsi, tso, tsn, position,
                   removal_date, removal_reason
            FROM {TS_DB}.lru_removal_installation
            ORDER BY removal_date DESC, id DESC
            LIMIT %s
            """,
            (max_rows,)
        )
        _save_lru_items(cursor.fetchall())
    except Exception as exc:
        app.logger.warning(
            'Offline snapshot sync lru_removal_installation failed: %s', exc)


def _save_fallback_records(records):
    try:
        with open(FALLBACK_RECORDS_FILE, 'w', encoding='utf-8') as file_obj:
            json.dump(records, file_obj, indent=2, default=str)
    except Exception as exc:
        app.logger.warning('Fallback records file write error: %s', exc)


def _load_fallback_records():
    should_save = False
    if os.path.exists(FALLBACK_RECORDS_FILE):
        try:
            with open(FALLBACK_RECORDS_FILE, 'r', encoding='utf-8') as file_obj:
                raw_records = json.load(file_obj)
        except Exception as exc:
            app.logger.warning('Fallback records file read error: %s', exc)
            raw_records = []
            should_save = True
    else:
        raw_records = []
        should_save = True

    if not isinstance(raw_records, list) or not raw_records:
        raw_records = _default_fallback_records()
        should_save = True

    normalized_records = []
    for index, raw_record in enumerate(raw_records, start=1):
        if not isinstance(raw_record, dict):
            should_save = True
            continue

        record = dict(raw_record)
        record.setdefault('id', index)
        record.setdefault('tail', '')
        record.setdefault('modelo', '')
        record.setdefault('prioridade', 'Medium')
        record.setdefault('categoria', 'General')
        record.setdefault('problema', '')
        record.setdefault('ata', '')
        record.setdefault('localizacao', '')
        record.setdefault('tecnico_responsavel', '')
        record.setdefault('tempo_estimado_horas', 0)
        record.setdefault('status_atual', 'Open')
        record.setdefault('troubleshooting', '')
        record.setdefault('solucao', '')
        record.setdefault(
            'data_cadastro', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        record.setdefault('data_criacao', record.get('data_cadastro'))
        record.setdefault('criado_por', 'system')
        normalized_records.append(record)

    normalized_records.sort(
        key=lambda item: (str(item.get('data_cadastro') or ''),
                          int(item.get('id') or 0)),
        reverse=True,
    )

    if should_save:
        _save_fallback_records(normalized_records)

    return normalized_records


def _filter_fallback_records(req_args, limit=500):
    records = _load_fallback_records()
    tail = req_args.get('tail', '').strip().lower()
    ata = req_args.get('ata', '').strip().lower()
    prioridade = req_args.get('prioridade', '').strip().lower()
    status_raw = req_args.get(
        'status_atual', req_args.get('status', '')).strip().lower()
    data_inicio = req_args.get('data_inicio', '').strip()
    data_fim = req_args.get('data_fim', '').strip()
    selected_models = [value.strip() for value in req_args.getlist(
        'model') if str(value).strip()]
    selected_model_tokens = {_normalize_model_filter_token(
        value) for value in selected_models if _normalize_model_filter_token(value)}

    status_map = {
        'open': 'open',
        'in progress': 'in progress',
        'in-progress': 'in progress',
        'review': 'pending review',
        'pending review': 'pending review',
        'resolved': 'closed',
        'closed': 'closed',
    }
    status_filter = status_map.get(status_raw)

    filtered = []
    for row in records:
        row_tail = str(row.get('tail') or '').lower()
        row_ata = str(row.get('ata') or '').lower()
        row_prioridade = str(row.get('prioridade') or '').lower()
        row_status = str(row.get('status_atual') or '').lower()
        row_model = str(row.get('modelo') or '')
        row_model_token = _normalize_model_filter_token(row_model)
        row_date = str(row.get('data_cadastro') or '')[:10]

        if tail and tail not in row_tail:
            continue
        if ata and ata not in row_ata:
            continue
        if prioridade and prioridade != row_prioridade:
            continue
        if status_filter and status_filter != row_status:
            continue
        if selected_model_tokens and row_model_token not in selected_model_tokens:
            continue
        if data_inicio and row_date and row_date < data_inicio:
            continue
        if data_fim and row_date and row_date > data_fim:
            continue

        filtered.append(row)

    if limit:
        filtered = filtered[:int(limit)]

    return filtered, selected_models


def _create_fallback_record_from_form(form_data):
    records = _load_fallback_records()
    next_id = max((int(item.get('id') or 0)
                  for item in records), default=1000) + 1
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    prioridade_raw = (form_data.get('prioridade') or 'Medium').strip().lower()
    prioridade_map = {
        'critical': 'Critical',
        'high': 'High',
        'medium': 'Medium',
        'low': 'Low',
        '⚠️ critical': 'Critical',
        '🔴 high': 'High',
        '🟡 medium': 'Medium',
        '🟢 low': 'Low',
    }

    record = {
        'id': next_id,
        'tail': form_data.get('tail') or '',
        'modelo': form_data.get('modelo') or '',
        'prioridade': prioridade_map.get(prioridade_raw, 'Medium'),
        'categoria': form_data.get('categoria') or 'General',
        'problema': form_data.get('problema') or form_data.get('descricao') or '',
        'ata': form_data.get('ata') or '',
        'localizacao': form_data.get('localizacao') or '',
        'tecnico_responsavel': form_data.get('tecnico_responsavel') or '',
        'tempo_estimado_horas': _to_float(form_data.get('tempo_estimado_horas'), 0.0),
        'status_atual': form_data.get('status_atual') or 'Open',
        'troubleshooting': form_data.get('troubleshooting') or '',
        'solucao': form_data.get('solucao') or '',
        'data_cadastro': now,
        'data_criacao': now,
        'criado_por': session.get('username', 'offline-user'),
    }

    records.insert(0, record)
    _save_fallback_records(records)
    return record

# ========== HELPER FUNCTIONS ==========


def get_db_cursor():
    """Returns a MySQL cursor."""
    try:
        mysql.connection.ping(True)
    except Exception:
        # flask_mysqldb reabre no próximo access; fallback usa reconnect explícito.
        if hasattr(mysql, 'reconnect'):
            try:
                mysql.reconnect()
            except Exception:
                pass
    return mysql.connection.cursor(MySQLdb.cursors.DictCursor)


def mysql_is_available():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(0.5)
        return sock.connect_ex((app.config.get('MYSQL_HOST', 'localhost'), 3306)) == 0
    except Exception:
        return False
    finally:
        sock.close()


@app.context_processor
def inject_runtime_status():
    return {
        'offline_mode': not mysql_is_available(),
    }


def _parse_date(value):
    if not value:
        return None
    if isinstance(value, (date, datetime)):
        return value.date() if isinstance(value, datetime) else value
    try:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').date()
    except ValueError:
        return None


def _to_float(value, default=0.0):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return default


def _to_int(value, default=0):
    try:
        return int(float(value or 0))
    except (TypeError, ValueError):
        return default


def _extract_mel_note_value(notes, marker):
    text = str(notes or '')
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned.startswith(marker):
            return cleaned[len(marker):].strip() or None
    return None


def _build_mel_resolution_summary(notes):
    solution_response = _extract_mel_note_value(notes, '[SOLUTION RESPONSE]')
    if solution_response:
        return solution_response
    fallback = str(notes or '').strip()
    return fallback or 'Fechamento registrado em sistema.'


def _normalize_model_name(value):
    """Normalize common Mexicana model aliases to a canonical display value."""
    raw = str(value or '').strip().upper().replace(' ', '')
    if not raw:
        return ''
    alias_map = {
        'EMB145': 'ERJ145',
        'ERJ145': 'ERJ145',
        'EMB170': 'E170',
        'ERJ170': 'E170',
        'E170': 'E170',
        'EMB175': 'E175',
        'ERJ175': 'E175',
        'E175': 'E175',
        'EMB190': 'E190',
        'E190': 'E190',
        'EMB195': 'E195',
        'E195': 'E195',
        'E190E2': 'E190-E2',
        'E195E2': 'E195-E2',
        'E190-E2': 'E190-E2',
        'E195-E2': 'E195-E2',
    }
    return alias_map.get(raw, raw)


def _normalize_model_filter_token(value):
    return _normalize_model_name(value).replace('-', '')


def _is_valid_tail_code(value):
    tail = str(value or '').strip().upper()
    if not tail:
        return False
    if tail in {'FLEET', 'FROTA', 'ALL', 'TOTAL'}:
        return False
    return '-' in tail and len(tail) >= 5


def _infer_model_from_tail(tail):
    tail_code = str(tail or '').strip().upper()
    if tail_code.startswith('PS-'):
        return 'E195-E2'
    if tail_code.startswith('PR-E2'):
        suffix = tail_code.split('-', 1)[-1]
        if suffix.startswith('E2A') or suffix.startswith('E2B') or suffix.startswith('E2D'):
            return 'E195-E2'
        return 'E190-E2'
    if tail_code.startswith('PR-E1'):
        return 'E190'
    if tail_code.startswith('PR-ERJ'):
        return 'ERJ145'
    return 'E190-E2'


def get_model_options():
    """Return model options from DB plus known defaults used by the UI."""
    default_models = [
        'ERJ145',
        'E170',
        'E175',
        'E190',
        'E195',
        'E190-E2',
        'E195-E2',
    ]

    model_names = []
    try:
        cursor = get_db_cursor()
        cursor.execute(
            f"""
            SELECT DISTINCT TRIM(modelo) AS modelo
            FROM {TS_DB}.falhas
            WHERE modelo IS NOT NULL AND TRIM(modelo) <> ''
            ORDER BY TRIM(modelo)
            """
        )
        model_names = [str(r.get('modelo')).strip()
                       for r in cursor.fetchall() if r.get('modelo')]
    except Exception as e:
        app.logger.warning("Model options query error: %s", e)
        model_names = [str(r.get('modelo')).strip()
                       for r in _load_fallback_records() if r.get('modelo')]

    merged = []
    seen = set()
    for name in default_models + model_names:
        key = _normalize_model_name(name)
        if not key:
            continue
        key_ci = key.lower()
        if key_ci in seen:
            continue
        seen.add(key_ci)
        merged.append({'code': key, 'name': key})

    return merged


def _build_logbook_filters(req_args):
    where = ["1=1"]
    params = []

    tail = req_args.get('tail', '').strip()
    ata = req_args.get('ata', '').strip()
    prioridade = req_args.get('prioridade', '').strip()
    status_raw = req_args.get(
        'status_atual', req_args.get('status', '')).strip().lower()
    data_inicio = req_args.get('data_inicio', '').strip()
    data_fim = req_args.get('data_fim', '').strip()
    selected_models = [value.strip() for value in req_args.getlist(
        'model') if str(value).strip()]
    normalized_models = [_normalize_model_filter_token(
        value) for value in selected_models if _normalize_model_filter_token(value)]

    if tail:
        where.append("tail LIKE %s")
        params.append(f"%{tail}%")
    if ata:
        where.append("ata LIKE %s")
        params.append(f"%{ata}%")
    if prioridade:
        where.append("prioridade = %s")
        params.append(prioridade)

    status_map = {
        'open': 'Open',
        'in progress': 'In Progress',
        'in-progress': 'In Progress',
        'review': 'Pending Review',
        'pending review': 'Pending Review',
        'resolved': 'Closed',
        'closed': 'Closed',
    }
    status = status_map.get(status_raw)
    if status:
        where.append("status_atual = %s")
        params.append(status)
    if data_inicio:
        where.append("DATE(data_cadastro) >= %s")
        params.append(data_inicio)
    if data_fim:
        where.append("DATE(data_cadastro) <= %s")
        params.append(data_fim)
    if normalized_models:
        where.append("REPLACE(UPPER(TRIM(modelo)), '-', '') IN (" +
                     ",".join(["%s"] * len(normalized_models)) + ")")
        params.extend(normalized_models)

    return where, params, selected_models


def _fetch_logbook_records(req_args, limit=500):
    where, params, selected_models = _build_logbook_filters(req_args)
    try:
        cursor = get_db_cursor()
        limit_sql = f" LIMIT {int(limit)}" if limit else ""
        cursor.execute(
            f"""
            SELECT
                id,
                tail,
                modelo,
                prioridade,
                categoria,
                problema,
                ata,
                localizacao,
                tecnico_responsavel,
                tempo_estimado_horas,
                status_atual,
                troubleshooting,
                solucao,
                data_cadastro,
                data_criacao,
                criado_por
            FROM {TS_DB}.falhas
            WHERE {' AND '.join(where)}
            ORDER BY data_cadastro DESC, id DESC{limit_sql}
            """,
            tuple(params)
        )
        return cursor.fetchall(), selected_models
    except Exception as e:
        app.logger.warning("Logbook data fallback activated: %s", e)
        return _filter_fallback_records(req_args, limit=limit)


def ensure_users_table():
    """Ensure authentication table exists and has at least one admin user."""
    cursor = None
    try:
        cursor = get_db_cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL,
                email VARCHAR(255) NULL,
                access_level VARCHAR(50) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

        cursor.execute("SELECT id FROM users WHERE username = %s", ('admin',))
        admin = cursor.fetchone()
        if not admin:
            admin_hash = generate_password_hash('admin123')
            cursor.execute(
                """
                INSERT INTO users (username, password, email, access_level)
                VALUES (%s, %s, %s, %s)
                """,
                ('admin', admin_hash, 'admin@example.com', 'Admin')
            )
        mysql.connection.commit()
    except Exception as e:
        app.logger.error(f"Users table setup error: {e}")
    finally:
        if cursor:
            pass


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session.get('username'):
            return redirect(url_for('login'))
        return func(*args, **kwargs)
    return wrapper

# Jinja filters


def format_date(value):
    if not value:
        return ''
    try:
        if isinstance(value, (date, datetime)):
            return value.strftime('%d/%m/%Y')
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value).strftime('%d/%m/%Y')
            except ValueError:
                try:
                    return datetime.strptime(value.split(' ')[0], '%Y-%m-%d').strftime('%d/%m/%Y')
                except ValueError:
                    return value
    except ValueError:
        return value
    return value


app.jinja_env.filters['format_date'] = format_date
app.jinja_env.globals['date'] = date
app.jinja_env.globals['current_date'] = lambda: datetime.now().strftime(
    '%d/%m/%Y')

# COMMENTED OUT - Causes "Already closed" error when called during module import
# with app.app_context():
#     ensure_users_table()

# ========== ROUTES ==========

# LOGIN / LOGOUT / MENU


@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index_or_login():
    """Home page - redirects to login if not authenticated"""
    if session.get('username'):
        return redirect(url_for('menu'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Username and password required', 'danger')
            return render_template('login.html')

        user = get_auth_user(username)

        if user and check_password_hash(user['password'], password):
            session['username'] = user['username']
            session['user_id'] = user['id']
            session['access_level'] = user.get('access_level', 'User')
            flash(f"Welcome, {username}!", 'success')
            return redirect(url_for('menu'))

        flash('Invalid credentials', 'danger')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('login'))


@app.route('/favicon.ico')
def favicon():
    """Serve the Mexicana symbol as favicon."""
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'mexicana-symbol.svg'
    )


@app.route('/menu')
@login_required
def menu():
    """Main menu"""
    return render_template('menu.html')


@app.route('/consulta', methods=['GET'])
@login_required
def consulta():
    """Compat route used by legacy templates, mapped to logbook."""
    return redirect(url_for('logbook_data'))


@app.route('/fleet/e2', methods=['GET'])
@login_required
def e2_fleet_dashboard():
    """Redirect legacy E2 dashboard entrypoint to current AI analysis page."""
    return redirect(url_for('analytics.ai_analysis_page'))


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Change user password"""
    if request.method == 'POST':
        current_pwd = request.form.get('current_password', '')
        new_pwd = request.form.get('new_password', '')
        confirm_pwd = request.form.get('confirm_password', '')

        if new_pwd != confirm_pwd:
            flash('Passwords do not match', 'danger')
            return render_template('change_password.html')

        try:
            cursor = get_db_cursor()
            cursor.execute(
                "SELECT password FROM users WHERE username = %s", (session['username'],))
            user = cursor.fetchone()

            if not user or not check_password_hash(user['password'], current_pwd):
                flash('Current password incorrect', 'danger')
                return render_template('change_password.html')

            hashed_pwd = generate_password_hash(
                new_pwd, method='pbkdf2:sha256')
            cursor = get_db_cursor()
            cursor.execute("UPDATE users SET password = %s WHERE username = %s",
                           (hashed_pwd, session['username']))
            mysql.connection.commit()

            flash('Password changed successfully', 'success')
            return redirect(url_for('menu'))
        except Exception as e:
            app.logger.error(f"Password change error: {e}")
            flash('Error changing password', 'danger')

    return render_template('change_password.html')


@app.route('/user_management')
@login_required
def user_management():
    """User management (admin)"""
    access_levels = ['Basic', 'Normal', 'Admin']
    users = []
    try:
        cursor = get_db_cursor()
        cursor.execute(
            """
            SELECT id, username, email, access_level, created_at
            FROM users
            ORDER BY username
            """
        )
        users = cursor.fetchall()

    except Exception as e:
        app.logger.error(f"User management error: {e}")

    return render_template('user_management.html', users=users, access_levels=access_levels)


@app.route('/create_user', methods=['POST'])
@login_required
def create_user():
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    email = request.form.get('email', '').strip() or None
    allowed_access_levels = {'basic': 'Basic',
                             'normal': 'Normal', 'admin': 'Admin'}
    raw_access_level = request.form.get('access_level', 'Normal').strip()
    access_level = allowed_access_levels.get(
        raw_access_level.lower(), 'Normal')

    if not username or not password:
        flash('Username and password are required.', 'danger')
        return redirect(url_for('user_management'))

    try:
        cursor = get_db_cursor()
        cursor.execute(
            """
            INSERT INTO users (username, password, email, access_level)
            VALUES (%s, %s, %s, %s)
            """,
            (username, generate_password_hash(password), email, access_level)
        )
        mysql.connection.commit()

        flash('User created successfully.', 'success')
    except Exception as e:
        app.logger.error("Create user error: %s", e)
        flash('Failed to create user.', 'danger')
    return redirect(url_for('user_management'))


@app.route('/reset_user_password', methods=['POST'])
@login_required
def reset_user_password():
    user_id = request.form.get('user_id')
    new_password = request.form.get(
        'new_password', 'admin123').strip() or 'admin123'
    try:
        cursor = get_db_cursor()
        cursor.execute(
            "UPDATE users SET password = %s WHERE id = %s",
            (generate_password_hash(new_password), user_id)
        )
        mysql.connection.commit()

        flash('Password reset successfully.', 'success')
    except Exception as e:
        app.logger.error("Reset password error: %s", e)
        flash('Failed to reset password.', 'danger')
    return redirect(url_for('user_management'))


@app.route('/delete_user', methods=['POST'])
@login_required
def delete_user():
    user_id = request.form.get('user_id')
    try:
        cursor = get_db_cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        mysql.connection.commit()

        flash('User removed successfully.', 'success')
    except Exception as e:
        app.logger.error("Delete user error: %s", e)
        flash('Failed to remove user.', 'danger')
    return redirect(url_for('user_management'))

# ========== 10 OPERATIONAL PAGES ==========


@app.route('/cadastro', methods=['GET', 'POST'])
@login_required
def cadastro():
    """Fail registration page"""
    msg = None
    falhas = []

    if request.method == 'POST':
        try:
            cursor = get_db_cursor()
            status_atual = request.form.get('status_atual') or 'Open'
            problema = request.form.get(
                'problema') or request.form.get('descricao') or ''
            categoria = request.form.get('categoria') or 'Manutencao Corretiva'
            prioridade_raw = (request.form.get(
                'prioridade') or 'Medium').strip()
            prioridade_map = {
                'critical': 'Critical',
                'high': 'High',
                'medium': 'Medium',
                'low': 'Low',
                '⚠️ critical': 'Critical',
                '🔴 high': 'High',
                '🟡 medium': 'Medium',
                '🟢 low': 'Low',
            }
            prioridade = prioridade_map.get(prioridade_raw.lower(), 'Medium')

            allowed_status = {'Open', 'In Progress',
                              'Pending Review', 'Closed'}
            if status_atual not in allowed_status:
                status_atual = 'Open'

            cursor.execute(
                f"""
                INSERT INTO {TS_DB}.falhas
                (data_cadastro, tail, modelo, status_atual, problema, categoria, prioridade, ata,
                 localizacao, tecnico_responsavel, tempo_estimado_horas, troubleshooting, solucao)
                VALUES (NOW(), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    request.form.get('tail'),
                    request.form.get('modelo'),
                    status_atual,
                    problema,
                    categoria,
                    prioridade,
                    request.form.get('ata') or None,
                    request.form.get('localizacao') or None,
                    request.form.get('tecnico_responsavel') or None,
                    request.form.get('tempo_estimado_horas') or 0,
                    request.form.get('troubleshooting') or None,
                    request.form.get('solucao') or None,
                )
            )
            mysql.connection.commit()

            flash('Failure record created successfully.', 'success')
            return redirect(url_for('cadastro'))
        except (pymysql.OperationalError, pymysql.InterfaceError) as e:
            app.logger.error("Cadastro MySQL connection error: %s", e)
            _create_fallback_record_from_form(request.form)
            flash(
                'MySQL unavailable. Failure record saved in local offline mode.', 'warning')
            return redirect(url_for('cadastro'))
        except Exception as e:
            app.logger.error("Cadastro write error (%s): %s",
                             type(e).__name__, e)
            flash(f'Error saving record: {type(e).__name__} — {e}', 'danger')
            return redirect(url_for('cadastro'))

    try:
        cursor = get_db_cursor()
        cursor.execute(
            f"SELECT id, data_cadastro, tail, modelo, status_atual FROM {TS_DB}.falhas ORDER BY id DESC LIMIT 50"
        )
        falhas = cursor.fetchall()
    except Exception as e:
        app.logger.error("Cadastro read error: %s", e)
        falhas = [
            {
                'id': row.get('id'),
                'data_cadastro': row.get('data_cadastro'),
                'tail': row.get('tail'),
                'modelo': row.get('modelo'),
                'status_atual': row.get('status_atual'),
            }
            for row in _load_fallback_records()[:50]
        ]

    return render_template(
        'cadastro.html',
        falhas=falhas,
        msg=msg,
        model_options=get_model_options(),
    )


@app.route('/horas_ciclos', methods=['GET', 'POST'])
@login_required
def horas_ciclos():
    """Flight hours and cycles tracking"""
    dados = []
    try:
        cursor = get_db_cursor()
        cursor.execute(
            f"""
            SELECT tail,
                   MAX(serial) AS serial,
                   SUM(COALESCE(fh, 0)) AS fh,
                   SUM(COALESCE(fc, 0)) AS fc,
                   MAX(data_cadastro) AS data_cadastro
            FROM {FLEET_DB}.tail_metrics
            WHERE tail IS NOT NULL AND tail <> ''
            GROUP BY tail
            ORDER BY tail
            """
        )
        dados = cursor.fetchall()
    except Exception as e:
        app.logger.warning("Horas ciclos query with schema failed: %s", e)
        try:
            cursor = get_db_cursor()
            cursor.execute(
                """
                SELECT tail,
                       MAX(serial) AS serial,
                       SUM(COALESCE(fh, 0)) AS fh,
                       SUM(COALESCE(fc, 0)) AS fc,
                       MAX(data_cadastro) AS data_cadastro
                FROM tail_metrics
                WHERE tail IS NOT NULL AND tail <> ''
                GROUP BY tail
                ORDER BY tail
                """
            )
            dados = cursor.fetchall()
        except Exception as inner:
            app.logger.error("Horas ciclos query error: %s", inner)
            dados = _load_tail_metrics()

    summary = []
    total_fh = 0.0
    total_fc = 0
    raw_total_fh = 0.0
    raw_total_fc = 0

    for row in dados:
        fh = _to_float(row.get('fh'))
        fc = _to_int(row.get('fc'))
        raw_total_fh += _to_float(row.get('fh'))
        raw_total_fc += _to_int(row.get('fc'))
        utilization_rate = 0
        if fh > 0:
            utilization_rate = min(100, int((fc / fh) * 100))
        total_fh += fh
        total_fc += fc
        summary.append({
            'tail': row.get('tail'),
            'modelo': 'E2',
            'total_fh': round(fh, 2),
            'total_fc': fc,
            'avg_fh_per_month': round(fh / 12, 2) if fh else 0,
            'avg_fc_per_month': round(fc / 12, 2) if fc else 0,
            'utilization_rate': utilization_rate,
            'operational_status': 'Ativo'
        })

    totals = {'total_fh': total_fh, 'total_fc': total_fc}
    high_usage_aircraft = [x for x in summary if x['total_fh'] >= 10000]
    diagnostics = {
        'db_rows': len(dados),
        'db_total_fh': round(raw_total_fh, 2),
        'db_total_fc': int(raw_total_fc),
        'page_rows': len(summary),
        'page_total_fh': round(total_fh, 2),
        'page_total_fc': int(total_fc),
    }

    return render_template(
        'horas_ciclos.html',
        dados=dados,
        summary=summary,
        totals=totals,
        high_usage_aircraft=high_usage_aircraft,
        diagnostics=diagnostics
    )


@app.route('/horas_ciclos/export/pdf', methods=['POST'])
@login_required
def horas_ciclos_export_pdf():
    flash('PDF export is unavailable in this simplified version.', 'warning')
    return redirect(url_for('horas_ciclos'))


@app.route('/horas_ciclos/export/excel', methods=['POST'])
@login_required
def horas_ciclos_export_excel():
    flash('Excel export is unavailable in this simplified version.', 'warning')
    return redirect(url_for('horas_ciclos'))


@app.route('/fleet_status_report', methods=['GET'])
@login_required
def fleet_status_report():
    """Fleet operational status"""
    requested_models = [
        value.strip()
        for value in request.args.getlist('model')
        if str(value).strip()
    ]
    frota = []
    falhas_by_tail = {}
    aog_by_tail = {}
    mel_by_tail = {}
    model_by_tail = {}
    ata_by_tail: dict = {}
    recent_by_tail: dict = {}

    try:
        cursor = get_db_cursor()
        cursor.execute(
            f"""
            SELECT tail,
                   MAX(serial) AS serial,
                   SUM(COALESCE(fh, 0)) AS fh,
                   SUM(COALESCE(fc, 0)) AS fc,
                   MAX(data_cadastro) AS data_cadastro
            FROM {FLEET_DB}.tail_metrics
            WHERE tail IS NOT NULL AND tail <> ''
            GROUP BY tail
            ORDER BY tail
            """
        )
        frota = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT tail,
                   COUNT(*) AS failures,
                   SUM(CASE WHEN LOWER(COALESCE(status_atual, 'open')) IN ('open', 'in progress', 'pending') THEN 1 ELSE 0 END) AS open_issues,
                   MAX(data_cadastro) AS last_failure
            FROM {TS_DB}.falhas
            WHERE tail IS NOT NULL AND tail <> ''
            GROUP BY tail
            """
        )
        for row in cursor.fetchall():
            falhas_by_tail[row['tail']] = row

        cursor.execute(
            f"""
            SELECT tail, COUNT(*) AS active_aog
            FROM {TS_DB}.out_of_service
            WHERE tail IS NOT NULL AND tail <> ''
                            AND release_date IS NULL
            GROUP BY tail
            """
        )
        for row in cursor.fetchall():
            aog_by_tail[row['tail']] = _to_int(row.get('active_aog'))

        cursor.execute(
            f"""
            SELECT tail, COUNT(*) AS open_mel
                        FROM {MEL_DB}.mel_items
            WHERE tail IS NOT NULL AND tail <> ''
              AND date_closed IS NULL
            GROUP BY tail
            """
        )
        for row in cursor.fetchall():
            mel_by_tail[row['tail']] = _to_int(row.get('open_mel'))

        # Top 2 ATA chapters per tail
        cursor.execute(
            f"""
            SELECT tail, TRIM(SUBSTRING_INDEX(ata, '.', 1)) AS ata_ch, COUNT(*) AS cnt
            FROM {TS_DB}.falhas
            WHERE tail IS NOT NULL AND tail <> ''
              AND ata IS NOT NULL AND TRIM(ata) <> ''
            GROUP BY tail, ata_ch
            ORDER BY tail, cnt DESC
            """
        )
        _ata_raw: dict = {}
        for row in cursor.fetchall():
            _t = str(row.get('tail') or '').strip().upper()
            if _t not in _ata_raw:
                _ata_raw[_t] = []
            if len(_ata_raw[_t]) < 2:
                _ata_raw[_t].append(str(row.get('ata_ch', '')))
        ata_by_tail = _ata_raw

        # Failures in the last 30 days per tail
        cursor.execute(
            f"""
            SELECT tail, COUNT(*) AS recent
            FROM {TS_DB}.falhas
            WHERE tail IS NOT NULL AND tail <> ''
              AND data_cadastro >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY tail
            """
        )
        for row in cursor.fetchall():
            _t = str(row.get('tail') or '').strip().upper()
            recent_by_tail[_t] = _to_int(row.get('recent'))

        cursor.execute(
            f"""
            SELECT tail, TRIM(modelo) AS modelo
            FROM {TS_DB}.falhas
            WHERE tail IS NOT NULL AND tail <> ''
              AND modelo IS NOT NULL AND TRIM(modelo) <> ''
            ORDER BY data_cadastro DESC, id DESC
            """
        )
        for row in cursor.fetchall():
            tail = row.get('tail')
            if not tail or tail in model_by_tail:
                continue
            model_by_tail[tail] = _normalize_model_name(row.get('modelo'))

    except Exception as e:
        app.logger.error("Fleet status query error: %s", e)
        frota = _load_tail_metrics()
        for row in _load_fallback_records():
            tail = row.get('tail')
            falhas_by_tail.setdefault(
                tail, {'failures': 0, 'open_issues': 0, 'last_failure': row.get('data_cadastro')})
            falhas_by_tail[tail]['failures'] = _to_int(
                falhas_by_tail[tail].get('failures')) + 1
            if str(row.get('status_atual') or '').lower() in ('open', 'in progress', 'pending review'):
                falhas_by_tail[tail]['open_issues'] = _to_int(
                    falhas_by_tail[tail].get('open_issues')) + 1
        for row in _load_aog_items():
            if not row.get('release_date'):
                aog_by_tail[row.get('tail')] = _to_int(
                    aog_by_tail.get(row.get('tail'))) + 1
        for row in _load_mel_items():
            if not row.get('date_closed'):
                mel_by_tail[row.get('tail')] = _to_int(
                    mel_by_tail.get(row.get('tail'))) + 1

        for row in _load_fallback_records():
            tail = row.get('tail')
            if not tail or tail in model_by_tail:
                continue
            model_by_tail[tail] = _normalize_model_name(row.get('modelo'))

    fleet_model_candidates = ['ERJ145', 'E170',
                              'E175', 'E190', 'E195', 'E190-E2', 'E195-E2']
    for tail_model in model_by_tail.values():
        normalized = _normalize_model_name(tail_model)
        if normalized and normalized not in fleet_model_candidates:
            fleet_model_candidates.append(normalized)

    selected_models = [_normalize_model_name(
        item) for item in requested_models if _normalize_model_name(item)]
    if not selected_models:
        selected_models = ['E190-E2', 'E195-E2']
    models = get_model_options()
    for candidate in fleet_model_candidates:
        if candidate not in {item['code'] for item in models}:
            models.append({'code': candidate, 'name': candidate})

    # Merge tails from all operational sources so fleet view is complete even
    # when a tail has troubleshooting/MEL/AOG data but missing metrics row.
    fleet_by_tail = {}
    for row in frota:
        tail_key = str(row.get('tail') or '').strip().upper()
        if not _is_valid_tail_code(tail_key):
            continue
        normalized_row = dict(row)
        normalized_row['tail'] = tail_key
        fleet_by_tail[tail_key] = normalized_row

    source_tails = set(fleet_by_tail.keys())
    source_tails.update(str(k or '').strip().upper()
                        for k in falhas_by_tail.keys())
    source_tails.update(str(k or '').strip().upper()
                        for k in aog_by_tail.keys())
    source_tails.update(str(k or '').strip().upper()
                        for k in mel_by_tail.keys())
    source_tails.update(str(k or '').strip().upper()
                        for k in model_by_tail.keys())
    source_tails = {tail for tail in source_tails if _is_valid_tail_code(tail)}

    for tail in source_tails:
        if tail in fleet_by_tail:
            continue
        fleet_by_tail[tail] = {
            'tail': tail,
            'serial': None,
            'fh': 0,
            'fc': 0,
            'data_cadastro': None,
        }

    frota = [fleet_by_tail[key] for key in sorted(fleet_by_tail.keys())]

    fleet_rows = []
    excellent_count = 0
    good_count = 0
    fair_count = 0
    mel_open_count = 0

    for row in frota:
        tail = str(row.get('tail') or '').strip().upper()
        if not _is_valid_tail_code(tail):
            continue
        inferred_model = _infer_model_from_tail(tail)
        model_code = _normalize_model_name(
            model_by_tail.get(tail) or inferred_model)
        if selected_models and model_code not in selected_models:
            continue

        falha_info = falhas_by_tail.get(tail, {})
        failures = _to_int(falha_info.get('failures'))
        open_troubleshooting = _to_int(falha_info.get('open_issues'))
        active_aog = _to_int(aog_by_tail.get(tail))
        open_mel = _to_int(mel_by_tail.get(tail))
        mel_open_count += open_mel

        # Business rule: aircraft is operational unless in Out of Service/AOG.
        if active_aog > 0:
            status_indicator = 'aog'
            fair_count += 1
        else:
            status_indicator = 'operational'
            excellent_count += 1

        # Keep troubleshooting visibility separated from MEL visibility.
        if open_troubleshooting > 0:
            good_count += 1

        health_score = 100 - (failures * 2) - \
            (open_troubleshooting * 5) - (open_mel * 4)
        if active_aog:
            health_score -= 25
        health_score = max(10, min(100, health_score))

        if health_score >= 85:
            health_status = 'EXCELLENT'
        elif health_score >= 70:
            health_status = 'GOOD'
        elif health_score >= 50:
            health_status = 'FAIR'
        else:
            health_status = 'POOR'

        last_failure = _parse_date(falha_info.get('last_failure'))
        days_since_last_failure = 0
        if last_failure:
            days_since_last_failure = max(
                0, (date.today() - last_failure).days)

        fleet_rows.append({
            'tail': tail,
            'modelo': model_code,
            'serial_number': row.get('serial'),
            'status_indicator': status_indicator,
            'health_score': health_score,
            'health_status': health_status,
            'failures': failures,
            'open_issues': open_troubleshooting,
            'open_troubleshooting': open_troubleshooting,
            'open_mel': open_mel,
            'has_open_troubleshooting': open_troubleshooting > 0,
            'fh': _to_float(row.get('fh')),
            'fc': _to_int(row.get('fc')),
            'days_since_last_failure': days_since_last_failure,
            'top_atas': ata_by_tail.get(tail, []),
            'recent_failures': recent_by_tail.get(tail, 0),
        })

    return render_template(
        'fleet_status_report.html',
        frota=frota,
        fleet_rows=fleet_rows,
        models=models,
        selected_models=selected_models,
        reference_date=datetime.now().strftime('%d/%m/%Y'),
        excellent_count=excellent_count,
        good_count=good_count,
        fair_count=fair_count,
        poor_count=0,
        mel_open_count=mel_open_count
    )


@app.route('/logbook_data', methods=['GET', 'POST'])
@login_required
def logbook_data():
    """Flight log and maintenance records"""
    registros = []
    selected_models = []

    try:
        registros, selected_models = _fetch_logbook_records(
            request.args, limit=500)
    except Exception as e:
        app.logger.error("Logbook query error: %s", e)
        registros = []

    models = get_model_options()
    return render_template(
        'logbook_data.html',
        registros=registros,
        logbook_rows=registros,
        models=models,
        selected_models=selected_models,
        msg=None
    )


@app.route('/logbook_data/export/excel', methods=['GET'])
@login_required
def logbook_export_excel():
    try:
        from openpyxl import Workbook

        registros, _ = _fetch_logbook_records(request.args, limit=100000)
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Logbook'
        sheet.append([
            'ID', 'Tail', 'Model', 'Priority', 'Category', 'Problem', 'ATA',
            'Location', 'Estimated Time (h)', 'Status',
            'Troubleshooting', 'Solution', 'Registration Date', 'Creation Date', 'Created By'
        ])

        for row in registros:
            sheet.append([
                row.get('id'), row.get('tail'), row.get(
                    'modelo'), row.get('prioridade'),
                row.get('categoria'), row.get('problema'), row.get(
                    'ata'), row.get('localizacao'),
                row.get('tempo_estimado_horas'), row.get('status_atual'),
                row.get('troubleshooting'), row.get(
                    'solucao'), row.get('data_cadastro'),
                row.get('data_criacao'), row.get('criado_por'),
            ])

        output = BytesIO()
        workbook.save(output)
        output.seek(0)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            output,
            as_attachment=True,
            download_name=f'logbook_data_{timestamp}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        app.logger.error("Logbook Excel export error: %s", e)
        flash('Failed to export Excel file.', 'danger')
        return redirect(url_for('logbook_data', **request.args.to_dict(flat=False)))


@app.route('/logbook_data/export/pdf', methods=['GET'])
@login_required
def logbook_export_pdf():
    try:
        registros, _ = _fetch_logbook_records(request.args, limit=5000)
        lines = [
            'LOGBOOK DATA EXPORT',
            f"Generated on {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            '',
        ]

        header = (
            'ID | Tail | Model | Priority | Problem | ATA | '
            'Status | Troubleshooting | Solution | Registration Date'
        )
        separator = '-' * len(header)
        lines.extend([header, separator])

        for row in registros:
            row_text = ' | '.join([
                str(row.get('id') or ''),
                str(row.get('tail') or ''),
                str(row.get('modelo') or ''),
                str(row.get('prioridade') or ''),
                str(row.get('problema') or ''),
                str(row.get('ata') or ''),
                str(row.get('status_atual') or ''),
                str(row.get('troubleshooting') or ''),
                str(row.get('solucao') or ''),
                str(row.get('data_cadastro') or ''),
            ])
            lines.extend(textwrap.wrap(row_text, width=150) or [''])
            lines.append('')

        pdf_bytes = _build_simple_text_pdf(lines)
        output = BytesIO(pdf_bytes)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return send_file(
            output,
            as_attachment=True,
            download_name=f'logbook_data_{timestamp}.pdf',
            mimetype='application/pdf'
        )
    except Exception as e:
        app.logger.error("Logbook PDF export error: %s", e)
        flash('Failed to export PDF file.', 'danger')
        return redirect(url_for('logbook_data', **request.args.to_dict(flat=False)))


@app.route('/logbook_data/export/csv', methods=['GET'])
@login_required
def logbook_export_csv():
    import csv
    import io
    try:
        registros, _ = _fetch_logbook_records(request.args, limit=100000)
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow([
            'ID', 'Tail', 'Model', 'Priority', 'Category', 'Problem',
            'ATA', 'Location', 'Est. Time (h)',
            'Status', 'Troubleshooting', 'Solution',
            'Registration Date', 'Creation Date', 'Created By'
        ])
        for row in registros:
            writer.writerow([
                row.get('id') or '',
                row.get('tail') or '',
                row.get('modelo') or '',
                row.get('prioridade') or '',
                row.get('categoria') or '',
                row.get('problema') or '',
                row.get('ata') or '',
                row.get('localizacao') or '',
                row.get('tempo_estimado_horas') or '',
                row.get('status_atual') or '',
                row.get('troubleshooting') or '',
                row.get('solucao') or '',
                str(row.get('data_cadastro') or ''),
                str(row.get('data_criacao') or ''),
                row.get('criado_por') or '',
            ])
        csv_bytes = output.getvalue().encode('utf-8-sig')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return Response(
            csv_bytes,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=logbook_data_{timestamp}.csv',
                'Content-Type': 'text/csv; charset=utf-8-sig',
            }
        )
    except Exception as e:
        app.logger.error("Logbook CSV export error: %s", e)
        flash('Failed to export CSV file.', 'danger')
        return redirect(url_for('logbook_data', **request.args.to_dict(flat=False)))


def _pdf_escape_text(value):
    text = str(value or '')
    return text.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _build_simple_text_pdf(lines):
    page_width = 842
    page_height = 595
    left_margin = 24
    top_margin = 560
    line_height = 11
    lines_per_page = 44

    if not lines:
        lines = ['No data available for export.']

    page_chunks = [
        lines[index:index + lines_per_page]
        for index in range(0, len(lines), lines_per_page)
    ]

    if not page_chunks:
        page_chunks = [['No data available for export.']]

    object_bodies = {
        1: b'<< /Type /Catalog /Pages 2 0 R >>',
        3: b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    }
    page_ids = []
    next_object_id = 4

    for chunk in page_chunks:
        commands = ['BT', '/F1 9 Tf']
        y_position = top_margin
        for line in chunk:
            safe_line = _pdf_escape_text(line)
            commands.append(
                f'1 0 0 1 {left_margin} {y_position} Tm ({safe_line}) Tj'
            )
            y_position -= line_height
        commands.append('ET')
        content_stream = '\n'.join(commands).encode('latin-1', 'replace')

        content_id = next_object_id
        page_id = next_object_id + 1
        next_object_id += 2

        object_bodies[content_id] = (
            f'<< /Length {len(content_stream)} >>\nstream\n'.encode('latin-1')
            + content_stream
            + b'\nendstream'
        )
        object_bodies[page_id] = (
            f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {page_width} '
            f'{page_height}] /Resources << /Font << /F1 3 0 R >> >> '
            f'/Contents {content_id} 0 R >>'
        ).encode('latin-1')
        page_ids.append(page_id)

    kids = ' '.join(f'{page_id} 0 R' for page_id in page_ids)
    object_bodies[2] = (
        f'<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>'
    ).encode('latin-1')

    max_object_id = max(object_bodies)
    pdf = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0] * (max_object_id + 1)

    for object_id in range(1, max_object_id + 1):
        offsets[object_id] = len(pdf)
        pdf.extend(f'{object_id} 0 obj\n'.encode('latin-1'))
        pdf.extend(object_bodies[object_id])
        pdf.extend(b'\nendobj\n')

    xref_offset = len(pdf)
    pdf.extend(f'xref\n0 {max_object_id + 1}\n'.encode('latin-1'))
    pdf.extend(b'0000000000 65535 f \n')
    for object_id in range(1, max_object_id + 1):
        pdf.extend(f'{offsets[object_id]:010d} 00000 n \n'.encode('latin-1'))

    pdf.extend(
        (
            f'trailer\n<< /Size {max_object_id + 1} /Root 1 0 R >>\n'
            f'startxref\n{xref_offset}\n%%EOF'
        ).encode('latin-1')
    )
    return bytes(pdf)


@app.route('/logbook_data/print', methods=['GET'])
@login_required
def logbook_print_view():
    try:
        registros, _ = _fetch_logbook_records(request.args, limit=100000)
        return render_template(
            'logbook_print.html',
            logbook_rows=registros,
            generated_at=datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        )
    except Exception as e:
        app.logger.error("Logbook print view error: %s", e)
        flash('Failed to generate print view.', 'danger')
        return redirect(url_for('logbook_data', **request.args.to_dict(flat=False)))


@app.route('/logbook_data/update_status', methods=['POST'])
@login_required
def logbook_update_status():
    data = request.get_json(silent=True) or {}
    record_id = data.get('id')
    status_raw = str(data.get('status') or '').strip().lower()
    status_map = {
        'open': 'Open',
        'in-progress': 'In Progress',
        'in progress': 'In Progress',
        'review': 'Pending Review',
        'pending review': 'Pending Review',
        'closed': 'Closed',
    }
    new_status = status_map.get(status_raw)
    if not record_id or not new_status:
        return jsonify({'success': False, 'error': 'Invalid parameters'}), 400

    try:
        cursor = get_db_cursor()
        cursor.execute(
            f"UPDATE {TS_DB}.falhas SET status_atual = %s WHERE id = %s",
            (new_status, record_id)
        )
        mysql.connection.commit()

        return jsonify({'success': True, 'status': new_status})
    except Exception as e:
        app.logger.error("Logbook status update error: %s", e)
        return jsonify({'success': False, 'error': 'Failed to update status'}), 500


@app.route('/api/update_falha', methods=['POST'])
@login_required
def api_update_falha():
    data = request.get_json(silent=True) or {}
    record_id = data.get('id')
    field = (data.get('field') or '').strip()
    value = data.get('value')

    allowed_fields = {
        'tail', 'modelo', 'prioridade', 'categoria', 'problema', 'ata',
        'localizacao', 'tecnico_responsavel', 'tempo_estimado_horas',
        'status_atual', 'solucao', 'troubleshooting'
    }
    if not record_id or field not in allowed_fields:
        return jsonify({'success': False, 'error': 'Field not allowed'}), 400

    if field == 'prioridade':
        value_map = {
            'critical': 'Critical',
            'high': 'High',
            'medium': 'Medium',
            'low': 'Low',
        }
        value = value_map.get(str(value).strip().lower(), 'Medium')

    if field == 'status_atual':
        status_map = {
            'open': 'Open',
            'in progress': 'In Progress',
            'pending review': 'Pending Review',
            'closed': 'Closed',
        }
        value = status_map.get(str(value).strip().lower(), 'Open')

    try:
        cursor = get_db_cursor()
        cursor.execute(
            f"UPDATE {TS_DB}.falhas SET {field} = %s WHERE id = %s",
            (value, record_id)
        )
        mysql.connection.commit()

        return jsonify({'success': True})
    except Exception as e:
        app.logger.error("API update falha error: %s", e)
        return jsonify({'success': False, 'error': 'Failed to save'}), 500


@app.route('/out_of_service', methods=['GET', 'POST'])
@login_required
def out_of_service():
    """AOG - Out of service aircraft"""
    if request.method == 'POST':
        action = request.form.get('action', 'add')
        try:
            cursor = get_db_cursor()
            if action == 'mark_operational':
                out_id = request.form.get('id')
                release_date = request.form.get(
                    'release_date') or date.today().isoformat()
                notes = request.form.get('operational_notes', '').strip()
                cursor.execute(
                    f"""
                    UPDATE {TS_DB}.out_of_service
                    SET release_date = %s,
                        maintenance_actions = CONCAT(COALESCE(maintenance_actions, ''), %s)
                    WHERE id = %s
                    """,
                    (release_date,
                     f"\n\n[RETURN] {notes}" if notes else '', out_id)
                )
                flash('Aircraft marked as operational.', 'success')
            else:
                cursor.execute(
                    f"""
                    INSERT INTO {TS_DB}.out_of_service
                    (date, tail, interruption_type, ata, fail_code, location,
                     event_description, maintenance_actions, expected_return, release_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        request.form.get('date') or date.today().isoformat(),
                        request.form.get('tail'),
                        request.form.get('interruption_type'),
                        request.form.get('ata'),
                        request.form.get('fail_code'),
                        request.form.get('location'),
                        request.form.get('event_description'),
                        request.form.get('maintenance_actions'),
                        request.form.get('expected_return') or None,
                        request.form.get('release_date') or None,
                    )
                )
                flash('AOG record created successfully.', 'success')
            mysql.connection.commit()

            return redirect(url_for('out_of_service'))
        except Exception as e:
            app.logger.error("Out of service write error: %s", e)
            items = _load_aog_items()
            if action == 'mark_operational':
                out_id = _to_int(request.form.get('id'))
                for item in items:
                    if _to_int(item.get('id')) == out_id:
                        item['release_date'] = request.form.get(
                            'release_date') or date.today().isoformat()
                        notes = request.form.get(
                            'operational_notes', '').strip()
                        if notes:
                            item['maintenance_actions'] = f"{item.get('maintenance_actions', '')}\n\n[RETURN] {notes}".strip(
                            )
                        break
                flash('Aircraft marked as operational in offline mode.', 'warning')
            else:
                next_id = max((_to_int(x.get('id'))
                              for x in items), default=0) + 1
                items.append({
                    'id': next_id,
                    'date': request.form.get('date') or date.today().isoformat(),
                    'tail': request.form.get('tail'),
                    'interruption_type': request.form.get('interruption_type'),
                    'ata': request.form.get('ata'),
                    'fail_code': request.form.get('fail_code'),
                    'location': request.form.get('location'),
                    'event_description': request.form.get('event_description'),
                    'maintenance_actions': request.form.get('maintenance_actions'),
                    'expected_return': request.form.get('expected_return') or None,
                    'release_date': request.form.get('release_date') or None,
                })
                flash('AOG record saved in offline mode.', 'warning')
            _save_aog_items(items)
            return redirect(url_for('out_of_service'))

    aog = []
    released = []
    try:
        cursor = get_db_cursor()
        cursor.execute(
            f"""
            SELECT id, date, tail, interruption_type, ata, fail_code, location,
                   event_description, maintenance_actions, expected_return, release_date
            FROM {TS_DB}.out_of_service
            WHERE release_date IS NULL
            ORDER BY date DESC, id DESC
            """
        )
        aog = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT id, date, tail, interruption_type, ata, fail_code, location,
                   event_description, maintenance_actions, expected_return, release_date
            FROM {TS_DB}.out_of_service
            WHERE release_date IS NOT NULL
            ORDER BY release_date DESC, id DESC
            LIMIT 200
            """
        )
        released = cursor.fetchall()

        cursor.execute(
            f"""
            SELECT tail, COALESCE(fh, 0) AS fh, COALESCE(fc, 0) AS fc
            FROM {FLEET_DB}.tail_metrics
            WHERE tail IS NOT NULL AND tail <> ''
            """
        )
        tail_metrics = {row['tail']: row for row in cursor.fetchall()}

    except Exception as e:
        app.logger.error("Out of service read error: %s", e)
        rows = _load_aog_items()
        aog = [dict(x) for x in rows if not x.get('release_date')]
        released = [dict(x) for x in rows if x.get('release_date')]
        tail_metrics = {
            row['tail']: row for row in _load_tail_metrics() if row.get('tail')}

    avg_ground_hours = 0
    estimated_aog_cost = 0
    released_today = 0

    for row in aog:
        tail_metric = tail_metrics.get(row.get('tail'), {})
        row['fh'] = _to_float(tail_metric.get('fh'))
        row['fc'] = _to_int(tail_metric.get('fc'))
        row['daily_cost'] = 12000
        start_date = _parse_date(row.get('date'))
        expected = _parse_date(row.get('expected_return'))
        days_open = 1
        if start_date:
            days_open = max(1, (date.today() - start_date).days)
        row['ground_hours'] = days_open * 24
        row['estimated_cost'] = days_open * row['daily_cost']
        estimated_aog_cost += row['estimated_cost']
        if expected and start_date:
            row['expected_days'] = max(0, (expected - start_date).days)

    for row in released:
        tail_metric = tail_metrics.get(row.get('tail'), {})
        row['fh'] = _to_float(tail_metric.get('fh'))
        row['fc'] = _to_int(tail_metric.get('fc'))
        start_date = _parse_date(row.get('date'))
        release_date = _parse_date(row.get('release_date'))
        if start_date and release_date:
            ground_hours = max(0, int((release_date - start_date).days) * 24)
            row['ground_hours'] = ground_hours
            row['total_aog_cost'] = int((ground_hours / 24) * 12000)
        else:
            row['ground_hours'] = 0
            row['total_aog_cost'] = 0
        if release_date == date.today():
            released_today += 1

    if aog:
        avg_ground_hours = int(sum(_to_int(x.get('ground_hours'))
                               for x in aog) / len(aog))

    tails = sorted({(x.get('tail') or '')
                   for x in list(tail_metrics.values()) if x.get('tail')})
    return render_template(
        'out_of_service.html',
        aog=aog,
        aog_list=aog,
        released_list=released,
        released_today=released_today,
        avg_ground_hours=avg_ground_hours,
        estimated_aog_cost=estimated_aog_cost,
        tails=tails
    )


@app.route('/tail_cadastro', methods=['GET', 'POST'])
@login_required
def tail_cadastro():
    """Aircraft registry management"""
    tails = []

    if request.method == 'POST':
        action = request.form.get('action', 'add')
        try:
            cursor = get_db_cursor()
            if action == 'delete':
                cursor.execute(
                    f"DELETE FROM {FLEET_DB}.tail_metrics WHERE id = %s",
                    (request.form.get('id'),)
                )
                flash('Aircraft removed successfully.', 'success')
            elif action == 'update':
                cursor.execute(
                    f"""
                    UPDATE {FLEET_DB}.tail_metrics
                    SET tail = %s,
                        serial = %s,
                        data_cadastro = %s,
                        fh = %s,
                        fc = %s
                    WHERE id = %s
                    """,
                    (
                        request.form.get('tail'),
                        request.form.get('serial') or None,
                        request.form.get('data_cadastro') or None,
                        request.form.get('hours') or 0,
                        request.form.get('cycles') or 0,
                        request.form.get('id'),
                    )
                )
                flash('Aircraft updated successfully.', 'success')
            else:
                cursor.execute(
                    f"""
                    INSERT INTO {FLEET_DB}.tail_metrics (tail, serial, fh, fc, data_cadastro)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        request.form.get('tail'),
                        request.form.get('serial') or None,
                        request.form.get('hours') or 0,
                        request.form.get('cycles') or 0,
                        request.form.get('data_cadastro') or None,
                    )
                )
                flash('Aircraft registered successfully.', 'success')

            mysql.connection.commit()

            return redirect(url_for('tail_cadastro'))
        except Exception as e:
            app.logger.error("Tail cadastro write error: %s", e)
            tails_local = _load_tail_metrics()
            if action == 'delete':
                row_id = _to_int(request.form.get('id'))
                tails_local = [row for row in tails_local if _to_int(
                    row.get('id')) != row_id]
                flash('Aircraft removed in offline mode.', 'warning')
            elif action == 'update':
                row_id = _to_int(request.form.get('id'))
                for row in tails_local:
                    if _to_int(row.get('id')) == row_id:
                        row['tail'] = request.form.get('tail')
                        row['serial'] = request.form.get('serial') or None
                        row['data_cadastro'] = request.form.get(
                            'data_cadastro') or None
                        row['fh'] = _to_float(request.form.get('hours'), 0)
                        row['fc'] = _to_int(request.form.get('cycles'), 0)
                        break
                flash('Aircraft updated in offline mode.', 'warning')
            else:
                next_id = max((_to_int(x.get('id'))
                              for x in tails_local), default=0) + 1
                tails_local.append({
                    'id': next_id,
                    'tail': request.form.get('tail'),
                    'serial': request.form.get('serial') or None,
                    'data_cadastro': request.form.get('data_cadastro') or None,
                    'fh': _to_float(request.form.get('hours'), 0),
                    'fc': _to_int(request.form.get('cycles'), 0),
                })
                flash('Aircraft saved in offline mode.', 'warning')
            _save_tail_metrics(tails_local)
            return redirect(url_for('tail_cadastro'))

    try:
        cursor = get_db_cursor()
        cursor.execute(
            f"""
            SELECT tail,
                   MAX(serial) AS serial,
                   MAX(data_cadastro) AS data_cadastro,
                   SUM(COALESCE(fh, 0)) AS total_fh,
                   SUM(COALESCE(fc, 0)) AS total_fc
            FROM {FLEET_DB}.tail_metrics
            WHERE tail IS NOT NULL AND tail <> ''
            GROUP BY tail
            ORDER BY tail
            """
        )
        tails = cursor.fetchall()

    except Exception as e:
        app.logger.error("Tail cadastro read error: %s", e)
        tails = _load_tail_metrics()

    active_count = len(tails)
    inactive_count = 0
    total_fh = sum(_to_float(x.get('total_fh')) for x in tails)
    total_fc = sum(_to_int(x.get('total_fc')) for x in tails)

    for item in tails:
        item['ativo'] = True
        fh = _to_float(item.get('total_fh'))
        fc = _to_int(item.get('total_fc'))
        fc_per_fh = (fc / fh) if fh > 0 else 0.0
        item['fc_per_fh'] = round(fc_per_fh, 2)
        item['fc_per_fh_display'] = f"{fc_per_fh:.2f}"

    return render_template(
        'tail_cadastro.html',
        tails=tails,
        active_count=active_count,
        inactive_count=inactive_count,
        total_fh=total_fh,
        total_fc=total_fc,
    )


@app.route('/mel_itens', methods=['GET', 'POST'])
@login_required
def mel_itens():
    """MEL - Minimum Equipment List"""

    # POST handler para cadastrar novo MEL
    if request.method == 'POST':
        try:
            cursor = get_db_cursor()
            cursor.execute(
                f"""
                INSERT INTO {MEL_DB}.mel_items
                (tail, system_inop, ata, date_opened, due_date, logbook, category, chapter, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    request.form.get('tail'),
                    request.form.get('system_inop'),
                    request.form.get('ata'),
                    request.form.get('date_opened') or None,
                    request.form.get('due_date') or None,
                    request.form.get('logbook') or None,
                    request.form.get('category') or None,
                    request.form.get('chapter') or None,
                    request.form.get('notes') or None,
                )
            )
            mysql.connection.commit()
            flash('MEL record created successfully.', 'success')
            return redirect(url_for('mel_itens'))
        except Exception as e:
            app.logger.error("MEL insert error: %s", e)
            items = _load_mel_items()
            next_id = max((_to_int(x.get('id')) for x in items), default=0) + 1
            items.append({
                'id': next_id,
                'date_opened': request.form.get('date_opened') or date.today().isoformat(),
                'tail': request.form.get('tail'),
                'logbook': request.form.get('logbook') or None,
                'system_inop': request.form.get('system_inop'),
                'category': request.form.get('category') or None,
                'ata': request.form.get('ata'),
                'chapter': request.form.get('chapter') or None,
                'due_date': request.form.get('due_date') or None,
                'date_closed': None,
                'notes': request.form.get('notes') or None,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            })
            _save_mel_items(items)
            flash('MEL record created in offline mode.', 'warning')
            return redirect(url_for('mel_itens'))

    filtros = {
        'ata': request.args.get('ata', '').strip(),
        'tail': request.args.get('tail', '').strip(),
        'status': request.args.get('status', '').strip().lower(),
    }
    where = ["1=1"]
    params = []
    if filtros['ata']:
        where.append("ata LIKE %s")
        params.append(f"%{filtros['ata']}%")
    if filtros['tail']:
        where.append("tail LIKE %s")
        params.append(f"%{filtros['tail']}%")

    itens = []
    try:
        cursor = get_db_cursor()
        cursor.execute(
            f"""
            SELECT id, date_opened, tail, logbook, system_inop, category, ata, chapter,
                   due_date, date_closed, notes, created_at
            FROM {MEL_DB}.mel_items
            WHERE {' AND '.join(where)}
            ORDER BY COALESCE(created_at, date_opened, due_date) DESC, id DESC
            """,
            tuple(params)
        )
        itens = cursor.fetchall()

    except Exception as e:
        app.logger.warning("MEL query with schema failed: %s", e)
        try:
            cursor = get_db_cursor()
            cursor.execute(
                f"""
                SELECT id, date_opened, tail, logbook, system_inop, category, ata, chapter,
                       due_date, date_closed, notes, created_at
                FROM mel_items
                WHERE {' AND '.join(where)}
                ORDER BY COALESCE(created_at, date_opened, due_date) DESC, id DESC
                """,
                tuple(params)
            )
            itens = cursor.fetchall()
        except Exception as inner:
            app.logger.warning("MEL extended query fallback failed: %s", inner)
            try:
                cursor = get_db_cursor()
                cursor.execute(
                    f"""
                    SELECT id, date_opened, tail, system_inop, ata, due_date, date_closed
                    FROM {MEL_DB}.mel_items
                    WHERE {' AND '.join(where)}
                    ORDER BY COALESCE(date_opened, due_date) DESC, id DESC
                    """,
                    tuple(params)
                )
                itens = cursor.fetchall()
            except Exception as final_err:
                app.logger.error("MEL query error: %s", final_err)
                itens = _load_mel_items()

    ata_counter = {}
    mel_list = []
    mel_closed_list = []
    urgent_mels = []
    for item in itens:
        opened = _parse_date(item.get('date_opened'))
        closed = _parse_date(item.get('date_closed'))
        days_open = max(0, (date.today() - opened).days) if opened else 0
        status = 'closed' if closed else 'open'
        ata_val = (item.get('ata') or '').strip()
        if ata_val:
            ata_counter[ata_val] = ata_counter.get(ata_val, 0) + 1

        mapped = {
            'id': item.get('id'),
            'tail': item.get('tail'),
            'modelo': 'E2',
            'ata': item.get('ata'),
            'chapter': item.get('chapter'),
            'category': item.get('category'),
            'logbook': item.get('logbook'),
            'notes': item.get('notes'),
            'created_at': item.get('created_at'),
            'system_inop': item.get('system_inop') or item.get('logbook'),
            'date_opened': item.get('date_opened'),
            'due_date': item.get('due_date'),
            'date_closed': item.get('date_closed'),
            'days_open': days_open,
            'status': status,
            'recurrence_count': ata_counter.get(ata_val, 1),
            'aircraft_affected': 1,
            'total_duration_days': days_open,
            'replaced_item': _extract_mel_note_value(item.get('notes'), '[REPLACED ITEM]'),
            'solution_response': _extract_mel_note_value(item.get('notes'), '[SOLUTION RESPONSE]'),
            'resolution_summary': _build_mel_resolution_summary(item.get('notes')) if closed else '',
        }

        if status == 'closed':
            mel_closed_list.append(mapped)
        else:
            mel_list.append(mapped)
            if days_open > 7:
                urgent_mels.append(mapped)

    if filtros['status'] in ('open', 'in progress', 'review'):
        mel_closed_list = []
    elif filtros['status'] in ('closed', 'resolved'):
        mel_list = []

    high_recurrence_ata = '—'
    if ata_counter:
        high_recurrence_ata = max(ata_counter, key=ata_counter.get)

    open_count = len(mel_list)
    closed_count = len(mel_closed_list)
    progress_count = len(
        [x for x in mel_list if _to_int(x.get('days_open')) <= 7])
    review_count = len(
        [x for x in mel_list if _to_int(x.get('days_open')) > 7])

    return render_template(
        'mel_itens.html',
        itens=itens,
        filtros=filtros,
        mel_list=mel_list,
        mel_closed_list=mel_closed_list,
        closed_mel_list=mel_closed_list,
        urgent_mels=urgent_mels,
        high_recurrence_ata=high_recurrence_ata,
        open_count=open_count,
        progress_count=progress_count,
        review_count=review_count,
        closed_count=closed_count,
    )


@app.route('/mel_itens/update_status', methods=['POST'])
@login_required
def mel_update_status():
    data = request.get_json(silent=True) or {}
    mel_id = data.get('id')
    new_status = (data.get('status') or '').strip().lower()
    replaced_item = (data.get('replaced_item') or '').strip()
    solution_response = (data.get('solution_response') or '').strip()

    if not mel_id or new_status not in ('open', 'closed'):
        return jsonify({'success': False, 'error': 'Invalid parameters'}), 400
    if new_status == 'closed' and not solution_response:
        return jsonify({'success': False, 'error': 'Solution is required to close item'}), 400

    try:
        cursor = get_db_cursor()
        if new_status == 'closed':
            note_parts = []
            if replaced_item:
                note_parts.append(f"[REPLACED ITEM] {replaced_item}")
            if solution_response:
                note_parts.append(f"[SOLUTION RESPONSE] {solution_response}")
            note_suffix = "\n" + "\n".join(note_parts) if note_parts else ''
            cursor.execute(
                f"""
                UPDATE {MEL_DB}.mel_items
                SET date_closed = CURDATE(),
                    notes = CONCAT(COALESCE(notes, ''), %s)
                WHERE id = %s
                """,
                (note_suffix, mel_id)
            )
        else:
            cursor.execute(
                f"UPDATE {MEL_DB}.mel_items SET date_closed = NULL WHERE id = %s",
                (mel_id,)
            )
        mysql.connection.commit()

        return jsonify({'success': True})
    except Exception as e:
        app.logger.error("MEL status update error: %s", e)
        items = _load_mel_items()
        for item in items:
            if _to_int(item.get('id')) == _to_int(mel_id):
                if new_status == 'closed':
                    item['date_closed'] = date.today().isoformat()
                    note_parts = []
                    if replaced_item:
                        note_parts.append(f"[REPLACED ITEM] {replaced_item}")
                    if solution_response:
                        note_parts.append(
                            f"[SOLUTION RESPONSE] {solution_response}")
                    suffix = "\n" + "\n".join(note_parts) if note_parts else ''
                    item['notes'] = f"{item.get('notes', '')}{suffix}".strip()
                else:
                    item['date_closed'] = None
                _save_mel_items(items)
                return jsonify({'success': True, 'offline': True})
        return jsonify({'success': False, 'error': 'Failed to update MEL'}), 500


@app.route('/consulta_etd', methods=['GET', 'POST'])
@app.route('/etd', methods=['GET', 'POST'])
@login_required
def etd():
    """ETD - Equipment Time Compliance"""
    page = int(request.args.get('page', 1) or 1)
    per_page = 50
    filters = {
        'subject': request.args.get('subject', ''),
        'serial': request.args.get('serial', ''),
        'palavra': request.args.get('palavra', ''),
        'page': page,
        'per_page': per_page
    }
    if request.method == 'POST':
        attachment_path = None
        attachment = request.files.get('attachment')
        if attachment and attachment.filename:
            filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{attachment.filename}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            attachment.save(save_path)
            attachment_path = url_for('download_file', filename=filename)

        values = (
            request.form.get('tail'),
            request.form.get('serial'),
            request.form.get('etrack'),
            request.form.get('data_cadastro') or None,
            request.form.get('subject'),
            request.form.get('hours_at_creation') or None,
            request.form.get('cycles_at_creation') or None,
            request.form.get('created_by') or None,
            request.form.get('created_at') or None,
            attachment_path,
            1 if request.form.get('safety') else 0,
            1 if request.form.get('hotline') else 0,
            1 if request.form.get('systemas') else 0,
            1 if request.form.get('estruturas') else 0,
            1 if request.form.get('outros') else 0,
            request.form.get('etd_emitida') or 'NO',
        )
        try:
            cursor = get_db_cursor()
            cursor.execute(
                f"""
                INSERT INTO {ETD_DB}.etds
                (tail, serial, etrack, data_cadastro, subject, hours_at_creation,
                 cycles_at_creation, created_by, created_at, attachment,
                 safety, hotline, systemas, estruturas, outros, etd_emitida)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                values
            )
            mysql.connection.commit()

            flash('ETD record created successfully.', 'success')
            return redirect(url_for('etd'))
        except Exception as e:
            app.logger.warning("ETD write with schema failed: %s", e)
            try:
                cursor = get_db_cursor()
                cursor.execute(
                    """
                    INSERT INTO etds
                    (tail, serial, etrack, data_cadastro, subject, hours_at_creation,
                     cycles_at_creation, created_by, created_at, attachment,
                     safety, hotline, systemas, estruturas, outros, etd_emitida)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    values
                )
                mysql.connection.commit()

                flash('ETD record created successfully.', 'success')
                return redirect(url_for('etd'))
            except Exception as inner:
                app.logger.error("ETD write error: %s", inner)
                items = _load_etd_items()
                next_id = max((_to_int(x.get('id'))
                              for x in items), default=0) + 1
                items.append({
                    'id': next_id,
                    'tail': request.form.get('tail'),
                    'serial': request.form.get('serial'),
                    'etrack': request.form.get('etrack'),
                    'data_cadastro': request.form.get('data_cadastro') or date.today().isoformat(),
                    'subject': request.form.get('subject'),
                    'hours_at_creation': request.form.get('hours_at_creation') or None,
                    'cycles_at_creation': request.form.get('cycles_at_creation') or None,
                    'created_by': request.form.get('created_by') or None,
                    'created_at': request.form.get('created_at') or datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'attachment': attachment_path,
                    'safety': 1 if request.form.get('safety') else 0,
                    'hotline': 1 if request.form.get('hotline') else 0,
                    'systemas': 1 if request.form.get('systemas') else 0,
                    'estruturas': 1 if request.form.get('estruturas') else 0,
                    'outros': 1 if request.form.get('outros') else 0,
                    'etd_emitida': request.form.get('etd_emitida') or 'NO',
                })
                _save_etd_items(items)
                flash('ETD record created in offline mode.', 'warning')
                return redirect(url_for('etd'))

    where = ["1=1"]
    params = []
    if filters['subject']:
        where.append("subject LIKE %s")
        params.append(f"%{filters['subject']}%")
    if filters['serial']:
        where.append("serial LIKE %s")
        params.append(f"%{filters['serial']}%")
    if filters['palavra']:
        where.append(
            "(subject LIKE %s OR serial LIKE %s OR etrack LIKE %s OR tail LIKE %s)")
        kw = f"%{filters['palavra']}%"
        params.extend([kw, kw, kw, kw])

    etds = []
    try:
        cursor = get_db_cursor()
        cursor.execute(
            f"""
            SELECT id, tail, serial, etrack, data_cadastro, subject,
                   hours_at_creation, cycles_at_creation, created_by, created_at,
                   attachment, safety, hotline, systemas, estruturas, outros, etd_emitida
            FROM {ETD_DB}.etds
            WHERE {' AND '.join(where)}
            ORDER BY created_at DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            tuple(params + [per_page, (page - 1) * per_page])
        )
        etds = cursor.fetchall()

    except Exception as e:
        app.logger.warning("ETD query with schema failed: %s", e)
        try:
            cursor = get_db_cursor()
            cursor.execute(
                f"""
                SELECT id, tail, serial, etrack, data_cadastro, subject,
                       hours_at_creation, cycles_at_creation, created_by, created_at,
                       attachment, safety, hotline, systemas, estruturas, outros, etd_emitida
                FROM etds
                WHERE {' AND '.join(where)}
                ORDER BY created_at DESC, id DESC
                LIMIT %s OFFSET %s
                """,
                tuple(params + [per_page, (page - 1) * per_page])
            )
            etds = cursor.fetchall()
        except Exception as inner:
            app.logger.error("ETD query error: %s", inner)
            etds = _load_etd_items()

    if not etds:
        etds = _load_etd_items()

    if filters['subject']:
        etds = [row for row in etds if filters['subject'].lower() in str(
            row.get('subject') or '').lower()]
    if filters['serial']:
        etds = [row for row in etds if filters['serial'].lower() in str(
            row.get('serial') or '').lower()]
    if filters['palavra']:
        kw = filters['palavra'].lower()
        etds = [
            row for row in etds
            if kw in str(row.get('subject') or '').lower()
            or kw in str(row.get('serial') or '').lower()
            or kw in str(row.get('etrack') or '').lower()
            or kw in str(row.get('tail') or '').lower()
        ]

    etds = etds[(page - 1) * per_page: page * per_page]

    for row in etds:
        created = _parse_date(row.get('data_cadastro')
                              ) or _parse_date(row.get('created_at'))
        row['days_pending'] = max(
            0, (date.today() - created).days) if created else 0

        etd_emitida = (row.get('etd_emitida') or '').upper()
        days = row['days_pending']

        if etd_emitida == 'YES':
            row['status_label'] = 'Issued'
            row['status_color'] = 'success'
        elif days > 7:
            row['status_label'] = 'Priority Pending'
            row['status_color'] = 'danger'
        else:
            row['status_label'] = 'Under Evaluation'
            row['status_color'] = 'warning'

    total_etd = len(etds)
    pending_etds = [x for x in etds if (
        x.get('etd_emitida') or '').upper() != 'YES']
    critical_count = sum(
        1 for x in pending_etds if _to_int(x.get('days_pending')) > 7)
    safety_count = sum(1 for x in pending_etds if _to_int(x.get('safety')) > 0)
    issued_count = sum(1 for x in etds if (
        x.get('etd_emitida') or '').upper() == 'YES')

    return render_template(
        'etd.html',
        etds=etds,
        rows=etds,
        filters=filters,
        total_etd=total_etd,
        critical_count=critical_count,
        safety_count=safety_count,
        issued_count=issued_count,
        etd_status_endpoint='etd_update_status'
    )


@app.route('/etd/<int:etd_id>/status', methods=['POST'])
@login_required
def etd_update_status(etd_id):
    new_status = (request.form.get('etd_emitida') or 'NO').upper()
    if new_status not in ('YES', 'NO'):
        new_status = 'NO'
    try:
        cursor = get_db_cursor()
        cursor.execute(
            f"UPDATE {ETD_DB}.etds SET etd_emitida = %s WHERE id = %s",
            (new_status, etd_id)
        )
        mysql.connection.commit()

        flash('ETD status updated.', 'success')
    except Exception as e:
        app.logger.warning("ETD status update with schema failed: %s", e)
        try:
            cursor = get_db_cursor()
            cursor.execute(
                "UPDATE etds SET etd_emitida = %s WHERE id = %s",
                (new_status, etd_id)
            )
            mysql.connection.commit()

            flash('ETD status updated.', 'success')
        except Exception as inner:
            app.logger.error("ETD status update error: %s", inner)
            items = _load_etd_items()
            for item in items:
                if _to_int(item.get('id')) == _to_int(etd_id):
                    item['etd_emitida'] = new_status
                    _save_etd_items(items)
                    flash('ETD status updated in offline mode.', 'warning')
                    return redirect(url_for('etd'))
            flash('Failed to update ETD status.', 'danger')
    return redirect(url_for('etd'))


@app.route('/lru_removal_installation', methods=['GET', 'POST'])
@login_required
def lru_removal_installation():
    """LRU - Line Replaceable Unit management"""
    lru_records = []
    total_records = 0
    raw_limit = str(request.args.get('limit') or '').strip()
    # Keep default wide enough to show the full dataset in normal operations.
    limit = max(50, min(_to_int(raw_limit, 2000) if raw_limit else 2000, 5000))

    if request.method == 'POST':
        try:
            cursor = get_db_cursor()
            cursor.execute(
                f"""
                INSERT INTO {TS_DB}.lru_removal_installation
                (acft_registration, pn_off, sn_off, pn_on, sn_on,
                 removal_classification, tsi, tso, tsn, position,
                 removal_date, removal_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    request.form.get('acft_registration'),
                    request.form.get('pn_off'),
                    request.form.get('sn_off'),
                    request.form.get('pn_on'),
                    request.form.get('sn_on'),
                    request.form.get('removal_classification') or None,
                    request.form.get('tsi') or None,
                    request.form.get('tso') or None,
                    request.form.get('tsn') or None,
                    request.form.get('position') or None,
                    request.form.get(
                        'removal_date') or date.today().isoformat(),
                    request.form.get('removal_reason') or None,
                )
            )
            mysql.connection.commit()

            flash('LRU record saved successfully.', 'success')
            return redirect(url_for('lru_removal_installation'))
        except Exception as e:
            app.logger.error(f"LRU error: {e}")
            items = _load_lru_items()
            next_id = max((_to_int(x.get('id')) for x in items), default=0) + 1
            items.append({
                'id': next_id,
                'acft_registration': request.form.get('acft_registration'),
                'pn_off': request.form.get('pn_off'),
                'sn_off': request.form.get('sn_off'),
                'pn_on': request.form.get('pn_on'),
                'sn_on': request.form.get('sn_on'),
                'removal_classification': request.form.get('removal_classification') or None,
                'tsi': request.form.get('tsi') or None,
                'tso': request.form.get('tso') or None,
                'tsn': request.form.get('tsn') or None,
                'position': request.form.get('position') or None,
                'removal_date': request.form.get('removal_date') or date.today().isoformat(),
                'removal_reason': request.form.get('removal_reason') or None,
            })
            _save_lru_items(items)
            flash('LRU record saved in offline mode.', 'warning')
            return redirect(url_for('lru_removal_installation'))

    try:
        cursor = get_db_cursor()
        cursor.execute(
            f"SELECT COUNT(*) AS total FROM {TS_DB}.lru_removal_installation")
        total_records = _to_int((cursor.fetchone() or {}).get('total'))
        cursor.execute(f"""
            SELECT id, acft_registration, pn_off, sn_off, pn_on, sn_on,
                   removal_classification, tsi, tso, tsn, position, removal_reason,
                   removal_date
            FROM {TS_DB}.lru_removal_installation
            ORDER BY removal_date DESC, id DESC
            LIMIT %s
        """, (limit,))
        lru_records = cursor.fetchall()
        cursor.execute(
            f"""
            SELECT tail
            FROM {FLEET_DB}.tail_metrics
            WHERE tail IS NOT NULL AND tail <> ''
            ORDER BY tail
            """
        )
        tails = [row['tail'] for row in cursor.fetchall()]

    except Exception as e:
        app.logger.error("LRU read error: %s", e)
        lru_records = _load_lru_items()
        total_records = len(lru_records)
        tails = sorted({
            str(row.get('tail') or '').strip()
            for row in _load_tail_metrics()
            if str(row.get('tail') or '').strip()
        })

    total_removed = len([x for x in lru_records if x.get('pn_off')])
    total_installed = len([x for x in lru_records if x.get('pn_on')])
    unique_pn = len({(x.get('pn_off') or '').strip()
                    for x in lru_records if x.get('pn_off')})
    failure_removals = len([
        x for x in lru_records
        if 'falha' in (x.get('removal_reason') or '').lower() or 'fail' in (x.get('removal_reason') or '').lower()
    ])

    pn_counter = {}
    for row in lru_records:
        pn = (row.get('pn_off') or '').strip()
        if pn:
            pn_counter[pn] = pn_counter.get(pn, 0) + 1
    high_removal_pn = None
    if pn_counter:
        most_pn = max(pn_counter, key=pn_counter.get)
        if pn_counter[most_pn] >= 3:
            high_removal_pn = most_pn

    return render_template(
        'lru_removal_installation.html',
        lru_records=lru_records,
        lru_registros=lru_records,
        tails=tails,
        total_records=total_records,
        displayed_records=len(lru_records),
        display_limit=limit,
        total_removed=total_removed,
        total_installed=total_installed,
        unique_pn=unique_pn,
        failure_removals=failure_removals,
        high_removal_pn=high_removal_pn
    )


@app.route('/lru_removal_installation/export/pdf', methods=['POST'])
@login_required
def lru_export_pdf():
    flash('PDF export is unavailable in this simplified version.', 'warning')
    return redirect(url_for('lru_removal_installation'))


@app.route('/lru_removal_installation/export/excel', methods=['POST'])
@login_required
def lru_export_excel():
    flash('Excel export is unavailable in this simplified version.', 'warning')
    return redirect(url_for('lru_removal_installation'))

# ========== FILE UPLOADS / DOWNLOADS ==========


@app.route('/uploads/<path:filename>')
def download_file(filename):
    """Serve uploaded files"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except:
        flash('File not found', 'danger')
        return redirect(url_for('menu'))

# ========== ERROR HANDLERS ==========


@app.errorhandler(404)
def page_not_found(e):
    return render_template('error_404.html'), 404


@app.errorhandler(500)
def internal_error(e):
    return render_template('error_500.html'), 500


@app.errorhandler(RequestEntityTooLarge)
def request_entity_too_large(e):
    if str(request.path or '').startswith('/api/'):
        return jsonify({
            'success': False,
            'error': 'Payload too large. Reduce file size or upload fewer files.',
            'max_upload_mb': int(app.config.get('MAX_CONTENT_LENGTH', 0) / (1024 * 1024)),
        }), 413
    return render_template('error_500.html'), 413

# ========== MAIN ==========


if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        port=5050,
        debug=False,
        use_reloader=False
    )
