import json
from datetime import date, datetime

import app as app_module


flask_app = app_module.app


def _ok(status_code: int) -> bool:
    return 200 <= int(status_code or 0) < 400


def _safe_db_cursor():
    try:
        return app_module.get_db_cursor()
    except Exception:
        return None


def _db_one(query, params=()):
    cur = _safe_db_cursor()
    if not cur:
        return None
    try:
        cur.execute(query, params)
        return cur.fetchone()
    except Exception:
        return None


def _db_exec(query, params=()):
    cur = _safe_db_cursor()
    if not cur:
        return False
    try:
        cur.execute(query, params)
        app_module.mysql.connection.commit()
        return True
    except Exception:
        return False


def run():
    marker = f"AUDIT_TMP_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    out = {
        "marker": marker,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "flows": {},
        "overall_ok": True,
    }

    with flask_app.app_context():
        with flask_app.test_client() as client:
            with client.session_transaction() as session:
                session["username"] = "admin"
                session["user_id"] = 1
                session["access_level"] = "Administrator"

            # 1) CADASTRO create + rollback
            f = {"create": False, "verify": False,
                 "rollback": False, "details": []}
            resp = client.post(
                "/cadastro",
                data={
                    "tail": "PR-TMP",
                    "modelo": "E190-E2",
                    "status_atual": "Open",
                    "problema": f"Falha temporaria {marker}",
                    "categoria": "Manutencao Corretiva",
                    "prioridade": "Medium",
                    "ata": "49",
                    "localizacao": "APU",
                    "tecnico_responsavel": "AUTOMATION",
                    "tempo_estimado_horas": "1",
                    "troubleshooting": "Teste de certificacao",
                    "solucao": "Rollback planejado",
                },
                follow_redirects=True,
            )
            f["create"] = _ok(resp.status_code)
            row = _db_one(
                f"SELECT id FROM {app_module.TS_DB}.falhas WHERE problema LIKE %s ORDER BY id DESC LIMIT 1",
                (f"%{marker}%",),
            )
            if row and row.get("id"):
                f["verify"] = True
                f["rollback"] = _db_exec(
                    f"DELETE FROM {app_module.TS_DB}.falhas WHERE id = %s",
                    (row["id"],),
                )
            else:
                f["details"].append(
                    "Registro nao encontrado em banco para verificacao/rollback.")
            out["flows"]["cadastro"] = f

            # 2) MEL create -> update_status -> rollback
            f = {"create": False, "update": False,
                 "verify": False, "rollback": False, "details": []}
            resp = client.post(
                "/mel_itens",
                data={
                    "tail": "PR-TMP",
                    "system_inop": "Temporary MEL test",
                    "ata": "21.41.00",
                    "date_opened": date.today().isoformat(),
                    "due_date": date.today().isoformat(),
                    "logbook": f"LB-{marker}",
                    "category": "B",
                    "chapter": "21-41",
                    "notes": f"{marker}",
                },
                follow_redirects=True,
            )
            f["create"] = _ok(resp.status_code)
            row = _db_one(
                f"SELECT id FROM {app_module.MEL_DB}.mel_items WHERE notes LIKE %s ORDER BY id DESC LIMIT 1",
                (f"%{marker}%",),
            )
            mel_id = row.get("id") if row else None
            if mel_id:
                resp_upd = client.post(
                    "/mel_itens/update_status",
                    json={
                        "id": mel_id,
                        "status": "closed",
                        "replaced_item": "TMP-PART",
                        "solution_response": "Temporary closeout for audit",
                    },
                )
                f["update"] = _ok(resp_upd.status_code)
                vrow = _db_one(
                    f"SELECT date_closed FROM {app_module.MEL_DB}.mel_items WHERE id = %s",
                    (mel_id,),
                )
                f["verify"] = bool(vrow)
                f["rollback"] = _db_exec(
                    f"DELETE FROM {app_module.MEL_DB}.mel_items WHERE id = %s",
                    (mel_id,),
                )
            else:
                f["details"].append(
                    "MEL temporario nao localizado para update/rollback.")
            out["flows"]["mel_itens"] = f

            # 3) ETD create -> status update -> rollback
            f = {"create": False, "update": False,
                 "verify": False, "rollback": False, "details": []}
            resp = client.post(
                "/etd",
                data={
                    "tail": "PR-TMP",
                    "serial": f"SER-{marker}",
                    "etrack": f"ETR-{marker}",
                    "data_cadastro": date.today().isoformat(),
                    "subject": f"ETD temporary {marker}",
                    "hours_at_creation": "10",
                    "cycles_at_creation": "5",
                    "created_by": "AUTOMATION",
                    "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "etd_emitida": "NO",
                },
                follow_redirects=True,
            )
            f["create"] = _ok(resp.status_code)
            row = _db_one(
                f"SELECT id FROM {app_module.ETD_DB}.etds WHERE subject LIKE %s ORDER BY id DESC LIMIT 1",
                (f"%{marker}%",),
            )
            etd_id = row.get("id") if row else None
            if etd_id:
                resp_upd = client.post(
                    f"/etd/{etd_id}/status", data={"etd_emitida": "YES"}, follow_redirects=True)
                f["update"] = _ok(resp_upd.status_code)
                vrow = _db_one(
                    f"SELECT etd_emitida FROM {app_module.ETD_DB}.etds WHERE id = %s",
                    (etd_id,),
                )
                f["verify"] = bool(vrow and str(
                    vrow.get("etd_emitida") or "").upper() == "YES")
                f["rollback"] = _db_exec(
                    f"DELETE FROM {app_module.ETD_DB}.etds WHERE id = %s",
                    (etd_id,),
                )
            else:
                f["details"].append(
                    "ETD temporario nao localizado para update/rollback.")
            out["flows"]["etd"] = f

            # 4) LRU create + rollback
            f = {"create": False, "verify": False,
                 "rollback": False, "details": []}
            resp = client.post(
                "/lru_removal_installation",
                data={
                    "acft_registration": "PR-TMP",
                    "pn_off": "TMP-PN-OFF",
                    "sn_off": f"TMP-SN-OFF-{marker}",
                    "pn_on": "TMP-PN-ON",
                    "sn_on": f"TMP-SN-ON-{marker}",
                    "removal_classification": "Scheduled",
                    "tsi": "11",
                    "tso": "22",
                    "tsn": "33",
                    "position": "Nose",
                    "removal_date": date.today().isoformat(),
                    "removal_reason": f"Temporary audit reason {marker}",
                },
                follow_redirects=True,
            )
            f["create"] = _ok(resp.status_code)
            row = _db_one(
                f"SELECT id FROM {app_module.TS_DB}.lru_removal_installation WHERE removal_reason LIKE %s ORDER BY id DESC LIMIT 1",
                (f"%{marker}%",),
            )
            lru_id = row.get("id") if row else None
            if lru_id:
                f["verify"] = True
                f["rollback"] = _db_exec(
                    f"DELETE FROM {app_module.TS_DB}.lru_removal_installation WHERE id = %s",
                    (lru_id,),
                )
            else:
                f["details"].append(
                    "LRU temporario nao localizado para rollback.")
            out["flows"]["lru_removal_installation"] = f

            # 5) TAIL cadastro add -> update -> delete
            f = {"create": False, "update": False,
                 "delete": False, "verify": False, "details": []}
            resp = client.post(
                "/tail_cadastro",
                data={
                    "action": "add",
                    "tail": "PR-TMP",
                    "serial": f"SER-{marker}",
                    "hours": "12",
                    "cycles": "6",
                    "data_cadastro": date.today().isoformat(),
                },
                follow_redirects=True,
            )
            f["create"] = _ok(resp.status_code)
            row = _db_one(
                f"SELECT id FROM {app_module.FLEET_DB}.tail_metrics WHERE serial = %s ORDER BY id DESC LIMIT 1",
                (f"SER-{marker}",),
            )
            tail_id = row.get("id") if row else None
            if tail_id:
                resp_upd = client.post(
                    "/tail_cadastro",
                    data={
                        "action": "update",
                        "id": tail_id,
                        "tail": "PR-TMP",
                        "serial": f"SER-{marker}",
                        "hours": "20",
                        "cycles": "10",
                        "data_cadastro": date.today().isoformat(),
                    },
                    follow_redirects=True,
                )
                f["update"] = _ok(resp_upd.status_code)
                resp_del = client.post(
                    "/tail_cadastro",
                    data={"action": "delete", "id": tail_id},
                    follow_redirects=True,
                )
                f["delete"] = _ok(resp_del.status_code)
                vrow = _db_one(
                    f"SELECT id FROM {app_module.FLEET_DB}.tail_metrics WHERE id = %s",
                    (tail_id,),
                )
                f["verify"] = vrow is None
            else:
                f["details"].append(
                    "Tail temporario nao localizado para update/delete.")
            out["flows"]["tail_cadastro"] = f

            # 6) USER create -> reset -> delete
            f = {"create": False, "reset": False,
                 "delete": False, "verify": False, "details": []}
            tmp_user = f"tmp_{marker.lower()}"
            resp = client.post(
                "/create_user",
                data={
                    "username": tmp_user,
                    "email": f"{tmp_user}@example.com",
                    "password": "Tmp#123456",
                    "access_level": "User",
                },
                follow_redirects=True,
            )
            f["create"] = _ok(resp.status_code)
            row = _db_one(
                "SELECT id FROM users WHERE username = %s ORDER BY id DESC LIMIT 1", (tmp_user,))
            uid = row.get("id") if row else None
            if uid:
                resp_reset = client.post(
                    "/reset_user_password",
                    data={"user_id": uid, "new_password": "Tmp#654321"},
                    follow_redirects=True,
                )
                f["reset"] = _ok(resp_reset.status_code)
                resp_del = client.post(
                    "/delete_user",
                    data={"user_id": uid},
                    follow_redirects=True,
                )
                f["delete"] = _ok(resp_del.status_code)
                vrow = _db_one("SELECT id FROM users WHERE id = %s", (uid,))
                f["verify"] = vrow is None
            else:
                f["details"].append(
                    "Usuario temporario nao localizado para reset/delete.")
            out["flows"]["user_management"] = f

            # 7) AOG create -> mark_operational -> rollback delete
            f = {"create": False, "update": False,
                 "rollback": False, "verify": False, "details": []}
            resp = client.post(
                "/out_of_service",
                data={
                    "action": "add",
                    "date": date.today().isoformat(),
                    "tail": "PR-TMP",
                    "interruption_type": "AOG",
                    "ata": "32",
                    "fail_code": "TMP",
                    "location": "Line",
                    "event_description": f"Temporary AOG {marker}",
                    "maintenance_actions": "Temporary action",
                    "expected_return": date.today().isoformat(),
                },
                follow_redirects=True,
            )
            f["create"] = _ok(resp.status_code)
            row = _db_one(
                f"SELECT id FROM {app_module.TS_DB}.out_of_service WHERE event_description LIKE %s ORDER BY id DESC LIMIT 1",
                (f"%{marker}%",),
            )
            out_id = row.get("id") if row else None
            if out_id:
                resp_upd = client.post(
                    "/out_of_service",
                    data={
                        "action": "mark_operational",
                        "id": out_id,
                        "release_date": date.today().isoformat(),
                        "operational_notes": "temporary close",
                    },
                    follow_redirects=True,
                )
                f["update"] = _ok(resp_upd.status_code)
                vrow = _db_one(
                    f"SELECT release_date FROM {app_module.TS_DB}.out_of_service WHERE id = %s",
                    (out_id,),
                )
                f["verify"] = bool(vrow and vrow.get("release_date"))
                f["rollback"] = _db_exec(
                    f"DELETE FROM {app_module.TS_DB}.out_of_service WHERE id = %s",
                    (out_id,),
                )
            else:
                f["details"].append(
                    "AOG temporario nao localizado para update/rollback.")
            out["flows"]["out_of_service"] = f

    for value in out["flows"].values():
        for key in ["create", "update", "delete", "reset", "verify", "rollback"]:
            if key in value and value[key] is False:
                out["overall_ok"] = False

    return out


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, ensure_ascii=False))
