"""資料存取層：FirestoreStore（正式）與 MemoryStore（本機測試），介面相同。

資料結構
  users/{line_user_id}  name, role(staff|boss), status(pending|active|rejected|disabled),
                        emp_no, state, created_at
  records/{nonce}       user_id, name, emp_no, item_id, item_name, count,
                        date(YYYY-MM-DD), month(YYYY-MM), voided, created_at
  attendance/{uid}_{date}  user_id, name, emp_no, date, month, clock_in(HH:MM), clock_out(HH:MM)
  meta/counters         next_emp_no
"""
import json
from datetime import datetime, timezone


def _now():
    return datetime.now(timezone.utc)


class MemoryStore:
    def __init__(self):
        self.users, self.records, self.att, self._next_no = {}, {}, {}, 1

    # 出勤
    def get_attendance(self, uid, date):
        a = self.att.get(f"{uid}_{date}")
        return dict(a) if a else None

    def save_attendance(self, uid, date, data):
        self.att.setdefault(f"{uid}_{date}", {}).update(data)

    def attendance_by_date(self, date):
        return [dict(a) for a in self.att.values() if a.get("date") == date]

    def attendance_by_month(self, month):
        return [dict(a) for a in self.att.values() if a.get("month") == month]

    def get_user(self, uid):
        u = self.users.get(uid)
        return dict(u) if u else None

    def save_user(self, uid, data):
        self.users.setdefault(uid, {"created_at": _now()}).update(data)

    def list_users(self, role=None, status=None):
        out = []
        for uid, u in self.users.items():
            if (role is None or u.get("role") == role) and (status is None or u.get("status") == status):
                out.append({"uid": uid, **u})
        return out

    def next_emp_no(self):
        n = self._next_no
        self._next_no += 1
        return f"E{n:03d}"

    def add_record(self, rid, rec):
        """回傳 False 代表這筆已存在（重複按）。"""
        if rid in self.records:
            return False
        self.records[rid] = {**rec, "voided": False, "created_at": _now()}
        return True

    def get_record(self, rid):
        r = self.records.get(rid)
        return dict(r) if r else None

    def void_record(self, rid):
        self.records[rid]["voided"] = True

    def _find(self, **eq):
        return [dict(r, id=k) for k, r in self.records.items()
                if not r["voided"] and all(r.get(f) == v for f, v in eq.items())]

    def records_by_user_date(self, uid, date):   return self._find(user_id=uid, date=date)
    def records_by_user_month(self, uid, month): return self._find(user_id=uid, month=month)
    def records_by_date(self, date):             return self._find(date=date)
    def records_by_month(self, month):           return self._find(month=month)


class FirestoreStore:
    def __init__(self, credentials_json):
        import firebase_admin
        from firebase_admin import credentials, firestore
        if not firebase_admin._apps:
            cred = credentials.Certificate(json.loads(credentials_json))
            firebase_admin.initialize_app(cred)
        self._fs = firestore
        self.db = firestore.client()

    # 出勤
    def get_attendance(self, uid, date):
        d = self.db.collection("attendance").document(f"{uid}_{date}").get()
        return d.to_dict() if d.exists else None

    def save_attendance(self, uid, date, data):
        self.db.collection("attendance").document(f"{uid}_{date}").set(data, merge=True)

    def _att(self, field, value):
        q = self.db.collection("attendance").where(filter=self._fs.FieldFilter(field, "==", value))
        return [d.to_dict() for d in q.stream()]

    def attendance_by_date(self, date):   return self._att("date", date)
    def attendance_by_month(self, month): return self._att("month", month)

    def get_user(self, uid):
        d = self.db.collection("users").document(uid).get()
        return d.to_dict() if d.exists else None

    def save_user(self, uid, data):
        ref = self.db.collection("users").document(uid)
        if not ref.get().exists:
            data = {"created_at": _now(), **data}
        ref.set(data, merge=True)

    def list_users(self, role=None, status=None):
        q = self.db.collection("users")
        if role:
            q = q.where(filter=self._fs.FieldFilter("role", "==", role))
        if status:
            q = q.where(filter=self._fs.FieldFilter("status", "==", status))
        return [{"uid": d.id, **d.to_dict()} for d in q.stream()]

    def next_emp_no(self):
        ref = self.db.collection("meta").document("counters")

        @self._fs.transactional
        def bump(tx):
            snap = ref.get(transaction=tx)
            n = (snap.to_dict() or {}).get("next_emp_no", 1) if snap.exists else 1
            tx.set(ref, {"next_emp_no": n + 1}, merge=True)
            return n

        return f"E{bump(self.db.transaction()):03d}"

    def add_record(self, rid, rec):
        from google.api_core.exceptions import AlreadyExists
        try:
            self.db.collection("records").document(rid).create(
                {**rec, "voided": False, "created_at": _now()})
            return True
        except AlreadyExists:
            return False

    def get_record(self, rid):
        d = self.db.collection("records").document(rid).get()
        return d.to_dict() if d.exists else None

    def void_record(self, rid):
        self.db.collection("records").document(rid).update({"voided": True})

    def _find(self, **eq):
        # 只用等號條件，不需要建立複合索引；voided 在程式裡過濾
        q = self.db.collection("records")
        for f, v in eq.items():
            q = q.where(filter=self._fs.FieldFilter(f, "==", v))
        out = []
        for d in q.stream():
            r = d.to_dict()
            if not r.get("voided"):
                out.append(dict(r, id=d.id))
        return out

    def records_by_user_date(self, uid, date):   return self._find(user_id=uid, date=date)
    def records_by_user_month(self, uid, month): return self._find(user_id=uid, month=month)
    def records_by_date(self, date):             return self._find(date=date)
    def records_by_month(self, month):           return self._find(month=month)


def make_store():
    from . import config
    if config.STORE_BACKEND == "memory":
        return MemoryStore()
    return FirestoreStore(config.FIREBASE_CREDENTIALS_JSON)
